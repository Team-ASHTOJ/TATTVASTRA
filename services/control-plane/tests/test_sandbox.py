"""Targeted coverage for the demo Windows sandbox endpoint."""

from datetime import UTC, datetime, timedelta

from jocky_control_plane.models import Endpoint, State
from sqlalchemy import func, select
from test_distributed import runtime

__all__ = ["runtime"]

HOSTNAME = "WINDOWS-SANDBOX-01"


def test_windows_sandbox_start_is_idempotent_and_leaves_real_endpoints_untouched(runtime):
    factory, _, client, org_id, _ = runtime

    # One real Linux endpoint, persisted exactly as a running agent persists it.
    with factory.begin() as db:
        linux = Endpoint(
            organization_id=org_id,
            simulation=False,
            transport_mode="DIRECT",
            hostname="LOCAL-LINUX-01",
            target_os="linux",
            target_arch="x86_64",
            agent_version="test",
            identity="linux-identity",
            public_key="key",
            certificate_fingerprint="linux-fingerprint",
            capabilities=["system.read"],
            execution_modes=["memory"],
            status=State.ONLINE,
            last_seen=datetime.now(UTC),
        )
        db.add(linux)
        db.flush()
        linux_id = linux.id

    first = client.post("/api/endpoints/sandbox/windows")
    assert first.status_code == 200, first.text
    created = first.json()
    assert created["hostname"] == HOSTNAME
    assert created["target_os"] == "windows"
    assert created["target_arch"] == "x86_64"
    assert created["transport_mode"] == "SANDBOX"
    assert created["status"] == "ONLINE"
    assert created["simulation"] is True
    assert created["simulation_label"] == "WINDOWS SANDBOX"
    assert created["execution_modes"] == ["sandbox"]
    assert created["last_seen"]

    # Repeated starts reuse the persisted row instead of creating another.
    repeated = client.post("/api/endpoints/sandbox/windows")
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["id"] == created["id"]
    with factory() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Endpoint).where(Endpoint.hostname == HOSTNAME)
            )
            == 1
        )

    inventory = client.get("/api/endpoints").json()
    sandbox = next(row for row in inventory if row["hostname"] == HOSTNAME)
    assert sandbox["status"] == "ONLINE"
    assert sandbox["simulation"] is True
    # Detail renders through the same layout as a real endpoint.
    detail = client.get(f"/api/endpoints/{created['id']}").json()
    assert detail["status"] == "ONLINE"
    assert detail["transport_mode"] == "SANDBOX"

    # Real endpoint rows are returned exactly as persisted.
    real = next(row for row in inventory if row["id"] == str(linux_id))
    assert real["status"] == "ONLINE"
    assert real["simulation"] is False
    assert real["transport_mode"] == "DIRECT"
    assert real["execution_modes"] == ["memory"]

    # Real heartbeat staleness still downgrades a real endpoint; the sandbox stays ONLINE.
    with factory.begin() as db:
        db.get(Endpoint, linux_id).last_seen = datetime.now(UTC) - timedelta(seconds=120)
    refreshed = client.get("/api/endpoints").json()
    assert next(row for row in refreshed if row["id"] == str(linux_id))["status"] == "OFFLINE"
    assert next(row for row in refreshed if row["hostname"] == HOSTNAME)["status"] == "ONLINE"
