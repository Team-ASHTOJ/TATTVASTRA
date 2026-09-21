"""Repeatable backend video scenario. Compilation is real; endpoint data is simulated."""

import base64
import json
from datetime import UTC, datetime
from importlib.resources import files
from uuid import UUID, uuid4

import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane.builds import build_variants, compile_version
from jocky_control_plane.config import Settings
from jocky_control_plane.hunts import envelope, summarize
from jocky_control_plane.ingestion import ingest_manifest, ingest_observation
from jocky_control_plane.models import (
    Artifact,
    Case,
    Compilation,
    Endpoint,
    ExecutionPlan,
    Hunt,
    Job,
    Role,
    Script,
    ScriptVersion,
    State,
    User,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest, provenance, publish

READY = "JOCKY_VIDEO_V1_READY"


def load(factory: sessionmaker[Session], settings: Settings, user_id: UUID | None = None) -> str:
    if settings.mode != "DEMO":
        raise RuntimeError("DEMO fixture loader requires JOCKY_MODE=DEMO")
    fixture = json.loads(files("jocky_control_plane").joinpath("data/demo.json").read_text())
    with factory.begin() as db:
        user = (
            db.get(User, user_id)
            if user_id
            else db.scalar(
                select(User).where(User.role == Role.ADMIN, User.disabled.is_(False)).limit(1)
            )
        )
        if user is None or user.disabled or user.role not in {Role.ADMIN, Role.ANALYST}:
            raise RuntimeError("An authorized operator is required")
        existing = db.scalar(
            select(Case).where(
                Case.organization_id == user.organization_id,
                Case.description == READY,
                Case.simulation.is_(True),
            )
        )
        if existing:
            return str(existing.id)
        case = Case(
            organization_id=user.organization_id,
            title=fixture["title"],
            simulation=True,
            simulation_label=fixture["simulation_label"],
        )
        db.add(case)
        db.flush()
        script = Script(**provenance(case), case_id=case.id, name="SIH video investigation")
        db.add(script)
        db.flush()
        version = ScriptVersion(
            **provenance(case),
            script_id=script.id,
            version=1,
            source=fixture["source"],
            source_hash=digest(fixture["source"].encode()),
        )
        db.add(version)
        db.flush()
        user_id, version_id, case_id = user.id, version.id, case.id
        publish(
            db,
            user,
            "demo.case.created",
            case.id,
            simulation=True,
            simulation_label=case.simulation_label,
        )
    with factory() as db:
        user, loaded_version = db.get(User, user_id), db.get(ScriptVersion, version_id)
        assert user is not None and loaded_version is not None
        version = loaded_version
        compilation = compile_version(db, version, user, settings)
        if compilation.status != State.SUCCESS:
            raise RuntimeError(
                "Demo preparation requires a working native compiler; inspect the saved compilation"
            )
        compilation_id = compilation.id
    with factory.begin() as db:
        user, loaded_version = db.get(User, user_id), db.get(ScriptVersion, version_id)
        loaded_compilation, loaded_case = db.get(Compilation, compilation_id), db.get(Case, case_id)
        assert (
            loaded_version is not None
            and loaded_compilation is not None
            and loaded_case is not None
        )
        version, compilation, case = loaded_version, loaded_compilation, loaded_case
        assert (
            user is not None
            and version is not None
            and compilation is not None
            and case is not None
        )
        variants = build_variants(
            db,
            compilation,
            version,
            len(fixture["endpoints"]),
            user,
            settings,
            seed_values=fixture["seeds"],
        )
        plan = ExecutionPlan(
            **provenance(version),
            compilation_id=compilation.id,
            document=compilation.outputs["plan"],
        )
        db.add(plan)
        db.flush()
        hunt = Hunt(
            **provenance(version),
            case_id=case_id,
            compilation_id=compilation.id,
            endpoint_ids=[],
            execution_mode="memory",
            status=State.RUNNING,
        )
        db.add(hunt)
        db.flush()
        endpoint_ids = []
        store = ObjectStore(settings.object_root)
        for spec, variant in zip(fixture["endpoints"], variants, strict=True):
            key = Ed25519PrivateKey.generate()
            endpoint = Endpoint(
                **provenance(version),
                hostname=spec["hostname"],
                target_os=spec["os"],
                target_arch=spec["arch"],
                agent_version="VIDEO_DEMO_FIXTURE",
                identity=digest(key.public_key().public_bytes_raw()),
                public_key=base64.b64encode(key.public_key().public_bytes_raw()).decode(),
                certificate_fingerprint=digest(b"demo:" + key.public_key().public_bytes_raw()),
                capabilities=plan.document["required_capabilities"],
                execution_modes=[],
                status=State.OFFLINE,
            )
            db.add(endpoint)
            db.flush()
            endpoint_ids.append(str(endpoint.id))
            job = Job(
                **provenance(version),
                hunt_id=hunt.id,
                endpoint_id=endpoint.id,
                variant_id=variant.id,
                plan_id=plan.id,
                status=State.RUNNING,
                reason="SIMULATED scenario; no endpoint code executed",
            )
            db.add(job)
            db.flush()
            job.envelope = envelope(job, hunt, plan, variant, settings)
            timestamp = datetime.now(UTC).isoformat()
            hashes = []
            for record in spec["observations"]:
                payload = {
                    "schema_version": "1.0.0",
                    "simulation": True,
                    "simulation_label": fixture["simulation_label"],
                    "observation_id": str(uuid4()),
                    "case_id": str(case_id),
                    "endpoint_id": str(endpoint.id),
                    "job_id": str(job.id),
                    "collector_id": record["collector"],
                    "timestamp": timestamp,
                    "source_time": None,
                    "type": record["collector"],
                    "data": record["data"],
                    "variant_id": str(variant.id),
                    "source_hash": plan.document["source_hash"],
                    "jir_hash": plan.document["jir_hash"],
                }
                payload["integrity_hash"] = digest(rfc8785.dumps(payload))
                hashes.append(payload["integrity_hash"])
                ingest_observation(db, endpoint, payload, user)
            content = rfc8785.dumps(
                {
                    "simulation": True,
                    "simulation_label": fixture["simulation_label"],
                    "endpoint": spec["hostname"],
                    "observations": spec["observations"],
                    "outcome": spec["outcome"],
                }
            )
            content_hash = store.put(content)
            artifact = Artifact(
                **provenance(version),
                case_id=case_id,
                job_id=job.id,
                content_hash=content_hash,
                storage_key=content_hash,
                size_bytes=len(content),
                media_type="application/json",
            )
            db.add(artifact)
            db.flush()
            manifest = {
                "schema_version": "1.0.0",
                "simulation": True,
                "simulation_label": fixture["simulation_label"],
                "case_id": str(case_id),
                "endpoint_id": str(endpoint.id),
                "agent_identity": endpoint.identity,
                "job_id": str(job.id),
                "source_hash": plan.document["source_hash"],
                "jir_hash": plan.document["jir_hash"],
                "llvm_ir_hash": variant.manifest["llvm_ir_hash"],
                "variant_id": str(variant.id),
                "variant_seed": variant.seed,
                "artifact_hash": variant.content_hash,
                "execution_mode": "memory",
                "started_at": timestamp,
                "completed_at": timestamp,
                "observation_hashes": hashes,
                "artifact_hashes": [content_hash],
            }
            manifest["signature"] = {
                "schema_version": "1.0.0",
                "status": "SIGNED",
                "algorithm": "Ed25519",
                "key_id": "demo-endpoint",
                "value_base64": base64.b64encode(
                    key.sign(b"JOCKY:manifest:v1\n" + rfc8785.dumps(manifest))
                ).decode(),
            }
            ingest_manifest(db, endpoint, manifest, user, store)
            job.status = State(spec["outcome"])
            job.reason = spec["reason"]
            publish(
                db,
                user,
                "hunt.progress",
                hunt.id,
                {"job_id": str(job.id), "state": job.status},
                simulation=True,
                simulation_label=fixture["simulation_label"],
            )
        hunt.endpoint_ids = endpoint_ids
        db.flush()
        summarize(db, hunt)
        case.description = READY
        publish(
            db,
            user,
            "demo.loaded",
            hunt.id,
            {"case_id": str(case_id)},
            simulation=True,
            simulation_label=fixture["simulation_label"],
        )
    return str(case_id)
