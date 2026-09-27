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
