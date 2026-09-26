"""Product integration: identity-bound enrollment and truthful stored-byte checks."""

from datetime import UTC, datetime
from uuid import UUID

from jocky_control_plane.models import Artifact, Case, Endpoint, EndpointEnrollment, State
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest, provenance
from test_distributed import runtime

__all__ = ["runtime"]


def test_enrollment_waits_for_its_authenticated_endpoint_heartbeat(runtime):
    factory, settings, client, org_id, _ = runtime
    issued = client.post(
        "/api/endpoints/enrollments", json={"simulation": False, "capabilities": ["system.read"]}
    )
    assert issued.status_code == 201
    identifier = issued.json()["id"]
    assert issued.json()["one_time_token"]
    assert client.get(f"/api/endpoints/enrollments/{identifier}").json()["state"] == "WAITING"
    with factory.begin() as db:
        enrollment = db.get(EndpointEnrollment, UUID(identifier))
        endpoint = Endpoint(
            organization_id=org_id,
            simulation=False,
            hostname="authorized",
            target_os="linux",
            target_arch="x86_64",
            agent_version="test",
            identity=digest(b"identity"),
            public_key="key",
            certificate_fingerprint=digest(b"cert"),
            capabilities=["system.read"],
            status=State.OFFLINE,
        )
        db.add(endpoint)
        db.flush()
        endpoint_id = endpoint.id
        enrollment.endpoint_id = endpoint_id
    assert client.get(f"/api/endpoints/enrollments/{identifier}").json()["state"] == "STALE"
    with factory.begin() as db:
        endpoint = db.get(Endpoint, endpoint_id)
        endpoint.last_seen = datetime.now(UTC)
        endpoint.status = State.ONLINE
    assert client.get(f"/api/endpoints/enrollments/{identifier}").json()["state"] == "ONLINE"


def test_artifact_validity_requires_accessible_matching_content_and_hashes(runtime):
    factory, settings, client, org_id, _ = runtime
    store = ObjectStore(settings.object_root)
    hashed = store.put(b"forensic content")
    with factory.begin() as db:
        case = Case(organization_id=org_id, simulation=False, title="Integrity")
        db.add(case)
        db.flush()
        artifact = Artifact(
            **provenance(case),
            case_id=case.id,
            content_hash=hashed,
            storage_key=hashed,
            size_bytes=len(b"forensic content"),
            media_type="text/plain",
        )
        db.add(artifact)
        db.flush()
        identifier = artifact.id
    valid = client.post(f"/api/artifacts/{identifier}/verify").json()
    assert valid["available"] and valid["integrity_valid"]
    assert valid["expected_hash"] == valid["computed_hash"] == hashed
    store.path(hashed).unlink()
    unavailable = client.post(f"/api/artifacts/{identifier}/verify").json()
    assert not unavailable["available"] and not unavailable["integrity_valid"]
    assert unavailable["expected_hash"] == hashed and unavailable["computed_hash"] is None
