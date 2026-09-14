import json
from typing import Any

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
    Finding,
    Observation,
    Report,
    ScriptVersion,
    State,
    TimelineEvent,
    User,
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
