"""Authenticated API for persistent control-plane resources."""

import asyncio
import json
import secrets
import threading
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, StreamingResponse
from jocky_contracts import control as contracts
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane import forge, hunts, investigation, local_agent, windows_bootstrap
from jocky_control_plane.builds import build_variants, compile_version
from jocky_control_plane.config import Settings
from jocky_control_plane.models import (
    Artifact,
    BenchmarkRun,
    BuildRun,
    Case,
    CompatibilityRun,
    Compilation,
    Endpoint,
    EndpointEnrollment,
    EventOutbox,
    EvidenceManifest,
    Finding,
    Hunt,
    Job,
    Organization,
    Report,
    Role,
    Script,
    ScriptVersion,
    SessionToken,
    State,
    TimelineEvent,
    User,
    Variant,
    WindowsBootstrap,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import (
    aware,
    digest,
    owned,
    password_hash,
    password_matches,
    provenance,
    publish,
    session_user,
    verify_audit,
)


def document(row: Any) -> dict[str, Any]:
    excluded = {"password_hash", "token_hash", "storage_key", "public_key"}
    return dict(
        jsonable_encoder(
            {
                column.name: getattr(row, column.name)
                for column in row.__table__.columns
                if column.name not in excluded
            }
        )
    )


def create_domain_router(factory: sessionmaker[Session], settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["control-plane"])
    store = ObjectStore(settings.object_root)
    local_lock = threading.Lock()

    def transaction() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    DB = Annotated[Session, Depends(transaction)]

    def authenticate(
        db: DB, request: Request, authorization: Annotated[str | None, Header()] = None
    ) -> User:
        user = session_user(db, authorization)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            db.scalar(
                select(Organization)
                .where(Organization.id == user.organization_id)
                .with_for_update()
            )
        return user

    Reader = Annotated[User, Depends(authenticate)]

    def analyst(user: Reader) -> User:
        if user.role not in {Role.ADMIN, Role.ANALYST}:
            raise HTTPException(403, "ANALYST or ADMIN role required")
        return user

    Writer = Annotated[User, Depends(analyst)]

    def administrator(user: Reader) -> User:
        if user.role != Role.ADMIN:
            raise HTTPException(403, "ADMIN role required")
        return user

    Admin = Annotated[User, Depends(administrator)]

    @router.post("/demo", status_code=201)
    def prepare_demo(db: DB, user: Writer) -> Any:
        if settings.mode != "DEMO":
            raise HTTPException(409, "Start the separate DEMO stack to load simulated endpoints")
        from jocky_control_plane.demo import load

        user_id = user.id
        db.commit()  # Compiler stages use the existing independent durable transactions.
        try:
            case_id = load(factory, settings, user_id)
        except RuntimeError as error:
            raise HTTPException(503, str(error)) from error
        return {"case_id": case_id, "simulation": True, "simulation_label": "SIH_VIDEO_DEMO"}

    @router.get("/auth/me")
    def me(user: Reader) -> Any:
        return document(user)

    @router.post("/auth/logout", status_code=204)
    def logout(db: DB, user: Reader, authorization: Annotated[str, Header()]) -> Response:
        token = db.scalar(
            select(SessionToken).where(
                SessionToken.token_hash == digest(authorization[7:].encode())
            )
        )
        if token:
            db.delete(token)
        publish(db, user, "auth.logout", user.id)
        return Response(status_code=204)

    def collection(
        db: Session, user: User, model: Any, limit: int = 500, **filters: Any
    ) -> list[dict[str, Any]]:
        query = select(model).where(model.organization_id == user.organization_id)
        for key, value in filters.items():
            if value is not None:
                query = query.where(getattr(model, key) == value)
        return [
            document(row)
            for row in reversed(
                list(
                    db.scalars(
                        query.order_by(model.created_at.desc(), model.id.desc()).limit(limit)
                    )
                )
            )
        ]

    @router.get("/scripts")
    def scripts(db: DB, user: Reader, case_id: UUID | None = None) -> Any:
        return collection(db, user, Script, case_id=case_id)

    @router.get("/scripts/{identifier}")
    def script_detail(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, Script, identifier, user))

    @router.get("/scripts/{identifier}/versions")
    def script_versions(identifier: UUID, db: DB, user: Reader) -> Any:
        owned(db, Script, identifier, user)
        return collection(db, user, ScriptVersion, script_id=identifier)

    @router.get("/observations")
    def observations(db: DB, user: Reader, case_id: UUID) -> Any:
        from jocky_control_plane.models import Observation

        owned(db, Case, case_id, user)
        return collection(db, user, Observation, case_id=case_id)

    @router.get("/manifests")
    def manifests(db: DB, user: Reader, job_id: UUID | None = None) -> Any:
        if job_id is not None:
            owned(db, Job, job_id, user)
        return collection(db, user, EvidenceManifest, job_id=job_id)

    @router.get("/jobs/{identifier}")
    def job_detail(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, Job, identifier, user))

    @router.get("/compilations")
    def compilations(db: DB, user: Reader) -> Any:
        return collection(db, user, Compilation)

    @router.get("/build-capabilities")
    def build_capabilities(user: Reader) -> Any:
        return forge.capabilities(settings)

    @router.get("/build-runs")
    def build_runs(db: DB, user: Reader) -> Any:
        return collection(db, user, BuildRun)

    @router.post("/build-runs", status_code=202)
    def create_build(
        payload: contracts.BuildCreate, background: BackgroundTasks, db: DB, user: Writer
    ) -> Any:
        compilation = owned(db, Compilation, payload.compilation_id, user)
        if not forge.capabilities(settings)["available"]:
            raise HTTPException(503, "Native compiler unavailable")
        run = forge.start_run(db, compilation, payload.count, payload.seed)
        publish(
            db,
            user,
            "build.created",
            run.id,
            {"compilation_id": str(compilation.id)},
            simulation=run.simulation,
            simulation_label=run.simulation_label,
        )
        db.commit()
        background.add_task(
            forge.execute, factory, settings, run.id, user.id, payload.expected_semantic_hash
        )
        return document(run)

    @router.get("/build-runs/{identifier}")
    def build_run(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, BuildRun, identifier, user))

    @router.get("/build-runs/{identifier}/manifest")
    def build_manifest(identifier: UUID, db: DB, user: Reader) -> Any:
        run = owned(db, BuildRun, identifier, user)
        if run.manifest is None:
            raise HTTPException(409, "Signed build manifest is not ready")
        return run.manifest

    @router.post("/build-runs/{identifier}/verify")
    def verify_build(identifier: UUID, db: DB, user: Reader) -> Any:
        run = owned(db, BuildRun, identifier, user)
        return forge.verify(db, run, settings)

    @router.get("/variants")
    def variant_list(db: DB, user: Reader) -> Any:
        return collection(db, user, Variant)

    @router.get("/hunts")
    def hunts_list(db: DB, user: Reader, case_id: UUID | None = None) -> Any:
        return collection(db, user, Hunt, case_id=case_id)

    @router.get("/reports")
    def reports(db: DB, user: Reader, case_id: UUID | None = None) -> Any:
        return collection(db, user, Report, case_id=case_id)

    @router.post("/auth/login")
    def login(payload: contracts.LoginRequest, db: DB) -> dict[str, Any]:
        user = db.scalar(
            select(User).where(
                User.organization_id == payload.organization_id, User.username == payload.username
            )
        )
        if (
            user is None
            or user.disabled
            or not password_matches(payload.password, user.password_hash)
        ):
            raise HTTPException(401, "Invalid credentials")
        token = secrets.token_urlsafe(48)
        expires = datetime.now(UTC) + timedelta(hours=1)
        db.add(SessionToken(user_id=user.id, token_hash=digest(token.encode()), expires_at=expires))
        publish(db, user, "auth.login", user.id)
        # A caller may use the token before request-scoped dependency teardown.
        # Persist it before sending the successful login response.
        db.commit()
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires,
            "user": document(user),
        }

    @router.post("/users", status_code=201)
    def add_user(payload: contracts.UserCreate, db: DB, user: Admin) -> dict[str, Any]:
        row = User(
            organization_id=user.organization_id,
            username=payload.username,
            password_hash=password_hash(payload.password),
            role=Role(payload.role),
        )
        db.add(row)
        db.flush()
        publish(db, user, "user.created", row.id)
        return document(row)

    @router.post("/cases", status_code=201)
    def add_case(payload: contracts.CaseCreate, db: DB, user: Writer) -> dict[str, Any]:
        if payload.simulation and settings.mode != "DEMO":
            raise HTTPException(409, "Simulated cases require DEMO mode")
        row = Case(
            organization_id=user.organization_id, **payload.model_dump(exclude={"schema_version"})
        )
        db.add(row)
        db.flush()
        publish(
            db,
            user,
            "case.created",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.get("/cases")
    def cases(db: DB, user: Reader, limit: int = Query(100, ge=1, le=500)) -> Any:
        return collection(db, user, Case, limit)

    @router.get("/cases/{identifier}")
    def case(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, Case, identifier, user))

    @router.patch("/cases/{identifier}")
    def patch_case(identifier: UUID, payload: contracts.CasePatch, db: DB, user: Writer) -> Any:
        row = owned(db, Case, identifier, user)
        for key, value in payload.model_dump(exclude_none=True, exclude={"schema_version"}).items():
            setattr(row, key, State(value) if key == "status" else value)
        publish(
            db,
            user,
            "case.updated",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.post("/scripts", status_code=201)
    def add_script(payload: contracts.ScriptCreate, db: DB, user: Writer) -> Any:
        case = owned(db, Case, payload.case_id, user)
        row = Script(**provenance(case), case_id=case.id, name=payload.name)
        db.add(row)
        db.flush()
        version = ScriptVersion(
            **provenance(case),
            script_id=row.id,
            version=1,
            source=payload.source,
            source_hash=digest(payload.source.encode()),
        )
        db.add(version)
        db.flush()
        publish(
            db,
            user,
            "script.created",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return {**document(row), "version": document(version)}

    @router.post("/scripts/{identifier}/versions", status_code=201)
    def add_version(
        identifier: UUID, payload: contracts.VersionCreate, db: DB, user: Writer
    ) -> Any:
        script = owned(db, Script, identifier, user)
        db.refresh(script, with_for_update=True)
        latest = (
            db.scalar(
                select(func.max(ScriptVersion.version)).where(ScriptVersion.script_id == identifier)
            )
            or 0
        )
        row = ScriptVersion(
            **provenance(script),
            script_id=identifier,
            version=latest + 1,
            source=payload.source,
            source_hash=digest(payload.source.encode()),
        )
        db.add(row)
        db.flush()
        publish(
            db,
            user,
            "script.version.created",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.post("/scripts/{identifier}/compile", status_code=201)
    def compile_script(identifier: UUID, db: DB, user: Writer) -> Any:
        owned(db, Script, identifier, user)
        version = db.scalar(
            select(ScriptVersion)
            .where(ScriptVersion.script_id == identifier)
            .order_by(ScriptVersion.version.desc())
            .limit(1)
        )
        assert version is not None
        return document(compile_version(db, version, user, settings))

    @router.get("/compilations/{identifier}")
    def compilation(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, Compilation, identifier, user))

    @router.get("/compilations/{identifier}/{stage}")
    def compiler_output(identifier: UUID, stage: str, db: DB, user: Reader) -> Any:
        row = owned(db, Compilation, identifier, user)
        if stage not in {"check", "tokens", "ast", "jir", "llvm", "plan"}:
            raise HTTPException(404, "Unknown compiler stage")
        if stage not in row.outputs:
            raise HTTPException(409, "Stage has not completed")
        return row.outputs[stage]

    @router.post("/compilations/{identifier}/target-builds", status_code=201)
    def target_builds(
        identifier: UUID, payload: contracts.TargetBuildCreate, db: DB, user: Writer
    ) -> Any:
        row = owned(db, Compilation, identifier, user)
        version = owned(db, ScriptVersion, row.script_version_id, user)
        output = []
        for target in dict.fromkeys(payload.targets):
            output.extend(
                build_variants(
                    db,
                    row,
                    version,
                    1,
                    user,
                    settings,
                    execution_mode="native",
                    target=target,
                    object_only=True,
                    seed_values=["0000000000000001"],
                )
            )
        return [document(item) for item in output]

    @router.post("/compilations/{identifier}/variants", status_code=201)
    def variants(identifier: UUID, payload: contracts.VariantCreate, db: DB, user: Writer) -> Any:
        row = owned(db, Compilation, identifier, user)
        version = owned(db, ScriptVersion, row.script_version_id, user)
        return [
            document(variant)
            for variant in build_variants(db, row, version, payload.count, user, settings)
        ]

    @router.post("/variants/compare")
    def compare(payload: contracts.VariantCompare, db: DB, user: Reader) -> Any:
        from jocky_control_plane.models import Variant

        rows = [owned(db, Variant, identifier, user) for identifier in payload.variant_ids]
        run_ids = {row.build_run_id for row in rows}
        runs = [db.get(BuildRun, identifier) for identifier in run_ids if identifier]
        trusted = (
            bool(rows)
            and None not in run_ids
            and all(
                run and run.status.value == "READY" and forge.verify(db, run, settings)["valid"]
                for run in runs
            )
        )
        return {
            "variants": [document(row) for row in rows],
            "same_source": len({row.manifest["source_hash"] for row in rows}) == 1,
            "distinct_artifacts": len({row.content_hash for row in rows}),
            "semantic_equivalence": "VERIFIED"
            if trusted
            and all(row.manifest.get("equivalence_status") == "VERIFIED" for row in rows)
            and len({row.manifest.get("semantic_result_hash") for row in rows}) == 1
            and len({row.manifest.get("jir_hash") for row in rows}) == 1
            else "NOT_TESTED",
            "equivalence_scope": "Deterministic compiler fixture only",
        }

    @router.get("/variants/{identifier}")
    def variant(identifier: UUID, db: DB, user: Reader) -> Any:
        from jocky_control_plane.models import Variant

        return document(owned(db, Variant, identifier, user))

    @router.get("/variants/{identifier}/manifest")
    def variant_manifest(identifier: UUID, db: DB, user: Reader) -> Any:
        return owned(db, Variant, identifier, user).manifest

    @router.post("/endpoints/enrollments", status_code=201)
    def enrollment(payload: contracts.EnrollmentCreate, db: DB, user: Admin) -> Any:
        if payload.simulation and settings.mode != "DEMO":
            raise HTTPException(409, "Simulation requires DEMO mode")
        token = secrets.token_urlsafe(48)
        row = EndpointEnrollment(
            organization_id=user.organization_id,
            token_hash=digest(token.encode()),
            expires_at=datetime.now(UTC) + timedelta(seconds=payload.validity_seconds),
            capabilities=payload.capabilities,
            simulation=payload.simulation,
            simulation_label=payload.simulation_label,
        )
        db.add(row)
        db.flush()
        publish(
            db,
            user,
            "endpoint.enrollment.issued",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return {"id": row.id, "one_time_token": token, "expires_at": row.expires_at}

    def windows_status(db: Session, user: User) -> dict[str, Any]:
        row = db.scalar(
            select(WindowsBootstrap).where(
                WindowsBootstrap.organization_id == user.organization_id,
                WindowsBootstrap.hostname == "WINDOWS-01",
            )
        )
        if row is None:
            return {"state": "NOT_CONFIGURED", "configured": False, "hostname": "WINDOWS-01"}
        endpoint = db.get(Endpoint, row.endpoint_id) if row.endpoint_id else None
        state = row.reported_state
        if endpoint is None and state == "ONLINE":
            state = "WAITING_FOR_HEARTBEAT"
        if (
            endpoint is not None
            and endpoint.last_seen is not None
            and endpoint.status != State.REVOKED
        ):
            age = datetime.now(UTC) - aware(endpoint.last_seen)
            state = "ONLINE" if age <= timedelta(seconds=90) else "STALE"
        elif row.desired_state == "STOPPED" and state not in {"FAILED", "READY"}:
            state = "STOPPED"
        elif (
            row.desired_state != "START"
            and row.last_poll_at is not None
            and not windows_bootstrap.polled(row)
            and state not in {"FAILED", "STOPPED"}
        ):
            # OFFLINE is a supervisor that was being heard and then went quiet.
            # A host that has registered but never polled is READY: prepared,
            # not connected, and never described as anything more.
            state = "OFFLINE"
        return {
            "id": row.id,
            "configured": True,
            "hostname": row.hostname,
            "state": state,
            "reported_state": row.reported_state,
            "desired_state": row.desired_state,
            "last_poll_at": row.last_poll_at,
            "error": row.last_error,
            "endpoint_id": row.endpoint_id,
            "endpoint": document(endpoint) if endpoint else None,
        }

    @router.get("/windows-endpoint/status")
    def get_windows_endpoint(db: DB, user: Admin) -> Any:
        return windows_status(db, user)

    @router.post("/windows-endpoint/bootstrap", status_code=201)
    def register_windows_bootstrap(db: DB, user: Admin) -> Any:
        existing = db.scalar(
            select(WindowsBootstrap).where(
                WindowsBootstrap.organization_id == user.organization_id,
                WindowsBootstrap.hostname == "WINDOWS-01",
            )
        )
        if existing is not None:
            raise HTTPException(409, "WINDOWS-01 bootstrap is already registered")
        configured = (
            settings.windows_api_url,
            settings.windows_control_server,
            settings.windows_enrollment_server,
        )
        if not all(configured) or not all(
            str(value).startswith("https://") for value in configured
        ):
            raise HTTPException(
                503,
                "Configure HTTPS JOCKY_WINDOWS_API_URL, JOCKY_WINDOWS_CONTROL_SERVER, "
                "and JOCKY_WINDOWS_ENROLLMENT_SERVER for the Windows VM",
            )
        secret = secrets.token_urlsafe(48)
        row = WindowsBootstrap(
            organization_id=user.organization_id,
            simulation=False,
            hostname="WINDOWS-01",
            credential_hash=digest(secret.encode()),
            desired_state="STOPPED",
            reported_state="READY",
        )
        db.add(row)
        db.flush()
        publish(db, user, "windows.bootstrap.registered", row.id)
        return {
            "schema_version": "1.0.0",
            "api_url": settings.windows_api_url,
            "control_server": settings.windows_control_server,
            "enrollment_server": settings.windows_enrollment_server,
            "organization_id": str(user.organization_id),
            "bootstrap_id": str(row.id),
            "bootstrap_secret": secret,
            "ca_pem": settings.tls_ca_path.read_text(),
        }

    @router.post("/windows-endpoint/start")
    def start_windows_endpoint(db: DB, user: Admin) -> Any:
        row = db.scalar(
            select(WindowsBootstrap)
            .where(
                WindowsBootstrap.organization_id == user.organization_id,
                WindowsBootstrap.hostname == "WINDOWS-01",
            )
            .with_for_update()
        )
        if row is None:
            raise HTTPException(
                409, "Windows bootstrap is not configured; complete Advanced Setup once"
            )
        current = windows_status(db, user)
        if row.desired_state == "START" and current["state"] in {
            "STARTING",
            "ENROLLING",
            "WAITING_FOR_HEARTBEAT",
            "ONLINE",
        }:
            return current
        row.desired_state = "START"
        row.reported_state = "STARTING"
        row.last_error = None
        if row.endpoint_id is None:
            row.activation_id = uuid4()
            row.enrollment_id = None
        publish(db, user, "windows.endpoint.start_requested", row.id)
        db.flush()
        return windows_status(db, user)

    @router.post("/windows-endpoint/stop")
    def stop_windows_endpoint(db: DB, user: Admin) -> Any:
        row = db.scalar(
            select(WindowsBootstrap)
            .where(
                WindowsBootstrap.organization_id == user.organization_id,
                WindowsBootstrap.hostname == "WINDOWS-01",
            )
            .with_for_update()
        )
        if row is None:
            raise HTTPException(409, "Windows bootstrap is not configured")
        if row.desired_state != "STOPPED":
            row.desired_state = "STOPPED"
            publish(db, user, "windows.endpoint.stop_requested", row.id)
        db.flush()
        return windows_status(db, user)

    @router.post("/windows-bootstrap/poll")
    def poll_windows_bootstrap(
        payload: contracts.WindowsBootstrapPoll,
        request: Request,
        db: DB,
        authorization: Annotated[str | None, Header()] = None,
    ) -> Any:
        forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
        if (
            settings.environment != "test"
            and request.url.scheme != "https"
            and forwarded != "https"
        ):
            raise HTTPException(426, "Windows bootstrap polling requires HTTPS")
        row = windows_bootstrap.credential(db, authorization)
        row.last_poll_at = datetime.now(UTC)
        row.reported_state = payload.state
        row.last_error = payload.error
        if payload.endpoint_id is not None:
            endpoint = db.scalar(
                select(Endpoint).where(
                    Endpoint.id == payload.endpoint_id,
                    Endpoint.organization_id == row.organization_id,
                )
            )
            if endpoint is None or endpoint.target_os != "windows":
                raise HTTPException(
                    409, "Bootstrap endpoint identity is not an owned Windows endpoint"
                )
            if row.endpoint_id is not None and row.endpoint_id != endpoint.id:
                raise HTTPException(409, "WINDOWS-01 identity is already bound")
            row.endpoint_id = endpoint.id
        if row.enrollment_id is not None and row.endpoint_id is None:
            issued = db.get(EndpointEnrollment, row.enrollment_id)
            if issued is not None and issued.endpoint_id is not None:
                row.endpoint_id = issued.endpoint_id
        response: dict[str, Any] = {
            "action": "START" if row.desired_state == "START" else "STOP",
            "authoritative_state": "WAITING_FOR_HEARTBEAT",
        }
        if row.endpoint_id is not None:
            endpoint = db.get(Endpoint, row.endpoint_id)
            if endpoint and endpoint.last_seen and endpoint.status != State.REVOKED:
                response["authoritative_state"] = (
                    "ONLINE"
                    if datetime.now(UTC) - aware(endpoint.last_seen) <= timedelta(seconds=90)
                    else "STALE"
                )
        elif row.desired_state == "START" and payload.needs_enrollment:
            if row.activation_id is None:
                row.activation_id = uuid4()
            issued = db.get(EndpointEnrollment, row.enrollment_id) if row.enrollment_id else None
            if issued is None or aware(issued.expires_at) <= datetime.now(UTC):
                if issued is not None:
                    row.activation_id = uuid4()
                token = windows_bootstrap.activation_token(settings, row)
                issued = EndpointEnrollment(
                    organization_id=row.organization_id,
                    token_hash=digest(token.encode()),
                    expires_at=datetime.now(UTC) + timedelta(minutes=10),
                    capabilities=[
                        "system.read",
                        "users.read",
                        "process.read",
                        "network.read",
                        "persistence.read",
                        "logs.read",
                        "drivers.read",
                    ],
                    simulation=False,
                )
                db.add(issued)
                db.flush()
                row.enrollment_id = issued.id
            else:
                token = windows_bootstrap.activation_token(settings, row)
            response["enrollment"] = {
                "id": str(issued.id),
                "one_time_token": token,
                "expires_at": issued.expires_at,
                "ca_pem": settings.tls_ca_path.read_text(),
            }
        return response

    def local_status(db: Session, user: User, slot: int = 1) -> dict[str, Any]:
        status = local_agent.runtime(settings, "/status", slot=slot)
        status["slot"] = slot
        if status.get("organization_id") and status["organization_id"] != str(user.organization_id):
            raise HTTPException(409, "Local runtime belongs to another organization")
        endpoint = (
            owned(db, Endpoint, UUID(status["endpoint_id"]), user)
            if status.get("endpoint_id")
            else None
        )
        if endpoint:
            status["endpoint"] = document(endpoint)
        if status["state"] == "WAITING_FOR_HEARTBEAT":
            started = aware(datetime.fromisoformat(status["connected_at"]))
            if (
                endpoint
                and endpoint.status != State.REVOKED
                and endpoint.last_seen
                and aware(endpoint.last_seen) >= started
            ):
                status["state"] = (
                    "ONLINE"
                    if datetime.now(UTC) - aware(endpoint.last_seen) <= timedelta(seconds=90)
                    else "STALE"
                )
            elif datetime.now(UTC) - started > timedelta(seconds=45):
                status.update(
                    state="FAILED",
                    error="Authenticated heartbeat timed out. Check AgentControl, then retry.",
                )
        return status

    @router.get("/local-agent/status")
    def get_local_agent(db: DB, user: Admin, slot: int = Query(default=1, ge=1, le=3)) -> Any:
        return local_status(db, user, slot)

    @router.get("/local-agents")
    def get_local_agents(db: DB, user: Admin) -> Any:
        return [local_status(db, user, slot) for slot in range(1, 4)]

    @router.post("/local-agent/start")
    def start_local_agent(db: DB, user: Admin, slot: int = Query(default=1, ge=1, le=3)) -> Any:
        with local_lock:
            status = local_status(db, user, slot)
            if status["state"] in {
                "STARTING",
                "ENROLLING",
                "WAITING_FOR_HEARTBEAT",
                "ONLINE",
                "STALE",
            }:
                return status
            if status.get("state") == "FAILED":
                local_agent.runtime(settings, "/stop", {}, slot=slot)
            material = {"organization_id": str(user.organization_id)}
            if status.get("needs_enrollment"):
                if status.get("enrollment_id"):
                    previous = owned(db, EndpointEnrollment, UUID(status["enrollment_id"]), user)
                    if previous.endpoint_id:
                        raise HTTPException(
                            409,
                            "Enrollment consumed but local credentials incomplete. "
                            "Restore runtime state; refusing to duplicate the endpoint.",
                        )
                issued = enrollment(
                    contracts.EnrollmentCreate(
                        simulation=False,
                        validity_seconds=600,
                        capabilities=[
                            "system.read",
                            "users.read",
                            "process.read",
                            "network.read",
                            "persistence.read",
                            "logs.read",
                            "drivers.read",
                        ],
                    ),
                    db,
                    user,
                )
                db.commit()  # AgentControl must see the durable token before enrollment begins.
                material.update(
                    enrollment_id=str(issued["id"]),
                    token=issued["one_time_token"],
                    ca=settings.tls_ca_path.read_text(),
                )
            local_agent.runtime(settings, "/start", material, slot=slot)
            return local_status(db, user, slot)

    @router.post("/local-agent/stop")
    def stop_local_agent(db: DB, user: Admin, slot: int = Query(default=1, ge=1, le=3)) -> Any:
        local_status(db, user, slot)  # Verify organization ownership before any lifecycle action.
        local_agent.runtime(settings, "/stop", {}, slot=slot)
        return local_status(db, user, slot)

    @router.get("/endpoints")
    def endpoints(db: DB, user: Reader) -> Any:
        rows = collection(db, user, Endpoint)
        for row in rows:
            if row["status"] == State.REVOKED:
                continue
            if row["last_seen"] is None or datetime.now(UTC) - aware(
                datetime.fromisoformat(row["last_seen"])
            ) > timedelta(seconds=90):
                row["status"] = State.OFFLINE
        return rows

    @router.get("/endpoints/enrollments/{identifier}")
    def enrollment_status(identifier: UUID, db: DB, user: Admin) -> Any:
        row = owned(db, EndpointEnrollment, identifier, user)
        state = "WAITING"
        endpoint = db.get(Endpoint, row.endpoint_id) if row.endpoint_id else None
        if endpoint is not None:
            state = (
                "ONLINE"
                if endpoint.last_seen
                and datetime.now(UTC) - aware(endpoint.last_seen) <= timedelta(seconds=90)
                and endpoint.status != State.REVOKED
                else "STALE"
            )
        elif aware(row.expires_at) <= datetime.now(UTC):
            state = "EXPIRED"
        return {
            "id": row.id,
            "state": state,
            "endpoint_id": row.endpoint_id,
            "expires_at": row.expires_at,
        }

    @router.get("/endpoints/enrollments/{identifier}/ca")
    def enrollment_ca(identifier: UUID, db: DB, user: Admin) -> Response:
        owned(db, EndpointEnrollment, identifier, user)
        return Response(
            settings.tls_ca_path.read_bytes(),
            media_type="application/x-pem-file",
            headers={
                "Content-Disposition": "attachment; filename=control-plane-ca.pem",
                "Cache-Control": "no-store",
            },
        )

    @router.get("/endpoints/enrollments/{identifier}/bootstrap")
    def enrollment_bootstrap(identifier: UUID, db: DB, user: Admin) -> Response:
        """Serve the Windows bootstrap that drives the existing enrollment flow."""
        owned(db, EndpointEnrollment, identifier, user)
        path = settings.bootstrap_script_path
        if not path.is_file():
            raise HTTPException(404, "Windows bootstrap script is not present in this deployment")
        return Response(
            path.read_bytes(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=connect-jocky.ps1",
                "Cache-Control": "no-store",
            },
        )

    @router.get("/endpoints/{identifier}")
    def endpoint(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, Endpoint, identifier, user))

    @router.post("/endpoints/{identifier}/revoke")
    def revoke_endpoint(identifier: UUID, db: DB, user: Admin) -> Any:
        row = owned(db, Endpoint, identifier, user)
        row.status = State.REVOKED
        publish(
            db,
            user,
            "endpoint.revoked",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.get("/endpoints/{identifier}/{kind}")
    def endpoint_records(identifier: UUID, kind: str, db: DB, user: Reader) -> Any:
        from jocky_control_plane.models import Observation

        owned(db, Endpoint, identifier, user)
        if kind not in {"jobs", "observations"}:
            raise HTTPException(404, "Unknown endpoint collection")
        return collection(db, user, Job if kind == "jobs" else Observation, endpoint_id=identifier)

    @router.post("/hunts", status_code=201)
    def add_hunt(payload: contracts.HuntCreate, db: DB, user: Writer) -> Any:
        case = owned(db, Case, payload.case_id, user)
        compilation = owned(db, Compilation, payload.compilation_id, user)
        version = owned(db, ScriptVersion, compilation.script_version_id, user)
        script = owned(db, Script, version.script_id, user)
        if script.case_id != case.id:
            raise HTTPException(409, "Compilation belongs to a different case")
        for identifier in payload.endpoint_ids:
            owned(db, Endpoint, identifier, user)
        if not set(payload.endpoint_modes).issubset(payload.endpoint_ids):
            raise HTTPException(422, "Execution overrides must reference selected endpoints")
        row = Hunt(
            **provenance(case),
            case_id=case.id,
            compilation_id=compilation.id,
            endpoint_ids=list(dict.fromkeys(str(i) for i in payload.endpoint_ids)),
            execution_mode=payload.execution_mode,
            endpoint_modes={str(key): mode for key, mode in payload.endpoint_modes.items()},
            enforcement_mode=payload.enforcement_mode,
            diverse=payload.diverse,
            retry_limit=payload.retry_limit,
        )
        db.add(row)
        db.flush()
        publish(
            db,
            user,
            "hunt.created",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.get("/hunts/{identifier}")
    def hunt(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, Hunt, identifier, user))

    @router.get("/hunts/{identifier}/jobs")
    def hunt_jobs(identifier: UUID, db: DB, user: Reader) -> Any:
        owned(db, Hunt, identifier, user)
        return collection(db, user, Job, limit=500, hunt_id=identifier)

    @router.post("/hunts/{identifier}/start")
    def start_hunt(identifier: UUID, db: DB, user: Writer) -> Any:
        row = owned(db, Hunt, identifier, user)
        hunts.start(db, row, user, settings)
        return document(row)

    @router.post("/hunts/{identifier}/cancel")
    def cancel_hunt(identifier: UUID, db: DB, user: Writer) -> Any:
        row = owned(db, Hunt, identifier, user)
        hunts.cancel(db, row, user)
        return document(row)

    @router.get("/artifacts")
    def artifacts(db: DB, user: Reader, case_id: UUID | None = None) -> Any:
        return collection(db, user, Artifact, case_id=case_id)

    @router.get("/artifacts/{identifier}")
    def artifact(identifier: UUID, db: DB, user: Reader) -> Any:
        row = owned(db, Artifact, identifier, user)
        publish(
            db,
            user,
            "artifact.access",
            identifier,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.get("/artifacts/{identifier}/content")
    def content(identifier: UUID, db: DB, user: Reader) -> Response:
        row = owned(db, Artifact, identifier, user)
        try:
            data = store.get(row.storage_key)
        except FileNotFoundError as error:
            raise HTTPException(404, "Object content unavailable") from error
        if digest(data) != row.content_hash:
            raise HTTPException(409, "Object integrity mismatch")
        publish(
            db,
            user,
            "artifact.access",
            identifier,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return Response(
            data,
            media_type=row.media_type,
            headers={"Content-Disposition": "attachment", "X-Content-Type-Options": "nosniff"},
        )

    @router.post("/artifacts/{identifier}/verify")
    def verify_artifact(identifier: UUID, db: DB, user: Reader) -> Any:
        row = owned(db, Artifact, identifier, user)
        try:
            data = store.get(row.storage_key)
            hashed = digest(data)
            result = {
                "available": True,
                "integrity_valid": hashed == row.content_hash and len(data) == row.size_bytes,
                "expected_hash": row.content_hash,
                "computed_hash": hashed,
            }
        except FileNotFoundError:
            result = {
                "available": False,
                "integrity_valid": False,
                "expected_hash": row.content_hash,
                "computed_hash": None,
            }
        publish(
            db,
            user,
            "artifact.verified",
            identifier,
            result,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return result

    @router.get("/manifests/{identifier}")
    def manifest(identifier: UUID, db: DB, user: Reader) -> Any:
        return document(owned(db, EvidenceManifest, identifier, user))

    @router.post("/manifests/{identifier}/verify")
    def verify_manifest(identifier: UUID, db: DB, user: Reader) -> Any:
        from jocky_control_plane.ingestion import verify_manifest_document

        row = owned(db, EvidenceManifest, identifier, user)
        result = verify_manifest_document(db, row, user, store)
        publish(
            db,
            user,
            "manifest.checked",
            row.id,
            result,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return result

    @router.get("/findings")
    def findings(db: DB, user: Reader, case_id: UUID) -> Any:
        owned(db, Case, case_id, user)
        return collection(db, user, Finding, case_id=case_id)

    @router.get("/graph")
    def graph(db: DB, user: Reader, case_id: UUID) -> Any:
        owned(db, Case, case_id, user)
        return investigation.graph(db, case_id, user)

    @router.get("/timeline")
    def timeline(
        db: DB,
        user: Reader,
        case_id: UUID,
        endpoint_id: UUID | None = None,
        collector: str | None = None,
        severity: str | None = None,
        type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Any:
        owned(db, Case, case_id, user)
        if any(value is not None and value.tzinfo is None for value in (start, end)):
            raise HTTPException(422, "Timeline range requires timezone-aware timestamps")
        if start is not None and end is not None and start > end:
            raise HTTPException(422, "Timeline range start must not follow end")
        query = select(TimelineEvent).where(
            TimelineEvent.organization_id == user.organization_id, TimelineEvent.case_id == case_id
        )
        for field, value in (
            ("endpoint_id", endpoint_id),
            ("collector", collector),
            ("severity", severity),
            ("type", type),
        ):
            if value is not None:
                query = query.where(getattr(TimelineEvent, field) == value)
        if start is not None:
            query = query.where(TimelineEvent.timestamp >= aware(start))
        if end is not None:
            query = query.where(TimelineEvent.timestamp <= aware(end))
        return [
            document(row)
            for row in db.scalars(
                query.order_by(TimelineEvent.timestamp, TimelineEvent.id).limit(500)
            )
        ]

    @router.get("/audit/verify")
    def audit(db: DB, user: Admin) -> Any:
        return verify_audit(db, user)

    @router.get("/events")
    def events(
        user: Reader,
        last_event_id: Annotated[str | None, Header()] = None,
        after: int = Query(-1, ge=-1),
        authorization: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        try:
            cursor = int(last_event_id) if last_event_id is not None else after
        except ValueError as error:
            raise HTTPException(422, "Invalid event cursor") from error
        if cursor < -1:
            raise HTTPException(422, "Invalid event cursor")

        async def stream() -> AsyncIterator[str]:
            nonlocal cursor
            # Bounded stream lifetime requires reauthentication on reconnect.
            until = asyncio.get_running_loop().time() + settings.event_stream_seconds
            while asyncio.get_running_loop().time() < until:
                with factory() as session:
                    try:
                        current = session_user(session, authorization)
                        if current.organization_id != user.organization_id:
                            return
                    except HTTPException:
                        yield 'event: auth.expired\ndata: {"detail":"Session expired"}\n\n'
                        return
                    rows = session.scalars(
                        select(EventOutbox)
                        .where(
                            EventOutbox.organization_id == user.organization_id,
                            EventOutbox.sequence > cursor,
                        )
                        .order_by(EventOutbox.sequence)
                        .limit(100)
                    ).all()
                    for row in rows:
                        cursor = row.sequence
                        encoded = json.dumps(document(row))
                        yield f"id: {cursor}\nevent: {row.topic}\ndata: {encoded}\n\n"
                if not rows:
                    yield ": keepalive\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    @router.post("/compatibility-runs", status_code=201)
    def compatibility(payload: contracts.CompatibilityCreate, db: DB, user: Writer) -> Any:
        from jocky_control_plane.models import Variant

        variant = owned(db, Variant, payload.variant_id, user)
        if payload.endpoint_id is not None:
            endpoint = owned(db, Endpoint, payload.endpoint_id, user)
            if endpoint.simulation != variant.simulation:
                raise HTTPException(409, "Compatibility provenance mismatch")
        row = CompatibilityRun(
            **provenance(variant),
            variant_id=variant.id,
            endpoint_id=payload.endpoint_id,
            recorded_by=user.id,
            observations=payload.model_dump(mode="json"),
        )
        db.add(row)
        db.flush()
        publish(
            db,
            user,
            "compatibility.recorded",
            row.id,
            simulation=row.simulation,
            simulation_label=row.simulation_label,
        )
        return document(row)

    @router.get("/compatibility-runs")
    def compatibility_runs(db: DB, user: Reader) -> Any:
        return collection(db, user, CompatibilityRun)

    @router.get("/benchmarks")
    def benchmarks(db: DB, user: Reader) -> Any:
        return collection(db, user, BenchmarkRun)

    @router.post("/benchmarks", status_code=201)
    def benchmark(payload: contracts.BenchmarkCreate, db: DB, user: Writer) -> Any:
        from jocky_control_plane.reporting import run_benchmark

        return document(
            run_benchmark(
                db,
                owned(db, Compilation, payload.compilation_id, user),
                payload.repetitions,
                user,
                settings,
            )
        )

    @router.post("/reports", status_code=201)
    def report(payload: contracts.ReportCreate, db: DB, user: Writer) -> Any:
        from jocky_control_plane.reporting import generate_report

        return document(generate_report(db, owned(db, Case, payload.case_id, user), user, store))

    @router.get("/reports/{identifier}")
    def report_status(identifier: UUID, db: DB, user: Reader) -> Any:
        from jocky_control_plane.models import Report

        row = owned(db, Report, identifier, user)
        return {
            **document(row),
            "download_url": f"/api/artifacts/{row.artifact_id}/content"
            if row.artifact_id
            else None,
        }

    return router
