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


def test_recent_inventory_window_preserves_new_resources(runtime):
    factory, _, client, org_id, _ = runtime
    from datetime import timedelta

    start = datetime.now(UTC)
    with factory.begin() as db:
        rows = [
            Case(
                organization_id=org_id,
                title=f"Inventory {i}",
                created_at=start + timedelta(seconds=i),
            )
            for i in range(501)
        ]
        db.add_all(rows)
        db.flush()
        newest = str(rows[-1].id)
        oldest = str(rows[0].id)
    inventory = client.get("/api/cases?limit=500").json()
    assert len(inventory) == 500
    assert inventory[-1]["id"] == newest
    assert oldest not in {row["id"] for row in inventory}
    default_window = client.get("/api/cases").json()
    assert len(default_window) == 100
    assert default_window[-1]["id"] == newest
    assert client.get(f"/api/cases/{oldest}").status_code == 200
