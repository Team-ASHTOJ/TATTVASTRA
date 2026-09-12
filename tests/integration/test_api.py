import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jocky_control_plane.app import create_app
from jocky_control_plane.config import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client():
    return TestClient(create_app(Settings(environment="test")))


def test_liveness_is_distinct_from_execution_readiness(client):
    assert client.get("/health/live").status_code == 200
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"


def test_no_fabricated_real_endpoint_inventory(client):
    result = client.get("/api/v1/endpoints")
    assert result.status_code == 200
    assert result.json()["items"] == []
    assert result.json()["available"] is False
    assert result.json()["simulation"] is False


def test_compiler_reports_unavailable_without_fake_output(client):
    response = client.post(
        "/api/v1/compilations",
        json={
            "simulation": False,
            "source": 'hunt "test" {}',
            "target": {"os": "linux", "arch": "aarch64"},
            "execution_mode": "memory",
        },
    )
    assert response.status_code == 501
    assert response.json()["code"] == "JOCKY_E_COMPILER_UNAVAILABLE"
    assert "artifact_hash" not in response.json()
    assert response.headers["x-request-id"] == response.json()["request_id"]


def test_schema_error_does_not_echo_sensitive_input(client):
    response = client.post("/api/v1/compilations", json={"source": "sensitive-fixture-token"})
    assert response.status_code == 422
    assert "sensitive-fixture-token" not in response.text


def test_verifier_recomputes_content_and_detects_tampering(client):
    observation = json.loads((ROOT / "fixtures/evidence/simulated-observation.json").read_text())
    valid = client.post("/api/v1/evidence/verify-observation", json=observation)
    assert valid.status_code == 200
    assert valid.json()["integrity_valid"] is True
    assert valid.json()["signature_status"] == "NOT_CHECKED"
    assert valid.json()["simulation"] is True
    observation["data"]["hostname"] = "tampered-host"
    invalid = client.post("/api/v1/evidence/verify-observation", json=observation)
    assert invalid.status_code == 200
    assert invalid.json()["integrity_valid"] is False
    assert invalid.json()["computed_hash"] != invalid.json()["expected_hash"]


def test_noncanonical_large_integer_is_rejected_without_server_error(client):
    observation = json.loads((ROOT / "fixtures/evidence/simulated-observation.json").read_text())
    observation["data"]["unsafe_number"] = 2**64
    response = client.post("/api/v1/evidence/verify-observation", json=observation)
    assert response.status_code == 422
    assert response.json()["code"] == "JOCKY_E_CANONICAL_JSON"


def test_actual_request_counter_increments(client):
    client.get("/health/live")
    response = client.get("/metrics")
    assert 'jocky_http_requests_total{method="GET",status="200"} 1.0' in response.text


def test_status_catalog_is_unique_and_retains_restricted_mappings(client):
    response = client.get("/api/v1/status")
    data = response.json()
    assert data["operational"] is False
    assert data["mode"] == "REAL"
    ids = [item["id"] for item in data["capabilities"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 122
    assert all(f"SAFE-{number:02}" in ids for number in range(1, 12))
    assert all(f"COL-{number:02}" in ids for number in range(1, 18))
    assert all(f"UI-{number:02}" in ids for number in range(1, 21))


def test_production_cannot_be_enabled_with_incomplete_trust_boundary():
    with pytest.raises(ValueError):
        Settings(environment="production")
    with pytest.raises(ValueError):
        Settings(transport_mode="TRUSTED_RELAY")


def test_openapi_includes_executable_routes_and_contracts(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "Observation" in schema["components"]["schemas"]
    assert "/api/v1/compilations" in schema["paths"]
    assert "/api/v1/jobs" not in schema["paths"]


def test_oversized_body_is_rejected_before_json_parsing(client):
    response = client.post(
        "/api/v1/evidence/verify-observation",
        content=b"x" * 1_048_577,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "JOCKY_E_BODY_LIMIT"
