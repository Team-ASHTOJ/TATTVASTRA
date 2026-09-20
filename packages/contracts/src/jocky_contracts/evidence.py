from typing import Literal

import rfc8785
from pydantic import AwareDatetime, Field, JsonValue, model_validator

from jocky_contracts.common import Contract, Hash, Identifier, Provenance, Signature
from jocky_contracts.compiler import ExecutionMode


class Observation(Provenance):
    observation_id: Identifier
    case_id: Identifier
    endpoint_id: Identifier
    job_id: Identifier
    collector_id: Identifier
    timestamp: AwareDatetime
    source_time: AwareDatetime | None
    type: str = Field(min_length=1)
    data: dict[str, JsonValue]
    variant_id: Identifier
    source_hash: Hash
    jir_hash: Hash
    integrity_hash: Hash


class EvidenceManifest(Provenance):
    case_id: Identifier
    endpoint_id: Identifier
    agent_identity: Identifier
    job_id: Identifier
    source_hash: Hash
    jir_hash: Hash
    llvm_ir_hash: Hash
    variant_id: Identifier
    variant_seed: str = Field(pattern=r"^[0-9a-f]{16}$")
    artifact_hash: Hash
    execution_mode: ExecutionMode
    started_at: AwareDatetime
    completed_at: AwareDatetime
    observation_hashes: list[Hash]
    # Additive v1 field: legacy manifests without uploaded objects remain valid.
    artifact_hashes: list[Hash] = Field(default_factory=list)
    signature: Signature

    @model_validator(mode="after")
    def validate_collection_bounds(self) -> "EvidenceManifest":
        if self.completed_at < self.started_at:
            raise ValueError("Evidence completion cannot precede collection start")
        if len(self.observation_hashes) != len(set(self.observation_hashes)):
            raise ValueError("Evidence manifest cannot repeat observation hashes")
        if len(self.artifact_hashes) != len(set(self.artifact_hashes)):
            raise ValueError("Evidence manifest cannot repeat artifact hashes")
        return self


class AuditEvent(Provenance):
    sequence: int = Field(ge=0)
    organization_id: Identifier
    actor_id: Identifier
    action: str
    timestamp: AwareDatetime
    resource_id: Identifier
    previous_hash: Hash
    data: dict[str, JsonValue]
    integrity_hash: Hash


class IntegrityResult(Provenance):
    observation_id: Identifier
    expected_hash: Hash
    computed_hash: Hash
    integrity_valid: bool
    signature_status: Literal["NOT_CHECKED"] = "NOT_CHECKED"
    verification_scope: Literal["SUBMITTED_OBSERVATION_ONLY"] = "SUBMITTED_OBSERVATION_ONLY"


class AuditVerification(Contract):
    integrity_valid: bool
    checked_events: int
    first_invalid_sequence: int | None
    externally_anchored: Literal[False] = False


def canonical_bytes(model: Contract, exclude: set[str] | None = None) -> bytes:
    """RFC 8785 over schema-normalized JSON; callers must validate before hashing."""
    return rfc8785.dumps(model.model_dump(mode="json", exclude=exclude or set()))


def integrity_hash(model: Contract) -> str:
    import hashlib

    return hashlib.sha256(canonical_bytes(model, {"integrity_hash"})).hexdigest()


def verify_observation(observation: Observation) -> IntegrityResult:
    import hmac

    computed = integrity_hash(observation)
    return IntegrityResult(
        simulation=observation.simulation,
        simulation_label=observation.simulation_label,
        observation_id=observation.observation_id,
        expected_hash=observation.integrity_hash,
        computed_hash=computed,
        integrity_valid=hmac.compare_digest(computed, observation.integrity_hash),
    )


def verify_audit_chain(events: list[AuditEvent]) -> AuditVerification:
    import hmac

    previous = "0" * 64
    for sequence, event in enumerate(events):
        valid = (
            event.sequence == sequence
            and hmac.compare_digest(previous, event.previous_hash)
            and hmac.compare_digest(event.integrity_hash, integrity_hash(event))
            and event.organization_id == events[0].organization_id
        )
        if not valid:
            return AuditVerification(
                integrity_valid=False,
                checked_events=sequence + 1,
                first_invalid_sequence=sequence,
            )
        previous = event.integrity_hash
    return AuditVerification(
        integrity_valid=bool(events), checked_events=len(events), first_invalid_sequence=None
    )
