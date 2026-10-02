"""Targeted Phase 4 regressions using real persistence and existing protocol boundaries."""

import base64
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import rfc8785
from fastapi import HTTPException
from jocky_control_plane import hunts
from jocky_control_plane.generated.jocky.v1 import agent_pb2 as wire
from jocky_control_plane.ingestion import (
    ingest_manifest,
    ingest_observation,
    verify_manifest_document,
)
from jocky_control_plane.models import (
    Artifact,
    Case,
    Compilation,
    Endpoint,
    EventOutbox,
    EvidenceManifest,
    ExecutionPlan,
    Hunt,
    Job,
    Observation,
    Script,
    ScriptVersion,
    State,
    User,
    Variant,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest, provenance
from jocky_control_plane.transport import AgentControl
from sqlalchemy import select
from test_distributed import observation_payload, runtime, setup_job

# Reuse the existing isolated PostgreSQL/SQLite fixture; no second model/test database layer.
__all__ = ["runtime"]


def _orchestration_fixture(factory, org_id):
    with factory.begin() as db:
        user = db.scalar(
            select(User).where(User.organization_id == org_id, User.username == "admin")
        )
        case = Case(
            organization_id=org_id,
            title="Multi-endpoint orchestration",
            simulation=False,
        )
        db.add(case)
        db.flush()
        script = Script(**provenance(case), case_id=case.id, name="Inventory")
        db.add(script)
        db.flush()
        version = ScriptVersion(
            **provenance(case),
            script_id=script.id,
            version=1,
            source="remote inventory",
            source_hash=digest(b"remote inventory"),
        )
        db.add(version)
        db.flush()
        compilation = Compilation(
            **provenance(case),
            script_version_id=version.id,
            status=State.SUCCESS,
            outputs={
                "plan": {
                    "source_hash": version.source_hash,
                    "jir_hash": digest(b"jir"),
                    "target_os": ["linux"],
                    "required_capabilities": ["system.read"],
                    "budget": {
                        "schema_version": "1.0.0",
                        "cpu_percent": 20,
                        "memory_bytes": 256000000,
                        "io_bytes": 150000000,
                        "duration_ms": 120000,
                    },
                },
                "jir": {"instructions": [{"opcode": "SYSTEM_INFO", "attributes": {"options": {}}}]},
            },
        )
        db.add(compilation)
        db.flush()
        endpoints = []
        for label, modes in (("A", ["memory"]), ("B", ["native"]), ("C", ["memory"])):
            endpoint = Endpoint(
                **provenance(case),
                hostname=f"ENDPOINT-{label}",
                target_os="linux",
                target_arch="x86_64",
                agent_version="test",
                identity=digest(f"identity-{label}".encode()),
                public_key=f"key-{label}",
                certificate_fingerprint=digest(f"cert-{label}".encode()),
                capabilities=["system.read"],
                execution_modes=modes,
                last_seen=datetime.now(UTC),
                status=State.ONLINE,
            )
            db.add(endpoint)
            endpoints.append(endpoint)
        db.flush()
        hunt = Hunt(
            **provenance(case),
            case_id=case.id,
            compilation_id=compilation.id,
            endpoint_ids=[str(endpoint.id) for endpoint in endpoints],
            execution_mode="memory",
            endpoint_modes={
                str(endpoints[0].id): "memory",
                str(endpoints[1].id): "native",
                str(endpoints[2].id): "memory",
            },
            diverse=True,
            retry_limit=1,
        )
        db.add(hunt)
        db.flush()
        return user.id, hunt.id, compilation.id, [endpoint.id for endpoint in endpoints]


def test_multi_endpoint_hunt_isolates_variants_failures_retries_and_evidence(runtime, monkeypatch):
    factory, settings, _, org_id, _ = runtime
    user_id, hunt_id, compilation_id, endpoint_ids = _orchestration_fixture(factory, org_id)
    builds = []

    def build_for_endpoint(
        db, compilation, version, count, user, build_settings, *, execution_mode
    ):
        builds.append(execution_mode)
        content = f"artifact-{len(builds)}".encode()
        variant = Variant(
            **provenance(compilation),
            compilation_id=compilation.id,
            seed=f"{len(builds):016x}",
            manifest={
                "artifact_hash": digest(content),
                "target_triple": "x86_64-unknown-linux-gnu",
                "execution_mode": execution_mode,
                "variant_seed": f"{len(builds):016x}",
                "llvm_ir_hash": digest(b"llvm"),
            },
            content_hash=digest(content),
            storage_key=digest(content),
        )
        db.add(variant)
        db.flush()
        return [variant]

    monkeypatch.setattr(hunts, "build_variants", build_for_endpoint)
    with factory.begin() as db:
        hunts.start(db, db.get(Hunt, hunt_id), db.get(User, user_id), settings)

    with factory.begin() as db:
        jobs = db.scalars(select(Job).where(Job.hunt_id == hunt_id).order_by(Job.created_at)).all()
        assert len(jobs) == 3
        assert builds == ["memory", "native", "memory"]
        assert jobs[0].status == State.QUEUED
        assert jobs[1].status == State.QUEUED
        assert jobs[2].status == State.QUEUED
        assert jobs[0].envelope["execution_mode"] == "memory"
        assert jobs[2].envelope["execution_mode"] == "memory"
        assert jobs[0].variant_id != jobs[2].variant_id
        assert jobs[0].envelope["source_hash"] == jobs[2].envelope["source_hash"]
        assert jobs[0].envelope["plan_id"] == jobs[2].envelope["plan_id"]
        hunt = db.get(Hunt, hunt_id)
        assert hunt.status == State.RUNNING

        user = db.get(User, user_id)
        for job in (jobs[0], jobs[2]):
            hunts.transition(db, job, State.DISPATCHED, user, settings)
            hunts.transition(db, job, State.RUNNING, user, settings)
        hunts.transition(db, jobs[1], State.DISPATCHED, user, settings)
        hunts.transition(db, jobs[1], State.RUNNING, user, settings)
        hunts.transition(db, jobs[0], State.SUCCESS, user, settings, "Endpoint A complete")
        hunts.transition(db, jobs[2], State.SUCCESS, user, settings, "Endpoint C complete")
        hunts.transition(db, jobs[1], State.FAILED, user, settings, "Endpoint B runtime failure")
        retry = db.scalar(select(Job).where(Job.retry_of == jobs[1].id))
        assert retry is not None
        assert retry.endpoint_id == jobs[1].endpoint_id
        assert retry.attempt == 2
        assert retry.variant_id == jobs[1].variant_id
        assert len(db.scalars(select(Job).where(Job.hunt_id == hunt_id)).all()) == 4
        hunts.transition(db, retry, State.FAILED, user, settings, "Endpoint B retry failed")

        for job, endpoint in ((jobs[0], endpoint_ids[0]), (jobs[2], endpoint_ids[2])):
            evidence = {"job_id": str(job.id), "endpoint_id": str(endpoint), "simulation": False}
            db.add(
                Observation(
                    **provenance(job),
                    case_id=hunt.case_id,
                    job_id=job.id,
                    endpoint_id=endpoint,
                    producer_id=str(uuid4()),
                    collector="system",
                    integrity_hash=digest(rfc8785.dumps(evidence)),
                    document=evidence,
                )
            )
        db.flush()
        assert db.get(Hunt, hunt_id).status == State.PARTIAL
        observations = db.scalars(
            select(Observation).where(Observation.job_id.in_([jobs[0].id, jobs[2].id]))
        ).all()
        assert len(observations) == 2
        assert {observation.endpoint_id for observation in observations} == {
            endpoint_ids[0],
            endpoint_ids[2],
        }
        assert (
            db.scalar(select(Job).where(Job.endpoint_id == endpoint_ids[0], Job.attempt == 2))
            is None
        )
        assert (
            db.scalar(select(Job).where(Job.endpoint_id == endpoint_ids[2], Job.attempt == 2))
            is None
        )


@pytest.mark.parametrize(
    ("correctness", "alert", "expected_status"),
    [("FAIL", "NOT_OBSERVED", State.INCOMPATIBLE), ("PASS", "YES", State.QUEUED)],
)
def test_recorded_compatibility_failure_is_endpoint_scoped(
    runtime, monkeypatch, correctness, alert, expected_status
):
    factory, settings, client, org_id, _ = runtime
    user_id, hunt_id, compilation_id, endpoint_ids = _orchestration_fixture(factory, org_id)

    def build_variant(db, compilation, version, count, user, build_settings, *, execution_mode):
        content = f"compatible-{execution_mode}".encode()
        variant = Variant(
            **provenance(compilation),
            compilation_id=compilation.id,
            seed="1" * 16,
            manifest={
                "artifact_hash": digest(content),
                "target_triple": "x86_64-unknown-linux-gnu",
                "execution_mode": execution_mode,
            },
            content_hash=digest(content),
            storage_key=digest(content),
        )
        db.add(variant)
        db.flush()
        return [variant]

    monkeypatch.setattr(hunts, "build_variants", build_variant)
    with factory.begin() as db:
        compilation = db.get(Compilation, compilation_id)
        compatibility_variant = Variant(
            **provenance(compilation),
            compilation_id=compilation.id,
            seed="2" * 16,
            manifest={"target_triple": "x86_64-unknown-linux-gnu"},
            content_hash=digest(b"compatibility"),
            storage_key=digest(b"compatibility"),
        )
        db.add(compatibility_variant)
        db.flush()
        db.flush()
        variant_id = compatibility_variant.id
    recorded = client.post(
        "/api/compatibility-runs",
        json={
            "variant_id": str(variant_id),
            "endpoint_id": str(endpoint_ids[1]),
            "environment": "linux-x86_64",
            "security_product_label": "not-measured",
            "correctness": correctness,
            "alert_observed": alert,
            "notes": "recorded endpoint compatibility failure",
        },
    )
    assert recorded.status_code == 201, recorded.text
    with factory.begin() as db:
        hunts.start(db, db.get(Hunt, hunt_id), db.get(User, user_id), settings)
        jobs = db.scalars(select(Job).where(Job.hunt_id == hunt_id).order_by(Job.created_at)).all()
        assert jobs[1].status == expected_status
        if correctness == "FAIL":
            assert "compatibility" in jobs[1].reason.lower()
        assert jobs[0].status == State.QUEUED
        assert jobs[2].status == State.QUEUED


def test_variant_build_failure_does_not_fail_other_endpoints(runtime, monkeypatch):
    factory, settings, _, org_id, _ = runtime
    user_id, hunt_id, _, endpoint_ids = _orchestration_fixture(factory, org_id)
    calls = 0

    def fail_first_build(db, compilation, version, count, user, build_settings, *, execution_mode):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HTTPException(422, "Endpoint A build failed")
        content = f"artifact-{calls}".encode()
        variant = Variant(
            **provenance(compilation),
            compilation_id=compilation.id,
            seed=f"{calls:016x}",
            manifest={
                "artifact_hash": digest(content),
                "target_triple": "x86_64-unknown-linux-gnu",
                "execution_mode": execution_mode,
            },
            content_hash=digest(content),
            storage_key=digest(content),
        )
        db.add(variant)
        db.flush()
        return [variant]

    monkeypatch.setattr(hunts, "build_variants", fail_first_build)
    with factory.begin() as db:
        hunts.start(db, db.get(Hunt, hunt_id), db.get(User, user_id), settings)
        jobs = db.scalars(select(Job).where(Job.hunt_id == hunt_id).order_by(Job.created_at)).all()
        assert jobs[0].endpoint_id == endpoint_ids[0]
        assert jobs[0].status == State.FAILED
        assert jobs[1].status == State.QUEUED
        assert jobs[2].status == State.QUEUED
        assert jobs[1].variant_id is not None
        assert jobs[2].variant_id is not None
        assert db.get(Hunt, hunt_id).status == State.RUNNING


def test_benchmark_and_compatibility_contracts_persist_and_publish(runtime, monkeypatch):
    factory, settings, client, org_id, admin_id = runtime
    ids = setup_job(factory, org_id, simulation=False)
    with factory() as db:
        job = db.get(Job, ids[2])
        compilation_id = db.get(ExecutionPlan, job.plan_id).compilation_id

    def fixture_compile(*args, **kwargs):
        return {
            "simulation": True,
            "simulation_label": "DETERMINISTIC_COMPILER_FIXTURE",
            "result": {"ok": True},
        }

    monkeypatch.setattr("jocky_control_plane.reporting.invoke_compiler", fixture_compile)
    benchmark = client.post(
        "/api/benchmarks",
        json={"compilation_id": str(compilation_id), "repetitions": 2},
    )
    assert benchmark.status_code == 201, benchmark.text
    assert benchmark.json()["status"] == "SUCCESS"
    listed_benchmarks = client.get("/api/benchmarks")
    assert listed_benchmarks.status_code == 200
    assert any(row["id"] == benchmark.json()["id"] for row in listed_benchmarks.json())

    compatibility = client.post(
        "/api/compatibility-runs",
        json={
            "variant_id": str(ids[4]),
            "endpoint_id": str(ids[3]),
            "environment": "linux-x86_64",
            "security_product_label": "not-measured",
            "correctness": "PASS",
            "alert_observed": "NOT_OBSERVED",
            "notes": "bounded backend contract fixture",
        },
    )
    assert compatibility.status_code == 201, compatibility.text
    assert compatibility.json()["observations"]["correctness"] == "PASS"
    listed_compatibility = client.get("/api/compatibility-runs")
    assert listed_compatibility.status_code == 200
    assert any(row["id"] == compatibility.json()["id"] for row in listed_compatibility.json())
    with factory() as db:
        topics = [row.topic for row in db.query(EventOutbox).all()]
        assert "benchmark.completed" in topics
        assert "compatibility.recorded" in topics


def manifest_for(db, ids, hashes, artifacts=()):
    job, endpoint = db.get(Job, ids[2]), db.get(Endpoint, ids[3])
    now = datetime.now(UTC).isoformat()
    body = {
        "schema_version": "1.0.0",
        "simulation": job.simulation,
        "simulation_label": job.simulation_label,
        "case_id": str(ids[0]),
        "job_id": str(ids[2]),
        "endpoint_id": str(ids[3]),
        "agent_identity": endpoint.identity,
        **job.envelope,
        "llvm_ir_hash": digest(b"fixture-llvm"),
        "variant_seed": "0" * 16,
        "started_at": now,
        "completed_at": now,
        "observation_hashes": hashes,
        "artifact_hashes": list(artifacts),
    }
    body.pop("signature", None)
    body["signature"] = {
        "status": "SIGNED",
        "algorithm": "Ed25519",
        "key_id": "test-fixture",
        "value_base64": base64.b64encode(
            ids[5].sign(b"JOCKY:manifest:v1\n" + rfc8785.dumps(body))
        ).decode(),
    }
    return body


def artifact_frame(ids, content, sequence=1):
    return wire.AgentFrame(
        schema_version="1.0.0",
        endpoint_id=str(ids[3]),
        sequence=sequence,
        simulation=True,
        artifact=wire.CanonicalDocument(
            json_utf8=rfc8785.dumps(
                {
                    "job_id": str(ids[2]),
                    "simulation": True,
                    "simulation_label": "TEST_FIXTURE",
                    "content_base64": base64.b64encode(content).decode(),
                    "content_hash": digest(content),
                    "media_type": "application/json",
                }
            )
        ),
    )


def test_uploaded_artifact_is_signed_sealed_idempotent_and_rehashed(runtime):
    factory, settings, client, org_id, admin_id = runtime
    ids = setup_job(factory, org_id, simulation=True)
    service = AgentControl(factory, settings)
    with factory() as db:
        fingerprint = db.get(Endpoint, ids[3]).certificate_fingerprint
    content = b'{"simulation":true,"simulation_label":"TEST_FIXTURE"}'
    receipt = service.accept(artifact_frame(ids, content), fingerprint)
    assert service.accept(artifact_frame(ids, content), fingerprint) == receipt
    service.accept(artifact_frame(ids, content, 2), fingerprint)
    store = ObjectStore(settings.object_root)
    with factory.begin() as db:
        artifacts = db.scalars(select(Artifact).where(Artifact.job_id == ids[2])).all()
        assert len(artifacts) == 1
        endpoint, user = db.get(Endpoint, ids[3]), db.get(User, admin_id)
        with pytest.raises(HTTPException):
            ingest_manifest(db, endpoint, manifest_for(db, ids, []), user, store)
        manifest = ingest_manifest(
            db, endpoint, manifest_for(db, ids, [], [digest(content)]), user, store
        )
        identifier = manifest.id
        assert verify_manifest_document(db, manifest, user, store)["integrity_valid"]
    with pytest.raises(HTTPException, match="sealed"):
        service.accept(artifact_frame(ids, b"late fixture", 3), fingerprint)
    assert client.post(f"/api/manifests/{identifier}/verify").json()["integrity_valid"]
    store.path(digest(content)).write_bytes(b"tampered")
    checked = client.post(f"/api/manifests/{identifier}/verify").json()
    assert not checked["integrity_valid"] and not checked["artifact_content_valid"]


def test_manifest_future_timestamp_and_late_observation_rejected(runtime):
    factory, _, _, org_id, admin_id = runtime
    ids = setup_job(factory, org_id, simulation=True)
    with factory.begin() as db:
        endpoint, user = db.get(Endpoint, ids[3]), db.get(User, admin_id)
        signed = manifest_for(db, ids, [])
        invalid = dict(signed, completed_at=(datetime.now(UTC) + timedelta(days=1)).isoformat())
        row = EvidenceManifest(
            job_id=ids[2],
            document=invalid,
            simulation=True,
            simulation_label="TEST_FIXTURE",
            signature_verified=False,
        )
        assert not verify_manifest_document(db, row, user)["timestamps_valid"]
        ingest_manifest(db, endpoint, signed, user)
        with pytest.raises(HTTPException, match="sealed"):
            ingest_observation(db, endpoint, observation_payload(db, ids, "system", {}), user)


def test_timeline_severity_source_time_and_range_filters(runtime):
    factory, _, client, org_id, admin_id = runtime
    ids = setup_job(factory, org_id, simulation=True)
    source_time = datetime.now(UTC) - timedelta(hours=1)
    with factory.begin() as db:
        payload = observation_payload(db, ids, "events", {"severity": "high"})
        payload["source_time"] = source_time.isoformat()
        payload["integrity_hash"] = digest(
            rfc8785.dumps({k: v for k, v in payload.items() if k != "integrity_hash"})
        )
        ingest_observation(db, db.get(Endpoint, ids[3]), payload, db.get(User, admin_id))
    filters = {
        "case_id": str(ids[0]),
        "endpoint_id": str(ids[3]),
        "collector": "events",
        "severity": "HIGH",
        "type": "events",
        "start": (source_time - timedelta(seconds=1)).isoformat(),
        "end": (source_time + timedelta(seconds=1)).isoformat(),
    }
    result = client.get("/api/timeline", params=filters)
    assert result.status_code == 200 and len(result.json()) == 1
    assert result.json()[0]["time_basis"] == "source"
    assert client.get("/api/timeline", params={**filters, "severity": "LOW"}).json() == []
    assert (
        client.get("/api/timeline", params={**filters, "start": "2026-01-01T00:00:00"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/timeline", params={**filters, "start": filters["end"], "end": filters["start"]}
        ).status_code
        == 422
    )


def test_all_graph_relationships_and_ambiguous_pid_reuse(runtime):
    from jocky_control_plane.investigation import graph

    factory, _, client, org_id, admin_id = runtime
    ids = setup_job(factory, org_id, simulation=True)
    with factory.begin() as db:
        endpoint, user = db.get(Endpoint, ids[3]), db.get(User, admin_id)
        for collector, data in [
            (
                "processes",
                {
                    "pid": 42,
                    "user": "fixture-user",
                    "signed": False,
                    "start_time": "2026-01-01T00:00:00Z",
                },
            ),
            (
                "connections",
                {"pid": 42, "remote": "8.8.8.8", "process_start_time": "2026-01-01T00:00:00Z"},
            ),
            ("file_metadata", {"pid": 42, "path": "/fixture/file"}),
            ("services", {"pid": 42, "name": "fixture-service"}),
            ("drivers", {"name": "fixture-driver"}),
            ("connections", {"pid": None, "remote": "1.1.1.1"}),
        ]:
            ingest_observation(db, endpoint, observation_payload(db, ids, collector, data), user)
        result = graph(db, ids[0], user)
        assert {e["relationship"] for e in result["edges"]} >= {
            "Endpoint -> Process",
            "User -> Process",
            "Process -> Connection",
            "Process -> File",
            "Process -> Service",
            "Endpoint -> Driver",
            "Connection -> IP",
            "Finding -> Observation",
        }
        assert all(
            item["simulation"] and item["simulation_label"]
            for item in result["nodes"] + result["edges"]
        )
        assert (
            len(client.get("/api/findings", params={"case_id": str(ids[0])}).json()) == 0
        )  # uncommitted
        ingest_observation(
            db,
            endpoint,
            observation_payload(
                db, ids, "processes", {"pid": 99, "signed": False, "start_time": "first"}
            ),
            user,
        )
        ingest_observation(
            db,
            endpoint,
            observation_payload(
                db, ids, "processes", {"pid": 99, "signed": False, "start_time": "second"}
            ),
            user,
        )
        ingest_observation(
            db,
            endpoint,
            observation_payload(db, ids, "connections", {"pid": 99, "remote": "8.8.4.4"}),
            user,
        )
    assert len(client.get("/api/findings", params={"case_id": str(ids[0])}).json()) == 1
