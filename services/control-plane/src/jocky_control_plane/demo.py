"""Backend-only, explicitly simulated fixture import using real compiler output."""

import base64
import json
from datetime import UTC, datetime
from importlib.resources import files
from uuid import uuid4

import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane.builds import build_variants, compile_version
from jocky_control_plane.config import Settings
from jocky_control_plane.hunts import envelope, summarize
from jocky_control_plane.ingestion import ingest_manifest, ingest_observation
from jocky_control_plane.investigation import graph
from jocky_control_plane.models import (
    Case,
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
from jocky_control_plane.security import digest, provenance, publish


def load(factory: sessionmaker[Session], settings: Settings) -> None:
    if settings.mode != "DEMO":
        raise RuntimeError("DEMO fixture loader requires JOCKY_MODE=DEMO")
    fixture = json.loads(files("jocky_control_plane").joinpath("data/demo.json").read_text())
    with factory.begin() as db:
        user = db.scalar(
            select(User).where(User.role == Role.ADMIN, User.disabled.is_(False)).limit(1)
        )
        if user is None:
            raise RuntimeError("Initialize the organization first")
        case = Case(
            organization_id=user.organization_id,
            title=fixture["title"],
            simulation=True,
            simulation_label=fixture["simulation_label"],
        )
        db.add(case)
        db.flush()
        script = Script(**provenance(case), case_id=case.id, name="Demo investigation")
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
    # Compilation commits measured stage events; do not wrap it in another begin.
    with factory() as db:
        user = db.get(User, user_id)
        loaded_version = db.get(ScriptVersion, version_id)
        assert user is not None and loaded_version is not None
        version = loaded_version
        compilation = compile_version(db, version, user, settings)
        if compilation.status != State.SUCCESS:
            raise RuntimeError(f"Demo requires the native compiler: {compilation.error}")
        compilation_id = compilation.id
    with factory.begin() as db:
        from jocky_control_plane.models import Compilation

        user = db.get(User, user_id)
        loaded_version = db.get(ScriptVersion, version_id)
        loaded_compilation = db.get(Compilation, compilation_id)
        assert user is not None and loaded_version is not None and loaded_compilation is not None
        version = loaded_version
        compilation = loaded_compilation
        variant = build_variants(db, compilation, version, 1, user, settings)[0]
        plan = ExecutionPlan(
            **provenance(version),
            compilation_id=compilation.id,
            document=compilation.outputs["plan"],
        )
        db.add(plan)
        db.flush()
        key = Ed25519PrivateKey.generate()
        endpoint = Endpoint(
            **provenance(version),
            hostname="DEMO-01",
            target_os="linux",
            target_arch="x86_64",
            agent_version="DEMO_FIXTURE",
            identity=digest(key.public_key().public_bytes_raw()),
            public_key=base64.b64encode(key.public_key().public_bytes_raw()).decode(),
            certificate_fingerprint=digest(b"demo-fixture:" + key.public_key().public_bytes_raw()),
            capabilities=plan.document["required_capabilities"],
            execution_modes=[],
            status=State.OFFLINE,
        )
        db.add(endpoint)
        db.flush()
        hunt = Hunt(
            **provenance(version),
            case_id=case_id,
            compilation_id=compilation.id,
            endpoint_ids=[str(endpoint.id)],
            execution_mode="native",
            status=State.RUNNING,
        )
        db.add(hunt)
        db.flush()
        job = Job(
            **provenance(version),
            hunt_id=hunt.id,
            endpoint_id=endpoint.id,
            variant_id=variant.id,
            plan_id=plan.id,
            status=State.RUNNING,
            reason="BACKEND_DEMO_FIXTURE",
        )
        db.add(job)
        db.flush()
        job.envelope = envelope(job, hunt, plan, variant, settings)
        hashes = []
        timestamp = datetime.now(UTC).isoformat()
        for record in fixture["observations"]:
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
            "execution_mode": "native",
            "started_at": timestamp,
            "completed_at": timestamp,
            "observation_hashes": hashes,
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
        ingest_manifest(db, endpoint, manifest, user)
        job.status = State.SUCCESS
        db.flush()
        summarize(db, hunt)
        graph(db, case_id, user)
        publish(
            db,
            user,
            "demo.loaded",
            hunt.id,
            simulation=True,
            simulation_label=fixture["simulation_label"],
        )
        print(f"Loaded DEMO case {case_id}; endpoint is a backend fixture, not an enrolled host")
