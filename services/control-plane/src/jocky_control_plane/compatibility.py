"""Immutable compatibility measurement snapshots from persisted control-plane facts."""

import json
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from jocky_contracts.control import CompatibilityCreate
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.models import (
    Compilation,
    Endpoint,
    EvidenceManifest,
    ExecutionPlan,
    Job,
    Observation,
    Script,
    ScriptVersion,
    State,
    User,
    Variant,
)
from jocky_control_plane.security import owned


def _number(value: Any, *, maximum: float | None = None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not isfinite(value) or value < 0 or (maximum is not None and value > maximum):
        return None
    return float(value)


def _hash(value: Any) -> str | None:
    return (
        value
        if isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
        else None
    )


def job_measurements(db: Session, job: Job, user: User) -> dict[str, Any]:
    progress = job.progress or {}
    manifest = db.scalar(
        select(EvidenceManifest).where(
            EvidenceManifest.job_id == job.id,
            EvidenceManifest.organization_id == user.organization_id,
            EvidenceManifest.simulation == job.simulation,
        )
    )
    evidence = manifest.document if manifest and manifest.signature_verified else {}
    if not isinstance(evidence, dict):
        evidence = {}
    runtime = _number(progress.get("execution_duration_ms"))
    if runtime is None:
        runtime = _number(evidence.get("execution_duration_ms"))
    cpu = _number(progress.get("cpu_percent"), maximum=100)
    peak = _number(progress.get("peak_memory_bytes"))
    if peak is None:
        peak = _number(progress.get("peak_rss_bytes"))
    observations = db.scalars(
        select(Observation).where(
            Observation.organization_id == user.organization_id,
            Observation.job_id == job.id,
            Observation.endpoint_id == job.endpoint_id,
            Observation.simulation == job.simulation,
        )
    ).all()
    counts = dict(Counter(row.collector for row in observations))
    system = next((row for row in observations if row.collector == "system"), None)
    system_data = {}
    if system and isinstance(system.document, dict):
        value = system.document.get("data")
        if isinstance(value, dict):
            system_data = value
    return {
        "execution_status": (
            "SUCCESS"
            if job.status == State.SUCCESS
            else "FAILED"
            if job.status == State.FAILED
            else "NOT_MEASURED"
        ),
        "runtime_ms": runtime,
        "cpu_percent": cpu,
        "peak_memory_bytes": int(peak) if peak is not None else None,
        "collector_counts": counts if observations else None,
        "os_version": system_data.get("os_version")
        or system_data.get("release")
        or system_data.get("version"),
        "execution_engine": progress.get("execution_engine") or evidence.get("execution_engine"),
    }


def _identity(
    db: Session,
    variant: Variant,
    user: User,
    endpoint: Endpoint | None = None,
) -> tuple[dict[str, Any], Compilation, ScriptVersion]:
    compilation = owned(db, Compilation, variant.compilation_id, user)
    version = owned(db, ScriptVersion, compilation.script_version_id, user)
    if compilation.simulation != variant.simulation or version.simulation != variant.simulation:
        raise HTTPException(409, "Compiler provenance mismatch")
    manifest = variant.manifest or {}
    outputs = compilation.outputs or {}
    llvm = outputs.get("llvm") or {}
    compiler_manifest = llvm.get("manifest") or {} if isinstance(llvm, dict) else {}
    plan = outputs.get("plan") or {}
    if not isinstance(plan, dict):
        plan = {}
    identity = {
        "variant_id": str(variant.id),
        "variant_seed": variant.seed,
        "artifact_sha256": _hash(variant.content_hash),
        "target_triple": manifest.get("target_triple"),
        "execution_mode": manifest.get("execution_mode"),
        "structural_fingerprint": manifest.get("structural_fingerprint"),
        "llvm_ir_hash": _hash(manifest.get("llvm_ir_hash")),
        "compilation_id": str(compilation.id),
        "jir_sha256": _hash(compiler_manifest.get("jir_hash"))
        or _hash(plan.get("jir_hash"))
        or _hash(manifest.get("jir_hash")),
        "source_sha256": _hash(version.source_hash),
        "endpoint_hostname": endpoint.hostname if endpoint else None,
        "endpoint_platform": endpoint.target_os if endpoint else None,
        "endpoint_architecture": endpoint.target_arch if endpoint else None,
        "transport_mode": endpoint.transport_mode if endpoint else None,
        "simulation": variant.simulation,
        "simulation_label": variant.simulation_label,
        "recorded_by_username": user.username,
    }
    return identity, compilation, version


def _environment_fingerprint(values: dict[str, Any]) -> str | None:
    product = values.get("security_product_label")
    platform = values.get("os_name") or values.get("endpoint_platform")
    architecture = values.get("architecture") or values.get("endpoint_architecture")
    if not platform or not architecture:
        return None
    if not product or str(product).upper() == "NOT_MEASURED":
        fields = (
            "job-baseline",
            platform,
            values.get("os_version") or "UNREPORTED",
            architecture,
            values.get("transport_mode") or "UNREPORTED",
            values.get("execution_mode") or "UNREPORTED",
        )
    else:
        fields = (
            platform,
            values.get("os_version"),
            architecture,
            product,
            values.get("security_product_version"),
            values.get("realtime_protection"),
        )
        if any(value is None or str(value).strip() == "" for value in fields):
            return None
    normalized = [" ".join(str(value).strip().lower().split()) for value in fields]
    encoded = json.dumps(normalized, ensure_ascii=True, separators=(",", ":")).encode()
    return f"ENV-{sha256(encoded).hexdigest()[:6].upper()}"


def job_preview(db: Session, job: Job, user: User) -> dict[str, Any]:
    if not job.variant_id:
        raise HTTPException(409, "Completed job has no persisted variant")
    variant = owned(db, Variant, job.variant_id, user)
    endpoint = owned(db, Endpoint, job.endpoint_id, user)
    if job.simulation != variant.simulation or endpoint.simulation != job.simulation:
        raise HTTPException(409, "Job provenance does not match variant or endpoint")
    identity, _, version = _identity(db, variant, user, endpoint)
    script = owned(db, Script, version.script_id, user)
    return {
        **identity,
        **job_measurements(db, job, user),
        "job_id": str(job.id),
        "hunt_id": str(job.hunt_id),
        "variant_id": str(variant.id),
        "endpoint_id": str(endpoint.id),
        "program": script.name,
        "measurement_source": "JOB_DERIVED",
    }


def snapshot(
    db: Session, payload: CompatibilityCreate, user: User
) -> tuple[Variant, UUID | None, dict[str, Any]]:
    variant = owned(db, Variant, payload.variant_id, user)
    job = owned(db, Job, payload.job_id, user) if payload.job_id else None
    endpoint_id = payload.endpoint_id
    if job:
        if job.variant_id != variant.id:
            raise HTTPException(409, "Job variant does not match compatibility variant")
        if endpoint_id is not None and endpoint_id != job.endpoint_id:
            raise HTTPException(409, "Job endpoint does not match compatibility endpoint")
        if job.simulation != variant.simulation:
            raise HTTPException(409, "Compatibility provenance mismatch")
        endpoint_id = job.endpoint_id
    endpoint = owned(db, Endpoint, endpoint_id, user) if endpoint_id else None
    if endpoint and endpoint.simulation != variant.simulation:
        raise HTTPException(409, "Compatibility provenance mismatch")
    if payload.measurement_source and payload.measurement_source != (
        "JOB_DERIVED" if job else "OPERATOR_RECORDED"
    ):
        raise HTTPException(422, "Measurement source does not match job linkage")
    if job:
        client_metrics = {
            "execution_status",
            "runtime_ms",
            "cpu_percent",
            "peak_memory_bytes",
            "collector_counts",
        }
        if client_metrics & payload.model_fields_set:
            raise HTTPException(422, "Job-derived measurements cannot be supplied by client")
    identity, compilation, _version = _identity(db, variant, user, endpoint)
    plan = (compilation.outputs or {}).get("plan") or {}
    if not plan and job and job.plan_id:
        persisted_plan = owned(db, ExecutionPlan, job.plan_id, user)
        if persisted_plan.compilation_id == compilation.id:
            plan = persisted_plan.document or {}
    if isinstance(plan, dict) and not identity.get("jir_sha256"):
        identity["jir_sha256"] = _hash(plan.get("jir_hash"))
    observations = payload.model_dump(mode="json")
    observations.update(identity)
    observations["endpoint_id"] = str(endpoint_id) if endpoint_id else None
    observations["measurement_source"] = "JOB_DERIVED" if job else "OPERATOR_RECORDED"
    if job:
        measurements = job_measurements(db, job, user)
        observations.update(measurements)
        observations["correctness"] = (
            "PASS"
            if (variant.manifest or {}).get("equivalence_status") == "VERIFIED"
            else "NOT_MEASURED"
        )
        observations["os_name"] = endpoint.target_os if endpoint else None
        observations["architecture"] = endpoint.target_arch if endpoint else None
        observations["os_version"] = measurements.get("os_version")
        observations["measured_at"] = (
            payload.measured_at.isoformat()
            if payload.measured_at
            else datetime.now(UTC).isoformat()
        )
        observations["baseline_environment_fingerprint"] = _environment_fingerprint(observations)
    observations["environment_fingerprint"] = _environment_fingerprint(observations)
    return variant, endpoint_id, observations
