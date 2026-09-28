import json
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from jocky_contracts.compiler import CompileRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.compiler import (
    CompilerInvocationError,
    CompilerUnavailableError,
    invoke_compiler,
)
from jocky_control_plane.config import Settings
from jocky_control_plane.models import (
    Artifact,
    AuditEvent,
    BenchmarkRun,
    Case,
    Compilation,
    Endpoint,
    EvidenceManifest,
    ExecutionPlan,
    Finding,
    Hunt,
    Job,
    Observation,
    Report,
    Script,
    ScriptVersion,
    State,
    TimelineEvent,
    User,
    Variant,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import owned, provenance, publish, verify_audit


def generate_report(db: Session, case: Case, user: User, store: ObjectStore) -> Report:
    from jocky_control_plane.api import document

    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "case": document(case),
        "simulation": case.simulation,
        "simulation_label": case.simulation_label,
    }
    for model in (Observation, Finding, TimelineEvent):
        payload[model.__tablename__] = [
            document(row)
            for row in db.scalars(
                select(model).where(
                    model.case_id == case.id, model.organization_id == user.organization_id
                )
            )
        ]
    payload["audit_verification"] = verify_audit(db, user)
    payload["audit"] = [
        document(row)
        for row in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == user.organization_id)
            .order_by(AuditEvent.sequence)
        )
    ]
    content = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    key = store.put(content)
    artifact = Artifact(
        **provenance(case),
        case_id=case.id,
        content_hash=key,
        size_bytes=len(content),
        media_type="application/json",
        storage_key=key,
    )
    db.add(artifact)
    db.flush()
    report = Report(
        **provenance(case), case_id=case.id, artifact_id=artifact.id, status=State.SUCCESS
    )
    db.add(report)
    db.flush()
    publish(
        db,
        user,
        "report.generated",
        report.id,
        simulation=case.simulation,
        simulation_label=case.simulation_label,
    )
    return report


COLLECTOR_ACTIONS = {
    "system": "Collect system metadata",
    "hostname": "Collect hostname metadata",
    "endpoints": "Collect endpoint metadata",
    "users": "Enumerate users",
    "sessions": "Enumerate user sessions",
    "environment": "Collect environment metadata",
    "packages": "Enumerate installed packages",
    "processes": "Enumerate processes",
    "process_metadata": "Collect process metadata",
    "process_hash": "Collect process hashes",
    "process_signatures": "Inspect process signatures",
    "connections": "Collect network connections",
    "ports": "Enumerate listening ports",
    "interfaces": "Enumerate network interfaces",
    "routes": "Collect network routes",
    "dns": "Collect DNS configuration",
    "files": "Collect file metadata",
    "file_metadata": "Collect file metadata",
    "directories": "Enumerate directories",
    "hash": "Hash approved files",
    "file_hash": "Hash approved files",
    "file_content": "Collect approved file content",
    "logs": "Collect event logs",
    "events": "Collect events",
    "services": "Enumerate services",
    "startup": "Enumerate startup entries",
    "scheduled_tasks": "Enumerate scheduled tasks",
    "drivers": "Inspect drivers",
    "driver_hash": "Collect driver hashes",
    "driver_signatures": "Inspect driver signatures",
    "modules": "Enumerate loaded modules",
}


def _enum(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _timestamp(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else str(value) if value else None


def _semantic_steps(plan: dict[str, Any]) -> list[dict[str, str]]:
    steps = [
        {
            "operation": "collect",
            "collector": str(name),
            "description": COLLECTOR_ACTIONS.get(str(name), f"Collect {name}"),
        }
        for name in plan.get("required_collectors", [])
    ]
    operations = {
        "filter": "Filter collected records",
        "project": "Select declared record fields",
        "sort": "Sort result records",
        "limit": "Limit result records",
        "group": "Group result records",
        "correlate": "Correlate typed datasets",
    }
    seen = set()
    for item in plan.get("pushdown", []):
        kind = str(item.get("kind", ""))
        if kind in operations and kind not in seen:
            steps.append({"operation": kind, "description": operations[kind]})
            seen.add(kind)
    domains = {
        str(item.get("result_type", {}).get("domain", ""))
        for item in plan.get("expected_result_schemas", [])
    }
    for domain, operation, description in (
        ("Correlation", "correlate", "Correlate typed datasets"),
        ("Finding", "finding", "Evaluate declared findings"),
        ("TimelineEvent", "timeline", "Assemble the declared timeline"),
    ):
        if domain in domains and operation not in seen:
            steps.append({"operation": operation, "description": description})
            seen.add(operation)
    return steps


def _artifact_verification(store: ObjectStore, artifact: Artifact) -> dict[str, Any]:
    try:
        content = store.get(artifact.storage_key)
    except FileNotFoundError:
        return {"available": False, "integrity_valid": False}
    from jocky_control_plane.security import digest

    return {
        "available": True,
        "integrity_valid": digest(content) == artifact.content_hash
        and len(content) == artifact.size_bytes,
    }


def _collector_limitations(store: ObjectStore, artifacts: list[Artifact]) -> list[str]:
    limitations = []
    for artifact in artifacts:
        if artifact.media_type != "application/json":
            continue
        try:
            value = json.loads(store.get(artifact.storage_key))
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        output = value.get("output", {}) if isinstance(value, dict) else {}
        availability = output.get("availability") if isinstance(output, dict) else None
        if availability and availability != "AVAILABLE":
            collector = output.get("collector", "Collector")
            reason = output.get("reason") or availability
            limitations.append(f"{collector}: {reason}")
    return sorted(set(limitations))


def build_hunt_report_document(
    db: Session,
    hunt: Hunt,
    user: User,
    store: ObjectStore,
    report: Report,
) -> dict[str, Any]:
    case: Case = owned(db, Case, hunt.case_id, user)
    compilation: Compilation = owned(db, Compilation, hunt.compilation_id, user)
    version: ScriptVersion = owned(db, ScriptVersion, compilation.script_version_id, user)
    script: Script = owned(db, Script, version.script_id, user)
    jobs = list(
        db.scalars(
            select(Job)
            .where(Job.organization_id == user.organization_id, Job.hunt_id == hunt.id)
            .order_by(Job.created_at, Job.id)
        )
    )
    job_ids = [job.id for job in jobs]
    endpoint_ids = list(dict.fromkeys(job.endpoint_id for job in jobs))
    endpoints = (
        list(
            db.scalars(
                select(Endpoint).where(
                    Endpoint.organization_id == user.organization_id,
                    Endpoint.id.in_(endpoint_ids),
                )
            )
        )
        if endpoint_ids
        else []
    )
    endpoint_by_id = {row.id: row for row in endpoints}
    observations = (
        list(
            db.scalars(
                select(Observation)
                .where(
                    Observation.organization_id == user.organization_id,
                    Observation.job_id.in_(job_ids),
                )
                .order_by(Observation.created_at, Observation.id)
            )
        )
        if job_ids
        else []
    )
    observation_ids = {str(row.id) for row in observations}
    artifacts = (
        list(
            db.scalars(
                select(Artifact)
                .where(
                    Artifact.organization_id == user.organization_id,
                    Artifact.job_id.in_(job_ids),
                )
                .order_by(Artifact.created_at, Artifact.id)
            )
        )
        if job_ids
        else []
    )
    manifests = (
        list(
            db.scalars(
                select(EvidenceManifest)
                .where(
                    EvidenceManifest.organization_id == user.organization_id,
                    EvidenceManifest.job_id.in_(job_ids),
                )
                .order_by(EvidenceManifest.created_at, EvidenceManifest.id)
            )
        )
        if job_ids
        else []
    )
    manifest_by_job = {row.job_id: row for row in manifests}

    def endpoint_name(identifier: UUID) -> str:
        endpoint = endpoint_by_id.get(identifier)
        return endpoint.hostname if endpoint else str(identifier)

    artifacts_by_job: dict[UUID, list[Artifact]] = defaultdict(list)
    for artifact in artifacts:
        if artifact.job_id:
            artifacts_by_job[artifact.job_id].append(artifact)
    observations_by_job: dict[UUID, list[Observation]] = defaultdict(list)
    for observation in observations:
        observations_by_job[observation.job_id].append(observation)

    plan_ids = [job.plan_id for job in jobs if job.plan_id]
    plans = (
        list(
            db.scalars(
                select(ExecutionPlan).where(
                    ExecutionPlan.organization_id == user.organization_id,
                    ExecutionPlan.id.in_(plan_ids),
                )
            )
        )
        if plan_ids
        else list(
            db.scalars(
                select(ExecutionPlan).where(
                    ExecutionPlan.organization_id == user.organization_id,
                    ExecutionPlan.compilation_id == compilation.id,
                )
            )
        )
    )
    plan = plans[0].document if plans else compilation.outputs.get("plan", {})
    if not isinstance(plan, dict):
        plan = {}

    variant_ids = [job.variant_id for job in jobs if job.variant_id]
    variants = (
        list(
            db.scalars(
                select(Variant).where(
                    Variant.organization_id == user.organization_id,
                    Variant.id.in_(variant_ids),
                )
            )
        )
        if variant_ids
        else []
    )
    variant_by_id = {row.id: row for row in variants}

    all_findings = db.scalars(
        select(Finding).where(
            Finding.organization_id == user.organization_id, Finding.case_id == case.id
        )
    )
    findings = [row for row in all_findings if observation_ids.intersection(row.observation_ids)]
    observation_by_id = {str(row.id): row for row in observations}
    finding_documents = []
    for finding in sorted(findings, key=lambda row: (row.created_at, row.id)):
        supporting = [
            observation_by_id[identifier]
            for identifier in finding.observation_ids
            if identifier in observation_by_id
        ]
        support_jobs = {row.job_id for row in supporting}
        linked_artifacts = [
            artifact.content_hash
            for job_id in support_jobs
            for artifact in artifacts_by_job[job_id]
        ]
        finding_documents.append(
            {
                "id": str(finding.id),
                "severity": finding.severity,
                "title": finding.title,
                "rule_key": finding.rule_key,
                "affected_endpoints": sorted(
                    {
                        str(row.endpoint_id): endpoint_name(row.endpoint_id) for row in supporting
                    }.values()
                ),
                "supporting_observation_count": len(supporting),
                "observation_ids": [str(row.id) for row in supporting],
                "timestamps": sorted(
                    {
                        str(row.document.get("timestamp"))
                        for row in supporting
                        if row.document.get("timestamp")
                    }
                ),
                "observation_integrity_hashes": [row.integrity_hash for row in supporting],
                "linked_artifact_hashes": sorted(set(linked_artifacts)),
                "created_at": _timestamp(finding.created_at),
                "simulation": finding.simulation,
                "simulation_label": finding.simulation_label,
            }
        )

    observation_groups: dict[tuple[UUID, str], list[Observation]] = defaultdict(list)
    for observation in observations:
        observation_groups[(observation.endpoint_id, observation.collector)].append(observation)
    observation_summary = []
    for (endpoint_id, collector), rows in sorted(
        observation_groups.items(),
        key=lambda item: (
            endpoint_name(item[0][0]),
            item[0][1],
        ),
    ):
        endpoint = endpoint_by_id.get(endpoint_id)
        observation_summary.append(
            {
                "endpoint_id": str(endpoint_id),
                "hostname": endpoint.hostname if endpoint else str(endpoint_id),
                "collector": collector,
                "count": len(rows),
                "representative_records": [
                    {
                        "observation_id": str(row.id),
                        "timestamp": row.document.get("timestamp"),
                        "data": row.document.get("data", {}),
                        "integrity_hash": row.integrity_hash,
                    }
                    for row in rows[:3]
                ],
            }
        )

    endpoint_results = []
    compiler_executions = []
    for job in jobs:
        endpoint = endpoint_by_id.get(job.endpoint_id)
        progress = job.progress or {}
        envelope = job.envelope or {}
        variant = variant_by_id.get(job.variant_id) if job.variant_id else None
        variant_manifest = variant.manifest if variant else {}
        manifest = manifest_by_job.get(job.id)
        manifest_document = manifest.document if manifest else {}
        endpoint_results.append(
            {
                "job_id": str(job.id),
                "endpoint_id": str(job.endpoint_id),
                "hostname": endpoint.hostname if endpoint else str(job.endpoint_id),
                "platform": endpoint.target_os if endpoint else None,
                "architecture": endpoint.target_arch if endpoint else None,
                "status": _enum(job.status),
                "transport": envelope.get("transport_mode")
                or (endpoint.transport_mode if endpoint else None),
                "execution_mode": envelope.get("execution_mode") or hunt.execution_mode,
                "execution_engine": progress.get("execution_engine"),
                "variant_id": str(job.variant_id) if job.variant_id else None,
                "worker_pid": progress.get("worker_pid"),
                "duration_ms": progress.get("execution_duration_ms"),
                "observation_count": len(observations_by_job[job.id]),
                "artifact_count": len(artifacts_by_job[job.id]),
                "manifest_count": 1 if manifest else 0,
                "reason": job.reason,
                "simulation": job.simulation,
                "simulation_label": job.simulation_label,
            }
        )
        compiler_executions.append(
            {
                "job_id": str(job.id),
                "compiler_version": variant_manifest.get("compiler_version"),
                "backend": plan.get("runtime", {}).get("backend"),
                "target": variant_manifest.get("target_triple"),
                "execution_mode": envelope.get("execution_mode") or hunt.execution_mode,
                "execution_engine": progress.get("execution_engine"),
                "variant_id": str(job.variant_id) if job.variant_id else None,
                "variant_seed": variant_manifest.get("variant_seed")
                or manifest_document.get("variant_seed")
                or (variant.seed if variant else None),
                "variant_profile": variant_manifest.get("variant_profile")
                or plan.get("runtime", {}).get("variant", {}).get("profile"),
                "source_hash": envelope.get("source_hash") or plan.get("source_hash"),
                "jir_hash": envelope.get("jir_hash") or plan.get("jir_hash"),
                "llvm_ir_hash": variant_manifest.get("llvm_ir_hash")
                or manifest_document.get("llvm_ir_hash"),
                "artifact_hash": envelope.get("artifact_hash")
                or variant_manifest.get("artifact_hash"),
            }
        )

    resource_ids = {
        str(hunt.id),
        *(str(row.id) for row in jobs),
        *(str(row.id) for row in observations),
        *(str(row.id) for row in findings),
        *(str(row.id) for row in manifests),
    }
    audit_events = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == user.organization_id)
            .order_by(AuditEvent.sequence)
        )
    )
    audit_labels = {
        "hunt.created": "Investigation created",
        "hunt.started": "Investigation dispatched",
        "hunt.job.created": "Job dispatched",
        "hunt.progress": "Job state updated",
        "observation.created": "Observation received",
        "finding.created": "Finding created",
        "manifest.verified": "Manifest received and verified",
    }
    timeline = []
    for event in audit_events:
        action = str(event.document.get("action", ""))
        if str(event.document.get("resource_id")) in resource_ids and action in audit_labels:
            timeline.append(
                {
                    "timestamp": event.document.get("timestamp"),
                    "event": audit_labels[action],
                    "action": action,
                    "resource_id": event.document.get("resource_id"),
                }
            )
    timeline.append(
        {
            "timestamp": _timestamp(report.created_at),
            "event": "Report generated",
            "action": "report.generated",
            "resource_id": str(report.id),
        }
    )
    timeline.sort(key=lambda item: str(item.get("timestamp") or ""))

    successful_jobs = sum(job.status == State.SUCCESS for job in jobs)
    severity_rank = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    highest = max(
        (finding.severity.upper() for finding in findings),
        key=lambda value: severity_rank.get(value, -1),
        default=None,
    )
    count_word = "One" if len(findings) == 1 else str(len(findings))
    finding_text = (
        "No persisted findings were produced by this investigation. This does not establish "
        "the absence of suspicious activity."
        if not findings
        else f"{count_word} {highest}-severity finding{'s' if len(findings) != 1 else ''} "
        "requires analyst review."
    )
    summary_text = (
        f"This investigation executed {script.name} across {len(endpoint_ids)} endpoints. "
        f"{successful_jobs}/{len(jobs)} jobs completed successfully, producing "
        f"{len(observations)} observations and {len(artifacts)} evidence artifacts. "
        f"{finding_text}"
    )

    limitations = []
    failed = [job for job in jobs if job.status != State.SUCCESS]
    if failed:
        limitations.append(f"{len(failed)} of {len(jobs)} jobs did not complete successfully.")
    limitations.extend(_collector_limitations(store, artifacts))
    if hunt.simulation or any(row.simulation for row in observations):
        limitations.append("This investigation contains SANDBOX observations.")
    if len(manifests) != len(jobs) or any(not row.signature_verified for row in manifests):
        limitations.append("One or more endpoint manifests are missing or not verified.")
    missing_runtime = [
        result["job_id"]
        for result in endpoint_results
        if not result["execution_engine"]
        or result["worker_pid"] is None
        or result["duration_ms"] is None
    ]
    if missing_runtime:
        limitations.append(
            "Runtime engine, worker PID, or duration metadata is incomplete for "
            f"{len(missing_runtime)} jobs."
        )
    if not plan:
        limitations.append(
            "A structured semantic execution plan is unavailable; source is included."
        )

    audit_verification = verify_audit(db, user)
    artifact_documents = []
    for artifact in artifacts:
        verification = _artifact_verification(store, artifact)
        artifact_documents.append(
            {
                "id": str(artifact.id),
                "job_id": str(artifact.job_id) if artifact.job_id else None,
                "content_hash": artifact.content_hash,
                "size_bytes": artifact.size_bytes,
                "media_type": artifact.media_type,
                **verification,
            }
        )
    manifest_documents = []
    for manifest in manifests:
        manifest_job = next((item for item in jobs if item.id == manifest.job_id), None)
        endpoint = endpoint_by_id.get(manifest_job.endpoint_id) if manifest_job else None
        manifest_documents.append(
            {
                "id": str(manifest.id),
                "job_id": str(manifest.job_id),
                "signature_verification": "VERIFIED"
                if manifest.signature_verified
                else "NOT VERIFIED",
                "signing_endpoint_identity": manifest.document.get("agent_identity")
                or (endpoint.identity if endpoint else None),
                "transport": manifest.document.get("transport_mode")
                or ((manifest_job.envelope or {}).get("transport_mode") if manifest_job else None),
                "simulation": manifest.simulation,
                "simulation_label": manifest.simulation_label,
            }
        )

    return {
        "schema_version": "1.0.0",
        "report_identity": {
            "report_id": str(report.id),
            "investigation_id": str(hunt.id),
            "case_id": str(case.id),
            "generated_at": _timestamp(report.created_at),
            "generated_by": user.username,
            "schema_version": "1.0.0",
        },
        "investigation": {
            "id": str(hunt.id),
            "case_id": str(case.id),
            "case_title": case.title,
            "status": _enum(hunt.status),
            "created_at": _timestamp(hunt.created_at),
            "simulation": hunt.simulation,
            "simulation_label": hunt.simulation_label,
        },
        "executive_summary": {
            "text": summary_text,
            "metrics": {
                "endpoints": len(endpoint_ids),
                "successful_jobs": successful_jobs,
                "jobs": len(jobs),
                "observations": len(observations),
                "findings": len(findings),
                "evidence_artifacts": len(artifacts),
                "verified_manifests": sum(row.signature_verified for row in manifests),
            },
        },
        "intent": {
            "program": script.name,
            "target_endpoint_ids": list(hunt.endpoint_ids),
            "endpoints": [
                {
                    "id": str(row.id),
                    "hostname": row.hostname,
                    "platform": row.target_os,
                    "architecture": row.target_arch,
                }
                for row in endpoints
            ],
            "execution_mode": hunt.execution_mode,
            "enforcement": hunt.enforcement_mode,
            "variant": plan.get("runtime", {}).get("variant") if plan else None,
            "budget": plan.get("budget") if plan else None,
            "declared_capabilities": plan.get("required_capabilities", []) if plan else [],
            "targets": plan.get("targets", []) if plan else [],
        },
        "semantic_plan": {
            "available": bool(plan),
            "operations": _semantic_steps(plan) if plan else [],
            "required_collectors": plan.get("required_collectors", []) if plan else [],
        },
        "endpoint_results": endpoint_results,
        "findings": finding_documents,
        "observation_summary": observation_summary,
        "timeline": timeline,
        "compiler_provenance": {
            "compilation_id": str(compilation.id),
            "executions": compiler_executions,
        },
        "evidence_integrity": {
            "manifests": manifest_documents,
            "artifacts": artifact_documents,
            "observation_integrity_hashes": [
                {"observation_id": str(row.id), "integrity_hash": row.integrity_hash}
                for row in observations
            ],
            "audit_chain_verification": audit_verification,
        },
        "source": {
            "script_id": str(script.id),
            "script_version_id": str(version.id),
            "version": version.version,
            "source_hash": version.source_hash,
            "text": version.source,
        },
        "limitations": limitations,
        "simulation": hunt.simulation,
        "simulation_label": hunt.simulation_label,
    }


def generate_hunt_report(db: Session, hunt: Hunt, user: User, store: ObjectStore) -> Report:
    case: Case = owned(db, Case, hunt.case_id, user)
    report = Report(
        **provenance(hunt),
        case_id=case.id,
        hunt_id=hunt.id,
        status=State.SUCCESS,
    )
    db.add(report)
    db.flush()
    payload = build_hunt_report_document(db, hunt, user, store, report)
    content = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    key = store.put(content)
    artifact = Artifact(
        **provenance(hunt),
        case_id=case.id,
        content_hash=key,
        size_bytes=len(content),
        media_type="application/json",
        storage_key=key,
    )
    db.add(artifact)
    db.flush()
    report.artifact_id = artifact.id
    publish(
        db,
        user,
        "report.generated",
        report.id,
        {"hunt_id": str(hunt.id), "artifact_id": str(artifact.id)},
        simulation=hunt.simulation,
        simulation_label=hunt.simulation_label,
    )
    return report


def run_benchmark(
    db: Session, compilation: Compilation, repetitions: int, user: User, settings: Settings
) -> BenchmarkRun:
    version: ScriptVersion = owned(db, ScriptVersion, compilation.script_version_id, user)
    row = BenchmarkRun(
        organization_id=user.organization_id,
        simulation=True,
        simulation_label="DETERMINISTIC_COMPILER_FIXTURE",
        compilation_id=compilation.id,
        status=State.RUNNING,
    )
    db.add(row)
    db.flush()
    publish(
        db,
        user,
        "benchmark.started",
        row.id,
        simulation=True,
        simulation_label=row.simulation_label,
    )
    db.commit()
    samples = []
    try:
        for index in range(repetitions):
            request = CompileRequest.model_validate(
                {
                    "simulation": True,
                    "simulation_label": row.simulation_label,
                    "source": version.source,
                    "command": "run",
                    "target": {"os": "linux", "arch": "x86_64"},
                    "execution_mode": "memory",
                    "variant_seed": f"{index:016x}",
                }
            )
            sample = invoke_compiler(
                settings.compiler_path, request, settings.compiler_timeout_seconds
            )
            samples.append(sample)
            row.measurements = {"samples": list(samples), "scope": "COMPILER_FIXTURE"}
            publish(
                db,
                user,
                "benchmark.sample",
                row.id,
                {"index": index},
                simulation=True,
                simulation_label=row.simulation_label,
            )
            db.commit()
        row.status = State.SUCCESS
    except (CompilerInvocationError, CompilerUnavailableError) as error:
        row.status = State.FAILED
        row.error = str(error) or "Native compiler unavailable"
    publish(
        db,
        user,
        "benchmark.completed",
        row.id,
        {"state": row.status},
        simulation=True,
        simulation_label=row.simulation_label,
    )
    return row
