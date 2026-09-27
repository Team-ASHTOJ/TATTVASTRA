"""Transactional ingestion with endpoint/job provenance and signature checks."""

import base64
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException
from jocky_contracts.evidence import EvidenceManifest as WireManifest
from jocky_contracts.evidence import Observation as WireObservation
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.models import (
    Artifact,
    Compilation,
    Endpoint,
    EvidenceManifest,
    Hunt,
    Job,
    Observation,
    ScriptVersion,
    State,
    TimelineEvent,
    User,
    Variant,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import aware, digest, owned, provenance, publish


def ingest_observation(
    db: Session, endpoint: Endpoint, payload: dict[str, Any], user: User
) -> Observation:
    parsed = WireObservation.model_validate(payload)
    job: Job = owned(db, Job, UUID(parsed.job_id), user)
    hunt: Hunt = owned(db, Hunt, job.hunt_id, user)
    if (
        job.endpoint_id != endpoint.id
        or parsed.endpoint_id != str(endpoint.id)
        or parsed.case_id != str(hunt.case_id)
        or parsed.simulation != job.simulation
        or parsed.simulation_label != job.simulation_label
        or parsed.variant_id != str(job.variant_id)
        or job.envelope is None
        or parsed.source_hash != job.envelope["source_hash"]
        or parsed.jir_hash != job.envelope["jir_hash"]
    ):
        raise HTTPException(403, "Observation provenance does not match assigned job")
    if job.status not in {State.RUNNING, State.CANCEL_REQUESTED}:
        raise HTTPException(409, "Job is not accepting observations")
    # Validate with Pydantic but preserve exact received timestamp spelling for
    # cross-language canonical signatures. Do not silently reserialize timestamps.
    body = {k: v for k, v in payload.items() if k != "integrity_hash"}
    if not hmac.compare_digest(digest(rfc8785.dumps(body)), parsed.integrity_hash):
        raise HTTPException(422, "Observation integrity mismatch")
    existing = db.scalar(
        select(Observation).where(
            Observation.endpoint_id == endpoint.id, Observation.producer_id == parsed.observation_id
        )
    )
    if existing:
        if existing.document != payload:
            raise HTTPException(409, "Observation ID was reused with different content")
        return existing
    if db.scalar(select(EvidenceManifest.id).where(EvidenceManifest.job_id == job.id)):
        raise HTTPException(409, "Job evidence is sealed by its immutable manifest")
    row = Observation(
        **provenance(job),
        case_id=hunt.case_id,
        job_id=job.id,
        endpoint_id=endpoint.id,
        producer_id=parsed.observation_id,
        collector=parsed.collector_id,
        integrity_hash=parsed.integrity_hash,
        document=payload,
    )
    db.add(row)
    db.flush()
    timestamp = parsed.source_time or parsed.timestamp
    if aware(timestamp) > datetime.now(UTC) + timedelta(minutes=5):
        raise HTTPException(422, "Observation timestamp exceeds allowed clock skew")
    timeline = TimelineEvent(
        **provenance(row),
        case_id=row.case_id,
        endpoint_id=endpoint.id,
        observation_id=row.id,
        timestamp=timestamp,
        time_basis="source" if parsed.source_time else "collection",
        collector=row.collector,
        severity=str(parsed.data.get("severity", "INFO")).upper()
        if str(parsed.data.get("severity", "INFO")).upper()
        in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
        else "INFO",
        type=parsed.type,
    )
    db.add(timeline)
    db.flush()
    publish(
        db,
        user,
        "observation.created",
        row.id,
        simulation=row.simulation,
        simulation_label=row.simulation_label,
    )
    publish(
        db,
        user,
        "timeline.created",
        timeline.id,
        simulation=row.simulation,
        simulation_label=row.simulation_label,
    )
    from jocky_control_plane.investigation import graph

    graph(db, row.case_id, user, persist=True)
    return row


def verify_manifest_document(
    db: Session, row: EvidenceManifest, user: User, store: ObjectStore | None = None
) -> dict[str, Any]:
    job: Job = owned(db, Job, row.job_id, user)
    endpoint: Endpoint = owned(db, Endpoint, job.endpoint_id, user)
    observations = db.scalars(
        select(Observation)
        .where(Observation.job_id == job.id)
        .order_by(Observation.created_at, Observation.id)
    ).all()
    document = row.document
    try:
        parsed = WireManifest.model_validate(document)
    except ValidationError:
        return {"integrity_valid": False, "provenance_valid": False, "schema_valid": False}
    hunt: Hunt = owned(db, Hunt, job.hunt_id, user)
    if job.variant_id is None:
        return {
            "integrity_valid": False,
            "provenance_valid": False,
            "simulation": row.simulation,
            "simulation_label": row.simulation_label,
        }
    variant: Variant = owned(db, Variant, job.variant_id, user)
    expected = {
        "case_id": str(hunt.case_id),
        "job_id": str(job.id),
        "endpoint_id": str(endpoint.id),
        "agent_identity": endpoint.identity,
        "simulation": job.simulation,
        "simulation_label": job.simulation_label,
        "variant_id": str(variant.id),
        "variant_seed": variant.seed,
        "llvm_ir_hash": variant.manifest.get("llvm_ir_hash"),
        **{
            field: (job.envelope or {}).get(field)
            for field in ("source_hash", "jir_hash", "artifact_hash", "execution_mode")
        },
    }
    if (job.envelope or {}).get("transport_mode") in {"DIRECT", "TRUSTED_RELAY"}:
        expected["transport_mode"] = (job.envelope or {})["transport_mode"]
    provenance_valid = all(document.get(field) == value for field, value in expected.items())
    provenance_valid = provenance_valid and expected["llvm_ir_hash"] is not None
    compilation: Compilation = owned(db, Compilation, hunt.compilation_id, user)
    version: ScriptVersion = owned(db, ScriptVersion, compilation.script_version_id, user)
    provenance_valid = provenance_valid and (
        variant.compilation_id == compilation.id and version.source_hash == document["source_hash"]
    )
    time_valid = parsed.completed_at <= datetime.now(UTC) + timedelta(minutes=5)
    time_valid = time_valid and parsed.started_at >= aware(job.created_at) - timedelta(minutes=5)
    artifacts = db.scalars(select(Artifact).where(Artifact.job_id == job.id)).all()
    artifact_hashes_valid = sorted(a.content_hash for a in artifacts) == sorted(
        parsed.artifact_hashes
    )
    artifact_content_valid = not artifacts
    if artifacts and store is not None:
        try:
            artifact_content_valid = all(
                digest(content := store.get(a.storage_key)) == a.content_hash
                and len(content) == a.size_bytes
                for a in artifacts
            )
        except (OSError, ValueError):
            artifact_content_valid = False
    actual = [observation.integrity_hash for observation in observations]
    declared = document.get("observation_hashes", [])
    valid_hashes = len(actual) == len(declared) and sorted(actual) == sorted(declared)
    valid_hashes = valid_hashes and all(
        digest(
            rfc8785.dumps({k: v for k, v in observation.document.items() if k != "integrity_hash"})
        )
        == observation.integrity_hash
        for observation in observations
    )
    signature_valid = False
    try:
        signature = document["signature"]
        if signature["algorithm"] == "Ed25519":
            key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(endpoint.public_key, validate=True)
            )
            key.verify(
                base64.b64decode(signature["value_base64"], validate=True),
                b"JOCKY:manifest:v1\n"
                + rfc8785.dumps({k: v for k, v in document.items() if k != "signature"}),
            )
            signature_valid = True
    except (ValueError, InvalidSignature, KeyError):
        pass
    return {
        "integrity_valid": valid_hashes
        and signature_valid
        and provenance_valid
        and time_valid
        and artifact_hashes_valid
        and artifact_content_valid,
        "provenance_valid": provenance_valid,
        "signature_valid": signature_valid,
        "observation_hashes_valid": valid_hashes,
        "timestamps_valid": time_valid,
        "artifact_hashes_valid": artifact_hashes_valid,
        "artifact_content_valid": artifact_content_valid,
        "simulation": row.simulation,
        "simulation_label": row.simulation_label,
    }


def ingest_manifest(
    db: Session,
    endpoint: Endpoint,
    payload: dict[str, Any],
    user: User,
    store: ObjectStore | None = None,
) -> EvidenceManifest:
    from jocky_contracts.evidence import EvidenceManifest as WireManifest

    parsed = WireManifest.model_validate(payload)
    job: Job = owned(db, Job, UUID(parsed.job_id), user)
    hunt: Hunt = owned(db, Hunt, job.hunt_id, user)
    if (
        job.endpoint_id != endpoint.id
        or parsed.endpoint_id != str(endpoint.id)
        or parsed.case_id != str(hunt.case_id)
        or parsed.simulation != job.simulation
        or parsed.simulation_label != job.simulation_label
        or job.envelope is None
    ):
        raise HTTPException(403, "Manifest provenance mismatch")
    if job.status not in {State.RUNNING, State.CANCEL_REQUESTED}:
        raise HTTPException(409, "Job is not accepting evidence manifests")
    for field in ("source_hash", "jir_hash", "variant_id", "artifact_hash", "execution_mode"):
        if payload[field] != job.envelope[field]:
            raise HTTPException(403, "Manifest build provenance mismatch")
    existing = db.scalar(select(EvidenceManifest).where(EvidenceManifest.job_id == job.id))
    if existing:
        if existing.document != payload:
            raise HTTPException(409, "Immutable manifest already exists")
        return existing
    row = EvidenceManifest(
        **provenance(job), job_id=job.id, document=payload, signature_verified=False
    )
    result = verify_manifest_document(db, row, user, store)
    if not result["integrity_valid"]:
        raise HTTPException(422, "Manifest signature or observation hashes do not verify")
    row.signature_verified = True
    db.add(row)
    db.flush()
    publish(
        db,
        user,
        "manifest.verified",
        row.id,
        simulation=row.simulation,
        simulation_label=row.simulation_label,
    )
    return row
