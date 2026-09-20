"""Targeted Phase 4 regressions using real persistence and existing protocol boundaries."""

import base64
from datetime import UTC, datetime, timedelta

import pytest
import rfc8785
from fastapi import HTTPException
from jocky_control_plane.generated.jocky.v1 import agent_pb2 as wire
from jocky_control_plane.ingestion import (
    ingest_manifest,
    ingest_observation,
    verify_manifest_document,
)
from jocky_control_plane.models import Artifact, Endpoint, EvidenceManifest, Job, User
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest
from jocky_control_plane.transport import AgentControl
from sqlalchemy import select
from test_distributed import observation_payload, runtime, setup_job

# Reuse the existing isolated PostgreSQL/SQLite fixture; no second model/test database layer.
__all__ = ["runtime"]


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
