"""Compatibility Lab regressions using persisted protocol fixtures, never live product claims."""

from datetime import UTC, datetime
from uuid import uuid4

from jocky_contracts.control import CompatibilityCreate
from jocky_control_plane.models import Job, Observation, Organization, State, Variant
from jocky_control_plane.security import digest, provenance
from test_distributed import runtime, setup_job

__all__ = ["runtime"]


def payload(ids, **overrides):
    value = {
        "variant_id": str(ids[4]),
        "environment": "fixture environment",
        "security_product_label": "NOT_MEASURED",
        "correctness": "NOT_MEASURED",
        "alert_observed": "NOT_OBSERVED",
        "notes": "test fixture only",
    }
    value.update(overrides)
    return value


def test_contract_additive_fields_and_old_payload():
    ids = (None, None, None, None, uuid4())
    old = CompatibilityCreate.model_validate(payload(ids))
    assert old.job_id is None
    assert old.peak_memory_bytes is None
    new = CompatibilityCreate.model_validate(
        payload(
            ids,
            measurement_source="OPERATOR_RECORDED",
            measured_at=datetime.now(UTC).isoformat(),
            os_name="Windows",
            os_version="11 24H2",
            architecture="x86_64",
            security_product_version="exact fixture version",
            realtime_protection="UNKNOWN",
            execution_status="SUCCESS",
            runtime_ms=1.5,
            cpu_percent=10,
            peak_memory_bytes=4096,
            collector_counts={"processes": 2},
        )
    )
    assert new.collector_counts == {"processes": 2}
    for update in (
        {"runtime_ms": -1},
        {"cpu_percent": 101},
        {"peak_memory_bytes": -1},
        {"collector_counts": {"processes": -1}},
    ):
        try:
            CompatibilityCreate.model_validate(payload(ids, **update))
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid field: {update}")


def test_server_identity_job_metrics_and_listing(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=False)
    with factory.begin() as db:
        variant = db.get(Variant, ids[4])
        variant.manifest = {
            **variant.manifest,
            "target_triple": "x86_64-unknown-linux-gnu",
            "execution_mode": "native",
            "structural_fingerprint": "FP-test",
        }
        job = db.get(Job, ids[2])
        job.status = State.SUCCESS
        job.progress = {"execution_duration_ms": 184, "cpu_percent": 7.5}
        db.add(
            Observation(
                **provenance(job),
                case_id=ids[0],
                job_id=job.id,
                endpoint_id=job.endpoint_id,
                producer_id=str(uuid4()),
                collector="processes",
                integrity_hash=digest(b"fixture-observation"),
                document={"simulation": False},
            )
        )
    link = payload(
        ids,
        job_id=str(ids[2]),
        os_name="Linux",
        os_version="test",
        architecture="x86_64",
        security_product_version="unknown",
    )
    spoof = client.post("/api/compatibility-runs", json={**link, "artifact_sha256": "f" * 64})
    assert spoof.status_code == 422
    override = client.post("/api/compatibility-runs", json={**link, "runtime_ms": 1})
    assert override.status_code == 422
    response = client.post("/api/compatibility-runs", json=link)
    assert response.status_code == 201, response.text
    row = response.json()
    o = row["observations"]
    assert o["artifact_sha256"] == digest(b"fixture")
    assert o["jir_sha256"] == digest(b"fixture-jir")
    assert o["source_sha256"] == digest(b"test protocol bytes")
    assert o["llvm_ir_hash"] == digest(b"fixture-llvm")
    assert o["structural_fingerprint"] == "FP-test"
    assert o["endpoint_hostname"] == "TEST-ONLY"
    assert o["measurement_source"] == "JOB_DERIVED"
    assert o["runtime_ms"] == 184
    assert o["cpu_percent"] == 7.5
    assert o["peak_memory_bytes"] is None
    assert o["collector_counts"] == {"processes": 1}
    assert row["endpoint_id"] == str(ids[3])
    listed = client.get("/api/compatibility-runs")
    assert listed.status_code == 200
    assert any(item["id"] == row["id"] and item["observations"] == o for item in listed.json())


def test_completed_job_candidate_auto_resolves_provenance(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=False)
    with factory.begin() as db:
        job = db.get(Job, ids[2])
        job.status = State.SUCCESS
        db.add(
            Observation(
                **provenance(job),
                case_id=ids[0],
                job_id=job.id,
                endpoint_id=job.endpoint_id,
                producer_id=str(uuid4()),
                collector="system",
                integrity_hash=digest(b"system-version"),
                document={"data": {"release": "fixture-release"}, "simulation": False},
            )
        )
        job.progress = {"execution_duration_ms": 184, "execution_engine": "LLVM_ORC_JIT"}
    response = client.get("/api/compatibility-runs/candidates")
    assert response.status_code == 200, response.text
    candidate = next(row for row in response.json() if row["job_id"] == str(ids[2]))
    assert candidate["variant_id"] == str(ids[4])
    assert candidate["endpoint_id"] == str(ids[3])
    assert candidate["endpoint_hostname"] == "TEST-ONLY"
    assert candidate["execution_status"] == "SUCCESS"
    assert candidate["runtime_ms"] == 184
    assert candidate["artifact_sha256"] == digest(b"fixture")
    assert candidate["measurement_source"] == "JOB_DERIVED"


def test_job_baseline_is_idempotent_and_security_observation_enriches_it(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=False)
    with factory.begin() as db:
        job = db.get(Job, ids[2])
        job.status = State.SUCCESS
        job.progress = {"execution_duration_ms": 184}
        variant = db.get(Variant, ids[4])
        variant.manifest = {**variant.manifest, "equivalence_status": "VERIFIED"}
    baseline = payload(ids, job_id=str(ids[2]), measurement_source="JOB_DERIVED")
    first = client.post("/api/compatibility-runs", json=baseline)
    second = client.post("/api/compatibility-runs", json=baseline)
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    observations = first.json()["observations"]
    assert observations["measurement_source"] == "JOB_DERIVED"
    assert observations["execution_status"] == "SUCCESS"
    assert observations["correctness"] == "PASS"
    assert observations["alert_observed"] == "NOT_OBSERVED"
    assert observations["environment_fingerprint"].startswith("ENV-")
    assert observations["baseline_environment_fingerprint"].startswith("ENV-")
    assert observations["measured_at"]

    enriched = client.post(
        "/api/compatibility-runs",
        json={
            **baseline,
            "environment": "Recorded security environment",
            "security_product_label": "Fixture Product",
            "security_product_version": "1.2.3",
            "realtime_protection": "ENABLED",
            "alert_observed": "NO",
        },
    )
    assert enriched.status_code == 201
    assert enriched.json()["id"] == first.json()["id"]
    enriched_observations = enriched.json()["observations"]
    assert enriched_observations["artifact_sha256"] == observations["artifact_sha256"]
    assert enriched_observations["runtime_ms"] == 184
    assert enriched_observations["security_product_label"] == "Fixture Product"
    assert enriched_observations["alert_observed"] == "NO"


def test_environment_fingerprint_is_normalized_and_security_specific(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=False)
    with factory.begin() as db:
        job = db.get(Job, ids[2])
        job.status = State.SUCCESS
        db.add(
            Observation(
                **provenance(job),
                case_id=ids[0],
                job_id=job.id,
                endpoint_id=job.endpoint_id,
                producer_id=str(uuid4()),
                collector="system",
                integrity_hash=digest(b"fingerprint-system-version"),
                document={"data": {"release": "fixture-release"}, "simulation": False},
            )
        )
    common = {
        **payload(ids),
        "job_id": str(ids[2]),
        "security_product_label": " Fixture Product ",
        "security_product_version": " 1.2.3 ",
        "realtime_protection": "ENABLED",
    }
    first = client.post("/api/compatibility-runs", json=common)
    second = client.post(
        "/api/compatibility-runs",
        json={**common, "security_product_label": "fixture   product"},
    )
    assert first.status_code == 201 and second.status_code == 201
    fingerprint = first.json()["observations"]["environment_fingerprint"]
    assert fingerprint.startswith("ENV-") and len(fingerprint) == 10
    assert second.json()["observations"]["environment_fingerprint"] == fingerprint


def test_job_link_rejects_other_variant_endpoint_and_tenant(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=False)
    with factory.begin() as db:
        original = db.get(Variant, ids[4])
        other = Variant(
            **provenance(original),
            compilation_id=original.compilation_id,
            seed="1" * 16,
            manifest={},
            content_hash=digest(b"other"),
            storage_key=digest(b"other"),
        )
        db.add(other)
        db.flush()
        other_id = other.id
        other_org = Organization(name="Other compatibility tenant")
        db.add(other_org)
        db.flush()
        foreign_job = Job(
            organization_id=other_org.id,
            hunt_id=ids[1],
            endpoint_id=ids[3],
            variant_id=ids[4],
            attempt=2,
            status=State.SUCCESS,
        )
        db.add(foreign_job)
        db.flush()
        foreign_job_id = foreign_job.id
    assert (
        client.post(
            "/api/compatibility-runs",
            json=payload(ids, variant_id=str(other_id), job_id=str(ids[2])),
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/compatibility-runs",
            json=payload(ids, endpoint_id=str(uuid4()), job_id=str(ids[2])),
        ).status_code
        == 409
    )
    assert (
        client.post("/api/compatibility-runs", json=payload(ids, job_id=str(uuid4()))).status_code
        == 404
    )
    assert (
        client.post(
            "/api/compatibility-runs", json=payload(ids, job_id=str(foreign_job_id))
        ).status_code
        == 404
    )


def test_unavailable_and_simulation_provenance(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=True)
    response = client.post("/api/compatibility-runs", json=payload(ids, job_id=str(ids[2])))
    assert response.status_code == 201, response.text
    row = response.json()
    o = row["observations"]
    assert row["simulation"] is True and row["simulation_label"] == "TEST_FIXTURE"
    assert o["simulation"] is True and o["simulation_label"] == "TEST_FIXTURE"
    assert o["execution_status"] == "NOT_MEASURED"
    assert o["runtime_ms"] is None and o["cpu_percent"] is None and o["peak_memory_bytes"] is None
    assert o["collector_counts"] is None
    assert o["measurement_source"] == "JOB_DERIVED"
    preview = client.get(f"/api/compatibility-runs/job-preview?job_id={ids[2]}&variant_id={ids[4]}")
    assert preview.status_code == 200
    assert preview.json()["peak_memory_bytes"] is None


def test_manual_measurement_is_operator_recorded(runtime):
    factory, _, client, org_id, _ = runtime
    ids = setup_job(factory, org_id, simulation=False)
    response = client.post(
        "/api/compatibility-runs", json=payload(ids, runtime_ms=12, alert_observed="YES")
    )
    assert response.status_code == 201, response.text
    assert response.json()["observations"]["measurement_source"] == "OPERATOR_RECORDED"
    assert response.json()["observations"]["runtime_ms"] == 12
