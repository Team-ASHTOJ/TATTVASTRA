from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field, JsonValue, StrictBool, model_validator

from jocky_contracts.common import Contract, Hash, Identifier, Provenance, Signature
from jocky_contracts.compiler import Budget, ExecutionMode, Target


class EndpointState(StrEnum):
    ONLINE = "ONLINE"
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    UNTRUSTED = "UNTRUSTED"
    VERSION_MISMATCH = "VERSION_MISMATCH"


class JobState(StrEnum):
    CREATED = "CREATED"
    COMPILED = "COMPILED"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    VERIFIED = "VERIFIED"
    ARCHIVED = "ARCHIVED"


JOB_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.CREATED: frozenset({JobState.COMPILED, JobState.FAILED, JobState.CANCELLED}),
    JobState.COMPILED: frozenset({JobState.VALIDATED, JobState.FAILED, JobState.CANCELLED}),
    JobState.VALIDATED: frozenset({JobState.QUEUED, JobState.FAILED, JobState.CANCELLED}),
    JobState.QUEUED: frozenset({JobState.DISPATCHED, JobState.FAILED, JobState.CANCELLED}),
    JobState.DISPATCHED: frozenset({JobState.RUNNING, JobState.FAILED, JobState.CANCELLED}),
    JobState.RUNNING: frozenset({JobState.SUCCESS, JobState.FAILED, JobState.CANCELLED}),
    JobState.SUCCESS: frozenset({JobState.VERIFIED}),
    JobState.FAILED: frozenset({JobState.ARCHIVED}),
    JobState.CANCELLED: frozenset({JobState.ARCHIVED}),
    JobState.VERIFIED: frozenset({JobState.ARCHIVED}),
    JobState.ARCHIVED: frozenset(),
}


def validate_transition(current: JobState, target: JobState) -> None:
    if target not in JOB_TRANSITIONS[current]:
        raise ValueError(f"Invalid job transition: {current} -> {target}")


class Endpoint(Provenance):
    endpoint_id: Identifier
    organization_id: Identifier
    hostname: str
    target: Target
    agent_version: str
    state: EndpointState
    last_seen: AwareDatetime | None
    identity_fingerprint: Hash
    capabilities: list[str]
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    memory_bytes: int | None = Field(default=None, ge=0)
    active_job_id: Identifier | None = None


class SignedJob(Provenance):
    job_id: Identifier
    case_id: Identifier
    organization_id: Identifier
    endpoint_id: Identifier
    plan_id: Identifier
    variant_id: Identifier
    artifact_hash: Hash
    source_hash: Hash
    jir_hash: Hash
    execution_mode: ExecutionMode
    required_capabilities: list[str]
    budget: Budget
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    signature: Signature

    @model_validator(mode="after")
    def validate_envelope(self) -> "SignedJob":
        if self.expires_at <= self.issued_at:
            raise ValueError("Job expiry must be after issuance")
        if self.signature.status not in {"SIGNED", "VERIFIED"}:
            raise ValueError("Job envelope requires a signature; trust still requires verification")
        return self


class Job(Provenance):
    job_id: Identifier
    case_id: Identifier
    endpoint_id: Identifier
    plan_id: Identifier
    state: JobState
    attempt: int = Field(ge=1)
    retry_of: Identifier | None = None


class AgentPlatform(Contract):
    os: Literal["windows", "linux"]
    arch: Literal["x86_64", "aarch64"]


class AgentCollectorRequest(Contract):
    collector: Identifier
    path: str | None = None
    recursive: StrictBool = False
    hash: StrictBool = False
    limit: int = Field(default=1000, ge=1, le=100000)


class AgentResourceBudget(Budget):
    max_result_bytes: int = Field(gt=0, le=9007199254740991)
    max_file_count: int = Field(gt=0, le=9007199254740991)
    max_file_bytes: int = Field(ge=0, le=9007199254740991)


class AgentSignedJob(Provenance):
    job_id: Identifier
    case_id: Identifier
    organization_id: Identifier
    endpoint_id: Identifier
    required_capabilities: list[str]
    collectors: list[AgentCollectorRequest] = Field(min_length=1, max_length=1000)
    budget: AgentResourceBudget
    enforcement_policy: Literal["STRICT", "MONITORED"]
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    signature: Signature

    @model_validator(mode="after")
    def validate_agent_job(self) -> "AgentSignedJob":
        if self.simulation:
            raise ValueError("REAL endpoint jobs cannot contain simulation provenance")
        if self.expires_at <= self.issued_at:
            raise ValueError("Job expiry must be after issuance")
        if self.signature.status not in {"SIGNED", "VERIFIED"}:
            raise ValueError("Agent job requires signature material")
        return self


class AgentObservation(Provenance):
    observation_id: Identifier
    endpoint_id: Identifier
    job_id: Identifier
    case_id: Identifier
    collector: Identifier
    observed_at: AwareDatetime
    source_time: AwareDatetime | None
    platform: AgentPlatform
    data: dict[str, JsonValue]
    integrity_hash: Hash

    @model_validator(mode="after")
    def reject_simulated_real_observation(self) -> "AgentObservation":
        if self.simulation:
            raise ValueError("AgentObservation is the REAL endpoint envelope")
        return self


class AgentEnforcement(Contract):
    timeout: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    result_size: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    file_count: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    file_bytes: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    concurrency: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    cpu: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    memory: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
    network_bytes: Literal["ENFORCED", "OBSERVED_ONLY", "UNSUPPORTED"]
