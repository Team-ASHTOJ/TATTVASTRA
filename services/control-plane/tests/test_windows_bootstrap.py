"""Bounded Windows supervisor API and heartbeat authority regressions."""

from datetime import UTC, datetime
from uuid import UUID

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from jocky_control_plane.cli import initialize_keys
from jocky_control_plane.models import Endpoint, EndpointEnrollment, Role, State, User
from jocky_control_plane.security import digest
from sqlalchemy import func, select
from test_distributed import runtime

__all__ = ["runtime"]


def test_external_addresses_and_certificate_come_from_configuration(runtime):
    """An external Windows host is never handed a loopback address."""
    _, settings, client, _, _ = runtime
    # Nothing configured: refuse with an actionable message rather than
    # producing a bootstrap configuration a Windows host could not use.
    refused = client.post("/api/windows-endpoint/bootstrap")
    assert refused.status_code == 503
    assert "JOCKY_AGENT_PUBLIC_HOST" in refused.json()["detail"]

    settings.agent_public_host = "jocky-lab.local"
    assert settings.agent_public_addresses == (
        "https://jocky-lab.local:18443",
        "https://jocky-lab.local:15051",
        "https://jocky-lab.local:15052",
    )
    # An explicitly configured URL still wins over the composed one.
    settings.windows_enrollment_server = "https://relay.example:4443"
    assert settings.agent_public_addresses[2] == "https://relay.example:4443"
    settings.windows_enrollment_server = None

    # The fixture already provisioned a certificate whose SANs hold only the
    # internal names, so this exercises the renewal path rather than issuance.
    ca_before = settings.tls_ca_path.read_bytes()
    key_before = serialization.load_pem_private_key(settings.tls_key_path.read_bytes(), None)
    initialize_keys(settings)
    renewed = x509.load_pem_x509_certificate(settings.tls_cert_path.read_bytes())
    san = renewed.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    # The internal names are untouched and the external host is added, so
    # verification is never relaxed to make the connection work.
    assert "jocky-lab.local" in san.get_values_for_type(x509.DNSName)
    for internal in ("localhost", "control-plane", "agent-control", "trusted-relay"):
        assert internal in san.get_values_for_type(x509.DNSName)
    # Adding an external name must not re-issue the CA or the server key: the
    # trust anchor every enrolled endpoint already holds stays valid.
    assert settings.tls_ca_path.read_bytes() == ca_before
    assert renewed.issuer == x509.load_pem_x509_certificate(ca_before).subject
    assert (
        serialization.load_pem_private_key(settings.tls_key_path.read_bytes(), None).public_key()
        == key_before.public_key()
    )


def test_public_host_registration_carries_reachable_https_addresses(runtime):
    _, settings, client, organization, _ = runtime
    settings.agent_public_host = "192.0.2.10"
    initialize_keys(settings)
    san = (
        x509.load_pem_x509_certificate(settings.tls_cert_path.read_bytes())
        .extensions.get_extension_for_class(x509.SubjectAlternativeName)
        .value
    )
    # A literal address belongs in the certificate as an IP, not as a DNS name.
    assert "192.0.2.10" in [str(address) for address in san.get_values_for_type(x509.IPAddress)]
    registration = client.post("/api/windows-endpoint/bootstrap")
    assert registration.status_code == 201, registration.text
    configuration = registration.json()
    assert configuration["api_url"] == "https://192.0.2.10:18443"
    assert configuration["control_server"] == "https://192.0.2.10:15051"
    assert configuration["enrollment_server"] == "https://192.0.2.10:15052"
    assert configuration["organization_id"] == str(organization)
    assert "BEGIN CERTIFICATE" in configuration["ca_pem"]


def test_registration_start_is_idempotent_and_online_requires_heartbeat(runtime):
    factory, settings, client, organization, _ = runtime
    assert client.get("/api/windows-endpoint/status").json()["state"] == "NOT_CONFIGURED"
    assert client.post("/api/windows-endpoint/start").status_code == 409

    settings.windows_api_url = "https://jocky.test"
    settings.windows_control_server = "https://agent.test:50051"
    settings.windows_enrollment_server = "https://agent.test:50052"
    registration = client.post("/api/windows-endpoint/bootstrap")
    assert registration.status_code == 201, registration.text
    configuration = registration.json()
    credential = {
        "Authorization": (
            f"Bootstrap {configuration['bootstrap_id']}.{configuration['bootstrap_secret']}"
        )
    }
    assert client.post("/api/windows-endpoint/bootstrap").status_code == 409
    # A registered bootstrap is READY — a prepared host, not a connected one.
    assert client.get("/api/windows-endpoint/status").json()["state"] == "READY"
    assert (
        client.post("/api/windows-bootstrap/poll", json={}, headers=credential).status_code == 422
    )
    assert (
        client.post(
            "/api/windows-bootstrap/poll",
            json={"state": "READY", "needs_enrollment": True},
            headers={"Authorization": "Bootstrap invalid.invalid"},
        ).status_code
        == 401
    )

    first_start = client.post("/api/windows-endpoint/start")
    second_start = client.post("/api/windows-endpoint/start")
    assert first_start.status_code == second_start.status_code == 200
    assert first_start.json()["state"] == second_start.json()["state"] == "STARTING"

    first_poll = client.post(
        "/api/windows-bootstrap/poll",
        json={"state": "READY", "needs_enrollment": True},
        headers=credential,
    )
    second_poll = client.post(
        "/api/windows-bootstrap/poll",
        json={"state": "ENROLLING", "needs_enrollment": True},
        headers=credential,
    )
    assert first_poll.status_code == second_poll.status_code == 200
    assert first_poll.json()["action"] == "START"
    for field in ("id", "one_time_token", "ca_pem"):
        assert first_poll.json()["enrollment"][field] == second_poll.json()["enrollment"][field]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(EndpointEnrollment)) == 1

    # A supervisor report alone is never accepted as endpoint connectivity.
    reported = client.post(
        "/api/windows-bootstrap/poll",
        json={"state": "ONLINE", "needs_enrollment": True},
        headers=credential,
    )
    assert reported.status_code == 200
    assert client.get("/api/windows-endpoint/status").json()["state"] == "WAITING_FOR_HEARTBEAT"

    with factory.begin() as db:
        endpoint = Endpoint(
            organization_id=organization,
            simulation=False,
            hostname="WINDOWS-01",
            target_os="windows",
            target_arch="x86_64",
            agent_version="test",
            identity=digest(b"windows-bootstrap-test"),
            public_key="test-key",
            certificate_fingerprint=digest(b"windows-bootstrap-test-certificate"),
            capabilities=["system.read", "process.read", "network.read", "drivers.read"],
            execution_modes=[],
            transport_mode="DIRECT",
            status=State.ONLINE,
            last_seen=datetime.now(UTC),
        )
        db.add(endpoint)
        db.flush()
        enrollment = db.get(EndpointEnrollment, UUID(first_poll.json()["enrollment"]["id"]))
        assert enrollment is not None
        enrollment.endpoint_id = endpoint.id
        enrollment.consumed_at = datetime.now(UTC)
        endpoint_id = endpoint.id

    heartbeat = client.post(
        "/api/windows-bootstrap/poll",
        json={
            "state": "WAITING_FOR_HEARTBEAT",
            "endpoint_id": str(endpoint_id),
            "needs_enrollment": False,
        },
        headers=credential,
    )
    assert heartbeat.status_code == 200, heartbeat.text
    assert heartbeat.json()["authoritative_state"] == "ONLINE"
    status = client.get("/api/windows-endpoint/status").json()
    assert status["state"] == "ONLINE"
    assert status["endpoint"]["hostname"] == "WINDOWS-01"
    assert client.post("/api/windows-endpoint/start").json()["endpoint_id"] == str(endpoint_id)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(EndpointEnrollment)) == 1


def test_windows_mutations_are_admin_only(runtime):
    factory, settings, client, _, admin_id = runtime
    settings.windows_api_url = "https://jocky.test"
    settings.windows_control_server = "https://agent.test:50051"
    settings.windows_enrollment_server = "https://agent.test:50052"
    with factory.begin() as db:
        db.get(User, admin_id).role = Role.ANALYST
    assert client.post("/api/windows-endpoint/bootstrap").status_code == 403
    assert client.post("/api/windows-endpoint/start").status_code == 403
    assert client.post("/api/windows-endpoint/stop").status_code == 403
    assert client.get("/api/windows-endpoint/status").status_code == 403
