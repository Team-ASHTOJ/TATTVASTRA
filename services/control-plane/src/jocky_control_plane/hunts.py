"""Durable per-endpoint scheduling, retries, cancellation and aggregate status."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from jocky_contracts.control import RemoteJobEnvelope
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.builds import build_variants
from jocky_control_plane.config import Settings
from jocky_control_plane.models import (
    CompatibilityRun,
    Compilation,
    Endpoint,
    ExecutionPlan,
    Hunt,
    Job,
    ScriptVersion,
    State,
    User,
    Variant,
)
from jocky_control_plane.security import aware, owned, provenance, publish, sign

TERMINAL = {State.SUCCESS, State.FAILED, State.CANCELLED, State.INCOMPATIBLE}
TRANSITIONS = {
    State.QUEUED: {State.DISPATCHED, State.CANCELLED, State.FAILED},
    State.DISPATCHED: {State.RUNNING, State.FAILED, State.CANCEL_REQUESTED},
    State.RUNNING: {State.SUCCESS, State.FAILED, State.CANCEL_REQUESTED},
    State.CANCEL_REQUESTED: {State.CANCELLED, State.FAILED, State.SUCCESS},
}


def summarize(db: Session, hunt: Hunt) -> None:
    jobs = db.scalars(select(Job).where(Job.hunt_id == hunt.id).order_by(Job.attempt)).all()
    latest = {job.endpoint_id: job for job in jobs}
    states = [job.status for job in latest.values()]
    if not states:
        if hunt.status == State.CANCEL_REQUESTED:
            hunt.status = State.CANCELLED
        return
    if any(state not in TERMINAL for state in states):
        hunt.status = (
            State.CANCEL_REQUESTED if hunt.status == State.CANCEL_REQUESTED else State.RUNNING
        )
    elif all(state == State.SUCCESS for state in states):
        hunt.status = State.SUCCESS
    elif all(state == State.CANCELLED for state in states):
        hunt.status = State.CANCELLED
    elif State.SUCCESS in states:
        hunt.status = State.PARTIAL
    else:
        hunt.status = State.FAILED


def envelope(
    job: Job,
    hunt: Hunt,
    plan: ExecutionPlan,
    variant: Variant,
    settings: Settings,
    transport_mode: str = "UNKNOWN",
) -> dict[str, Any]:
    now = datetime.now(UTC)
    signed = sign(
        settings.signing_key_path,
        {
            "schema_version": "1.0.0",
            "simulation": job.simulation,
            "simulation_label": job.simulation_label,
            "job_id": str(job.id),
            "case_id": str(hunt.case_id),
            "organization_id": str(job.organization_id),
            "endpoint_id": str(job.endpoint_id),
            "plan_id": str(plan.id),
            "variant_id": str(variant.id),
            "artifact_hash": variant.content_hash,
            "source_hash": plan.document["source_hash"],
            "jir_hash": plan.document["jir_hash"],
            "execution_mode": (hunt.endpoint_modes or {}).get(
                str(job.endpoint_id), hunt.execution_mode
            ),
            "transport_mode": transport_mode or "UNKNOWN",
            "enforcement_mode": hunt.enforcement_mode,
            "build_manifest": variant.manifest,
            "required_capabilities": plan.document["required_capabilities"],
            "budget": plan.document["budget"],
            "nonce": secrets.token_hex(32),
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
    )
    RemoteJobEnvelope.model_validate(signed)
    return signed


def start(db: Session, hunt: Hunt, user: User, settings: Settings) -> None:
    db.refresh(hunt, with_for_update=True)
    if hunt.status != State.CREATED:
        raise HTTPException(409, "Hunt has already been started")
    compilation: Compilation = owned(db, Compilation, hunt.compilation_id, user)
    if compilation.status != State.SUCCESS:
        raise HTTPException(409, "Hunt requires a successful compilation")
    version: ScriptVersion = owned(db, ScriptVersion, compilation.script_version_id, user)
    plan_document = compilation.outputs["plan"]
    plan = ExecutionPlan(**provenance(hunt), compilation_id=compilation.id, document=plan_document)
    db.add(plan)
    db.flush()
    hunt.status = State.RUNNING
    shared: dict[str, Variant] = {}
    for identifier in hunt.endpoint_ids:
        from uuid import UUID

        endpoint: Endpoint = owned(db, Endpoint, UUID(identifier), user)
        mode = (hunt.endpoint_modes or {}).get(identifier, hunt.execution_mode)
        reason = None
        instructions = compilation.outputs.get("jir", {}).get("instructions", [])
        supported = {
            "SYSTEM_INFO",
            "USER_ENUMERATE",
            "PROCESS_ENUMERATE",
            "NETWORK_INTERFACE_ENUMERATE",
            "NETWORK_CONNECTION_ENUMERATE",
            "ROUTE_ENUMERATE",
            "SERVICE_ENUMERATE",
            "EVENT_QUERY",
            "DRIVER_ENUMERATE",
            "YARA_SCAN",
        }
        if endpoint.status == State.REVOKED:
            reason = "Endpoint identity has been revoked"
        elif endpoint.simulation != hunt.simulation:
            reason = "Simulation provenance does not match hunt"
        elif endpoint.target_os not in plan_document["target_os"]:
            reason = "Source does not support endpoint OS"
        elif not set(plan_document["required_capabilities"]).issubset(endpoint.capabilities):
            reason = "Endpoint policy does not grant required capabilities"
        elif mode not in endpoint.execution_modes:
            reason = "Agent does not support compiler artifact execution in requested mode"
        elif hunt.enforcement_mode == "STRICT":
            reason = "Agent build cannot enforce strict CPU and memory budgets"
        elif not hunt.simulation and (
            not instructions
            or any(
                instruction["opcode"] not in supported
                or (
                    instruction["opcode"] != "YARA_SCAN"
                    and instruction["attributes"].get("options")
                )
                for instruction in instructions
            )
        ):
            reason = (
                "REAL execution bridge supports bounded inventory and approved YARA scans; "
                "this JIR requires an unavailable host operation"
            )
        elif endpoint.last_seen is None or datetime.now(UTC) - aware(
            endpoint.last_seen
        ) > timedelta(seconds=90):
            reason = "Endpoint heartbeat is stale"
        compatibility = db.scalar(
            select(CompatibilityRun)
            .join(Variant, CompatibilityRun.variant_id == Variant.id)
            .where(
                CompatibilityRun.endpoint_id == endpoint.id,
                Variant.compilation_id == compilation.id,
            )
            .order_by(CompatibilityRun.created_at.desc())
            .limit(1)
        )
        if (
            reason is None
            and compatibility
            and compatibility.observations.get("correctness") == "FAIL"
        ):
            reason = "Latest endpoint compatibility run failed correctness for this compilation"
        job = Job(
            **provenance(hunt),
            hunt_id=hunt.id,
            endpoint_id=endpoint.id,
            plan_id=plan.id,
            attempt=1,
            status=State.INCOMPATIBLE if reason else State.QUEUED,
            reason=reason,
        )
        db.add(job)
        db.flush()
        if reason is None:
            variant = shared.get(mode)
            if variant is None or hunt.diverse:
                try:
                    with db.begin_nested():
                        variant = build_variants(
                            db, compilation, version, 1, user, settings, execution_mode=mode
                        )[0]
                    shared[mode] = variant
                except HTTPException as error:
                    job.status = State.FAILED
                    job.reason = str(error.detail)
                    variant = None
            triple = variant.manifest.get("target_triple", "") if variant else ""
            manifest_os = (
                "windows" if "windows" in triple else "linux" if "linux" in triple else None
            )
            manifest_arch = triple.split("-")[0]
            if variant is None:
                pass  # A failed build cannot discard other endpoints' jobs and evidence.
            elif manifest_os != endpoint.target_os or manifest_arch != endpoint.target_arch:
                job.status = State.INCOMPATIBLE
                job.reason = "Host compiler artifact target does not match endpoint"
            else:
                job.variant_id = variant.id
                job.envelope = envelope(job, hunt, plan, variant, settings, endpoint.transport_mode)
                job.deadline = datetime.now(UTC) + timedelta(minutes=10)
        publish(
            db,
            user,
            "hunt.job.created",
            job.id,
            {"status": job.status, "reason": job.reason},
            simulation=job.simulation,
            simulation_label=job.simulation_label,
        )
    db.flush()
    summarize(db, hunt)
    publish(
        db,
        user,
        "hunt.started",
        hunt.id,
        {"status": hunt.status},
        simulation=hunt.simulation,
        simulation_label=hunt.simulation_label,
    )


def cancel(db: Session, hunt: Hunt, user: User) -> None:
    db.refresh(hunt, with_for_update=True)
    if hunt.status in TERMINAL or hunt.status == State.PARTIAL:
        raise HTTPException(409, "Hunt is already terminal")
    hunt.status = State.CANCEL_REQUESTED
    for job in db.scalars(select(Job).where(Job.hunt_id == hunt.id).with_for_update()):
        if job.status == State.QUEUED:
            job.status = State.CANCELLED
        elif job.status not in TERMINAL:
            job.status = State.CANCEL_REQUESTED
    db.flush()
    summarize(db, hunt)
    if hunt.status == State.CANCEL_REQUESTED and not hunt.endpoint_ids:
        hunt.status = State.CANCELLED
    publish(
        db,
        user,
        "hunt.cancelled",
        hunt.id,
        simulation=hunt.simulation,
        simulation_label=hunt.simulation_label,
    )


def transition(
    db: Session, job: Job, target: State, user: User, settings: Settings, detail: str = ""
) -> None:
    if job.status == target:
        return
    if target not in TRANSITIONS.get(job.status, set()):
        raise HTTPException(409, f"Invalid job transition {job.status} -> {target}")
    job.status = target
    job.reason = detail or None
    hunt: Hunt = owned(db, Hunt, job.hunt_id, user)
    if (
        target == State.FAILED
        and job.attempt <= hunt.retry_limit
        and hunt.status != State.CANCEL_REQUESTED
    ):
        retry = Job(
            **provenance(job),
            hunt_id=job.hunt_id,
            endpoint_id=job.endpoint_id,
            variant_id=job.variant_id,
            plan_id=job.plan_id,
            attempt=job.attempt + 1,
            retry_of=job.id,
            status=State.QUEUED,
            deadline=datetime.now(UTC) + timedelta(minutes=10),
        )
        db.add(retry)
        db.flush()
        assert job.plan_id is not None and job.variant_id is not None
        plan = owned(db, ExecutionPlan, job.plan_id, user)
        variant = owned(db, Variant, job.variant_id, user)
        retry.envelope = envelope(
            retry,
            hunt,
            plan,
            variant,
            settings,
            (job.envelope or {}).get("transport_mode", "UNKNOWN"),
        )
        publish(
            db,
            user,
            "hunt.job.retry",
            retry.id,
            {"retry_of": str(job.id)},
            simulation=job.simulation,
            simulation_label=job.simulation_label,
        )
    db.flush()
    summarize(db, hunt)
    publish(
        db,
        user,
        "hunt.progress",
        hunt.id,
        {"job_id": str(job.id), "state": target, "hunt_state": hunt.status},
        simulation=job.simulation,
        simulation_label=job.simulation_label,
    )
