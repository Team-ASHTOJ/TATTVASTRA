"""Delivery gates use the actual native compiler, fixture runner and signed object store."""
# ruff: noqa: F811

import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from jocky_control_plane.models import BuildRun, Variant
from jocky_control_plane.objects import ObjectStore
from test_distributed import PASSWORD, runtime  # noqa: F401

SOURCE = """hunt "forge-baseline" {
    targets { group "AUTHORIZED" os linux }
    runtime { backend llvm execution memory }
    capabilities { system.read }
    collect system as inventory
}"""


def compiled(client, source=SOURCE):
    case = client.post("/api/cases", json={"title": "Build acceptance", "simulation": False})
    assert case.status_code == 201
    script = client.post(
        "/api/scripts",
        json={"case_id": case.json()["id"], "name": "baseline.jky", "source": source},
    )
    assert script.status_code == 201, script.text
    result = client.post("/api/scripts/" + script.json()["id"] + "/compile")
    assert result.status_code == 201, result.text
    assert result.json()["status"] == "SUCCESS", result.text
    return result.json()["id"]


def build(client, compilation, **options):
    response = client.post(
        "/api/build-runs",
        json={"compilation_id": compilation, "seed": "0123456789abcdef", **options},
    )
    assert response.status_code == 202, response.text
    # TestClient waits for actual background completion; inspect durable state afresh.
    detail = client.get("/api/build-runs/" + response.json()["id"])
    assert detail.status_code == 200
    return detail.json()


def test_build_api_access_and_constraints(runtime):
    _, _, client, organization, _ = runtime
    assert client.get("/api/build-runs", headers={"Authorization": ""}).status_code == 401
    viewer = client.post(
        "/api/auth/login",
        json={"organization_id": str(organization), "username": "viewer", "password": PASSWORD},
    ).json()["access_token"]
    assert (
        client.post(
            "/api/build-runs",
            headers={"Authorization": "Bearer " + viewer},
            json={"compilation_id": str(uuid4())},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/build-runs", json={"compilation_id": str(uuid4()), "count": 0}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/build-runs", json={"compilation_id": str(uuid4()), "execution_mode": "native"}
        ).status_code
        == 422
    )
    assert client.get("/api/build-runs/" + str(uuid4())).status_code == 404


native = pytest.mark.skipif(
    not Path(os.getenv("JOCKY_COMPILER_PATH", "/missing")).is_file(),
    reason="real LLVM compiler required; executed in compiler-bearing container",
)


@native
def test_real_build_replay_fixture_manifest_and_tamper(runtime):
    factory, settings, client, _, _ = runtime
    compilation = compiled(client)
    first = build(client, compilation)
    assert first["status"] == "READY", first
    assert all(s["status"] == "SUCCESS" for s in first["stages"])
    assert first["results"]["equivalence_status"] == "VERIFIED"
    assert first["results"]["simulation"] is True
    variants = first["manifest"]["variants"]
    assert len(variants) == 3
    for field in ("artifact_hash", "llvm_ir_hash", "structural_fingerprint"):
        assert len({v[field] for v in variants}) == 3
    assert len({v["jir_hash"] for v in variants}) == 1
    assert all(v["artifact_size_bytes"] > 0 for v in variants)
    verified = client.post("/api/build-runs/" + first["id"] + "/verify").json()
    assert verified["valid"], verified
    replay = build(client, compilation)
    assert replay["status"] == "READY", replay
    assert [v["artifact_hash"] for v in replay["manifest"]["variants"]] == [
        v["artifact_hash"] for v in variants
    ]
    assert [v["structural_fingerprint"] for v in replay["manifest"]["variants"]] == [
        v["structural_fingerprint"] for v in variants
    ]
    comparison = client.post(
        "/api/variants/compare", json={"variant_ids": [v["id"] for v in variants]}
    ).json()
    assert comparison["semantic_equivalence"] == "VERIFIED"
    with factory.begin() as db:
        variant = db.get(Variant, UUID(variants[0]["id"]))
        ObjectStore(settings.object_root).path(variant.storage_key).write_bytes(
            b"tampered compiled object"
        )
    verified = client.post("/api/build-runs/" + first["id"] + "/verify").json()
    assert (
        verified["signature_valid"]
        and not verified["artifact_integrity_valid"]
        and not verified["valid"]
    )
    comparison = client.post(
        "/api/variants/compare", json={"variant_ids": [v["id"] for v in variants]}
    ).json()
    assert comparison["semantic_equivalence"] != "VERIFIED"
    with factory.begin() as db:
        variant = db.get(Variant, UUID(variants[0]["id"]))
        ObjectStore(settings.object_root).path(variant.storage_key).unlink()
    missing = client.post("/api/build-runs/" + first["id"] + "/verify").json()
    assert not missing["artifact_integrity_valid"] and not missing["valid"]
    with factory.begin() as db:
        run = db.get(BuildRun, UUID(first["id"]))
        run.manifest = {**run.manifest, "target": "tampered"}
    assert not client.post("/api/build-runs/" + first["id"] + "/verify").json()["signature_valid"]


@native
def test_real_fixture_mismatch_stops_before_manifest(runtime):
    _, _, client, _, _ = runtime
    result = build(client, compiled(client), expected_semantic_hash="0" * 64)
    assert result["status"] == "FAILED", result
    stages = {s["name"]: s["status"] for s in result["stages"]}
    assert stages["EQUIVALENCE"] == "FAILED"
    assert stages["MANIFEST"] == stages["READY"] == "SKIPPED"
    assert result["results"]["equivalence_status"] == "FAILED"
    assert client.get("/api/build-runs/" + result["id"] + "/manifest").status_code == 409


@native
def test_source_integrity_gate_blocks_delivery(runtime):
    from jocky_control_plane.models import Compilation, ScriptVersion

    factory, _, client, _, _ = runtime
    compilation = compiled(client)
    with factory.begin() as db:
        row = db.get(Compilation, UUID(compilation))
        version = db.get(ScriptVersion, row.script_version_id)
        # Insert corrupt input without weakening PostgreSQL's immutable-version trigger.
        corrupt = ScriptVersion(
            organization_id=version.organization_id,
            script_id=version.script_id,
            version=version.version + 1,
            source=version.source + "\n// corrupt input",
            source_hash=version.source_hash,
            simulation=False,
        )
        db.add(corrupt)
        db.flush()
        row.script_version_id = corrupt.id
    result = build(client, compilation)
    assert result["status"] == "FAILED"
    assert result["stages"][0]["status"] == "FAILED"
    assert all(s["status"] == "SKIPPED" for s in result["stages"][1:])
    assert result["manifest"] is None


@native
def test_protected_configuration_uses_external_key(runtime, monkeypatch):
    import secrets

    from jocky_control_plane.models import Compilation, ScriptVersion

    factory, settings, client, _, _ = runtime
    monkeypatch.setenv("JOCKY_LITERAL_KEY_HEX", secrets.token_hex(32))
    monkeypatch.setenv("JOCKY_LITERAL_KEY_ID", "ephemeral-fixture-key")
    source = (
        SOURCE.replace("execution memory", "execution memory protect_literals true")
        .replace("system.read", "filesystem.metadata")
        .replace(
            "collect system as inventory",
            'collect files { path path("jocky-sensitive-fixture-marker") } as inventory',
        )
    )
    compilation = compiled(client, source)
    result = build(client, compilation, count=1)
    assert result["status"] == "READY", result
    variant = result["manifest"]["variants"][0]
    assert variant["literal_pool"]["enabled"] is True
    assert variant["literal_pool"]["algorithm"] == "AES-256-GCM"
    assert b"jocky-sensitive-fixture-marker" not in ObjectStore(settings.object_root).get(
        variant["artifact_hash"]
    )
    assert client.post("/api/build-runs/" + result["id"] + "/verify").json()["valid"]
    with factory() as db:
        comp = db.get(Compilation, UUID(compilation))
        script = db.get(ScriptVersion, comp.script_version_id).script_id
    monkeypatch.delenv("JOCKY_LITERAL_KEY_HEX")
    monkeypatch.delenv("JOCKY_LITERAL_KEY_ID")
    rejected = client.post("/api/scripts/" + str(script) + "/compile")
    assert rejected.json()["status"] == "FAILED"
    assert not client.get("/api/build-capabilities").json()["literal_key_configured"]
