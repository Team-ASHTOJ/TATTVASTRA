"""Local lifecycle boundaries; browser acceptance separately runs the real Rust binary."""

import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from jocky_control_plane import local_agent
from jocky_control_plane.local_launcher import Start, Supervisor, create_app
from jocky_control_plane.models import Endpoint, EndpointEnrollment, Role, State, User
from jocky_control_plane.security import digest
from sqlalchemy import func, select
from test_distributed import runtime

__all__ = ["runtime"]


def test_internal_authentication_fixed_commands_and_failure(tmp_path):
    supervisor = Supervisor(tmp_path / "state")
    supervisor.agent = str(tmp_path / "absent-agent")
    with TestClient(create_app(supervisor, "internal-test-credential")) as client:
        assert client.get("/status").status_code == 401
        headers = {"Authorization": "Bearer internal-test-credential"}
        assert (
            client.post(
                "/start",
                headers=headers,
                json={
                    "organization_id": "00000000-0000-0000-0000-000000000001",
                    "command": "anything",
                },
            ).status_code
            == 422
        )
        started = client.post(
            "/start",
            headers=headers,
            json={"organization_id": "00000000-0000-0000-0000-000000000001"},
        )
        assert started.status_code == 200
        for _ in range(100):
            status = client.get("/status", headers=headers).json()
            if status["state"] == "FAILED":
                break
            time.sleep(0.01)
        assert status["state"] == "FAILED"
        assert "binary is missing" in status["error"]
        assert not (supervisor.root / "enrollment.token").exists()
        restored = Supervisor(supervisor.root)
        assert restored.status()["organization_id"] == status["organization_id"]
        assert restored.status()["state"] == "STOPPED"
        assert (
            client.post(
                "/start",
                headers=headers,
                json={"organization_id": "00000000-0000-0000-0000-000000000002"},
            ).status_code
            == 409
        )


def test_supervisor_reuses_active_operation_and_persisted_identity(tmp_path):
    supervisor = Supervisor(tmp_path)
    supervisor.operation.update(
        state="ENROLLING", organization_id="00000000-0000-0000-0000-000000000001"
    )
    material = Start(organization_id=UUID(supervisor.operation["organization_id"]))
    assert supervisor.start(material)["state"] == "ENROLLING"
    assert supervisor.process is None  # duplicate start never spawns another lifecycle
    (tmp_path / "remote.json").write_text(json.dumps({"endpoint_id": "identity-preserved"}))
    supervisor.save()
    restored = Supervisor(tmp_path)
    assert restored.status()["endpoint_id"] == "identity-preserved"
    assert not restored.status()["needs_enrollment"]


def test_admin_and_tenant_boundaries_and_runtime_unavailable(runtime):
    factory, _, client, _, admin_id = runtime
    for path in ("/api/local-agent/start", "/api/local-agent/stop"):
        assert client.post(path).status_code == 503
    with factory.begin() as db:
        db.get(User, admin_id).role = Role.ANALYST
    for path in ("/api/local-agent/start", "/api/local-agent/stop"):
        assert client.post(path).status_code == 403
    assert client.get("/api/local-agent/status").status_code == 403


def test_online_requires_new_heartbeat_and_start_is_idempotent(runtime, monkeypatch):
    factory, _, client, org_id, _ = runtime
    started = datetime.now(UTC)
    state = {"state": "STOPPED", "needs_enrollment": True}
    calls = []

    # Isolate launcher IO, exercising the real API, transactions and persisted heartbeat derivation.
    def boundary(settings, route, body=None, slot=1):
        calls.append(route)
        if route == "/start":
            state.update(
                state="ENROLLING", organization_id=str(org_id), enrollment_id=body["enrollment_id"]
            )
        return dict(state)

    monkeypatch.setattr(local_agent, "runtime", boundary)
    assert client.post("/api/local-agent/start").json()["state"] == "ENROLLING"
    assert client.post("/api/local-agent/start").json()["state"] == "ENROLLING"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(EndpointEnrollment)) == 1
    assert calls.count("/start") == 1
    with factory.begin() as db:
        endpoint = Endpoint(
            organization_id=org_id,
            simulation=False,
            hostname="LOCAL-LINUX-01",
            target_os="linux",
            target_arch="aarch64",
            agent_version="test",
            identity=digest(b"local"),
            public_key="key",
            certificate_fingerprint=digest(b"local-cert"),
            capabilities=["system.read"],
            status=State.ONLINE,
            last_seen=started - timedelta(seconds=1),
        )
        db.add(endpoint)
        db.flush()
        endpoint_id = endpoint.id
    state.update(
        state="WAITING_FOR_HEARTBEAT",
        connected_at=started.isoformat(),
        endpoint_id=str(endpoint_id),
        needs_enrollment=False,
    )
    assert client.get("/api/local-agent/status").json()["state"] == "WAITING_FOR_HEARTBEAT"
    with factory.begin() as db:
        db.get(Endpoint, endpoint_id).last_seen = datetime.now(UTC)
    assert client.get("/api/local-agent/status").json()["state"] == "ONLINE"
    state["connected_at"] = (started - timedelta(seconds=200)).isoformat()
    with factory.begin() as db:
        db.get(Endpoint, endpoint_id).last_seen = started - timedelta(seconds=100)
    assert client.get("/api/local-agent/status").json()["state"] == "STALE"
    state["organization_id"] = "00000000-0000-0000-0000-000000000002"
    assert client.post("/api/local-agent/start").status_code == 409
    assert client.post("/api/local-agent/stop").status_code == 409
    assert calls.count("/stop") == 0


def test_local_slots_are_bounded_and_isolated(runtime, monkeypatch):
    factory, _, client, org_id, _ = runtime
    states = {slot: {"state": "STOPPED", "needs_enrollment": True} for slot in range(1, 4)}

    def boundary(settings, route, body=None, slot=1):
        if route == "/start":
            states[slot].update(
                state="ENROLLING", organization_id=str(org_id), enrollment_id=body["enrollment_id"]
            )
        return dict(states[slot])

    monkeypatch.setattr(local_agent, "runtime", boundary)
    for slot in range(1, 4):
        assert client.post(f"/api/local-agent/start?slot={slot}").status_code == 200
        assert client.post(f"/api/local-agent/start?slot={slot}").status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(EndpointEnrollment)) == 3
    assert len({row["enrollment_id"] for row in client.get("/api/local-agents").json()}) == 3
    assert client.post("/api/local-agent/start?slot=4").status_code == 422


def enrolled_endpoint(db, org_id, slot):
    """One durable endpoint identity for a single local slot."""
    endpoint = Endpoint(
        organization_id=org_id,
        simulation=False,
        hostname=f"LOCAL-LINUX-0{slot}",
        target_os="linux",
        target_arch="aarch64",
        agent_version="test",
        identity=digest(f"local-{slot}".encode()),
        public_key="key",
        certificate_fingerprint=digest(f"local-cert-{slot}".encode()),
        capabilities=["system.read"],
        status=State.OFFLINE,
    )
    db.add(endpoint)
    db.flush()
    return endpoint.id


def test_three_slots_reach_online_independently_and_stay_isolated(runtime, monkeypatch):
    factory, _, client, org_id, _ = runtime
    started = datetime.now(UTC)
    states = {slot: {"state": "STOPPED", "needs_enrollment": True} for slot in range(1, 4)}
    calls = []

    def boundary(settings, route, body=None, slot=1):
        calls.append((slot, route))
        if route == "/start":
            states[slot].update(
                state="ENROLLING", organization_id=str(org_id), enrollment_id=body["enrollment_id"]
            )
        return dict(states[slot])

    monkeypatch.setattr(local_agent, "runtime", boundary)
    for slot in range(1, 4):
        assert client.post(f"/api/local-agent/start?slot={slot}").status_code == 200
    with factory.begin() as db:
        identities = {slot: enrolled_endpoint(db, org_id, slot) for slot in range(1, 4)}
    assert len(set(identities.values())) == 3
    for slot in range(1, 4):
        states[slot].update(
            state="WAITING_FOR_HEARTBEAT",
            connected_at=started.isoformat(),
            endpoint_id=str(identities[slot]),
            needs_enrollment=False,
        )
    # No slot is promoted by another slot's launcher report.
    assert [row["state"] for row in client.get("/api/local-agents").json()] == [
        "WAITING_FOR_HEARTBEAT"
    ] * 3
    assert len({row["endpoint_id"] for row in client.get("/api/local-agents").json()}) == 3
    # Only the slot holding its own authenticated heartbeat becomes ONLINE.
    with factory.begin() as db:
        db.get(Endpoint, identities[2]).last_seen = datetime.now(UTC)
    assert [row["state"] for row in client.get("/api/local-agents").json()] == [
        "WAITING_FOR_HEARTBEAT",
        "ONLINE",
        "WAITING_FOR_HEARTBEAT",
    ]
    # All three can hold fresh heartbeats at the same time.
    with factory.begin() as db:
        for slot in (1, 3):
            db.get(Endpoint, identities[slot]).last_seen = datetime.now(UTC)
    assert [row["state"] for row in client.get("/api/local-agents").json()] == ["ONLINE"] * 3
    # A start against an already ONLINE slot is idempotent and never touches
    # another slot's runtime.
    before = len(calls)
    assert client.post("/api/local-agent/start?slot=1").json()["state"] == "ONLINE"
    assert [call for call in calls[before:] if call[1] in {"/start", "/stop"}] == []


def test_failed_slot_retry_reuses_its_identity_and_recovers(runtime, monkeypatch):
    factory, _, client, org_id, _ = runtime
    calls = []

    def boundary(settings, route, body=None, slot=1):
        calls.append((slot, route))
        if route == "/stop":
            state.update(state="STOPPED", error=None)
        if route == "/start":
            state.update(state="WAITING_FOR_HEARTBEAT", connected_at=datetime.now(UTC).isoformat())
        return dict(state)

    state = {"state": "FAILED", "needs_enrollment": False}
    monkeypatch.setattr(local_agent, "runtime", boundary)
    with factory.begin() as db:
        state["endpoint_id"] = str(enrolled_endpoint(db, org_id, 2))
    state["error"] = "Authenticated heartbeat timed out. Check AgentControl, then retry."
    status = client.get("/api/local-agent/status?slot=2").json()
    assert status["state"] == "FAILED"
    assert "heartbeat timed out" in status["error"]
    recovered = client.post("/api/local-agent/start?slot=2")
    assert recovered.status_code == 200
    assert recovered.json()["state"] == "WAITING_FOR_HEARTBEAT"
    # The retry restarts the same slot instead of spawning a second lifecycle.
    assert [call for call in calls if call[1] in {"/start", "/stop"}] == [
        (2, "/stop"),
        (2, "/start"),
    ]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Endpoint)) == 1
        assert db.scalar(select(func.count()).select_from(EndpointEnrollment)) == 0


def test_windows_not_configured_leaves_local_slots_untouched(runtime, monkeypatch):
    factory, _, client, org_id, _ = runtime
    states = {slot: {"state": "STOPPED", "needs_enrollment": True} for slot in range(1, 4)}
    calls = []

    def boundary(settings, route, body=None, slot=1):
        calls.append((slot, route))
        if route == "/start":
            states[slot].update(
                state="ENROLLING", organization_id=str(org_id), enrollment_id=body["enrollment_id"]
            )
        return dict(states[slot])

    monkeypatch.setattr(local_agent, "runtime", boundary)
    windows = client.get("/api/windows-endpoint/status").json()
    assert windows["configured"] is False
    assert windows["state"] == "NOT_CONFIGURED"
    # An unconfigured Windows endpoint is a statement about Windows only: it
    # never contacts or blocks a local Linux runtime.
    assert calls == []
    assert client.post("/api/local-agent/start?slot=2").json()["state"] == "ENROLLING"
    assert [call for call in calls if call[1] in {"/start", "/stop"}] == [(2, "/start")]
