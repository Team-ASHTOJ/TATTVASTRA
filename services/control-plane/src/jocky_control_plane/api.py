"""Authenticated API for persistent control-plane resources."""

import asyncio
import json
import secrets
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, StreamingResponse
from jocky_contracts import control as contracts
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane import hunts, investigation
from jocky_control_plane.builds import build_variants, compile_version
from jocky_control_plane.config import Settings
from jocky_control_plane.models import (
    Artifact,
    BenchmarkRun,
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
        db: Session, user: User, model: Any, limit: int = 100, **filters: Any
    ) -> list[dict[str, Any]]:
        query = select(model).where(model.organization_id == user.organization_id)
        for key, value in filters.items():
            if value is not None:
                query = query.where(getattr(model, key) == value)
        return [
            document(row)
            for row in db.scalars(query.order_by(model.created_at, model.id).limit(limit))
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
        return {
            "variants": [document(row) for row in rows],
            "same_source": len({row.manifest["source_hash"] for row in rows}) == 1,
            "distinct_artifacts": len({row.content_hash for row in rows}),
            "semantic_equivalence": "NOT_TESTED",
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
            result = {"available": False, "integrity_valid": False, "computed_hash": None}
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
