"""Immutable compatibility measurement snapshots from persisted control-plane facts."""

from collections import Counter
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
    }


def snapshot(
    db: Session, payload: CompatibilityCreate, user: User
) -> tuple[Variant, UUID | None, dict[str, Any]]:
    variant = owned(db, Variant, payload.variant_id, user)
    compilation = owned(db, Compilation, variant.compilation_id, user)
    version = owned(db, ScriptVersion, compilation.script_version_id, user)
    if compilation.simulation != variant.simulation or version.simulation != variant.simulation:
        raise HTTPException(409, "Compiler provenance mismatch")
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
    manifest = variant.manifest or {}
    outputs = compilation.outputs or {}
    llvm = outputs.get("llvm") or {}
    compiler_manifest = llvm.get("manifest") or {} if isinstance(llvm, dict) else {}
    plan = outputs.get("plan") or {}
    if not isinstance(plan, dict):
        plan = {}
    if not plan and job and job.plan_id:
        persisted_plan = owned(db, ExecutionPlan, job.plan_id, user)
        if persisted_plan.compilation_id == compilation.id:
            plan = persisted_plan.document or {}
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
        "simulation": variant.simulation,
        "simulation_label": variant.simulation_label,
        "recorded_by_username": user.username,
    }
    observations = payload.model_dump(mode="json")
    observations.update(identity)
    observations["endpoint_id"] = str(endpoint_id) if endpoint_id else None
    observations["measurement_source"] = "JOB_DERIVED" if job else "OPERATOR_RECORDED"
    if job:
        observations.update(job_measurements(db, job, user))
    return variant, endpoint_id, observations
