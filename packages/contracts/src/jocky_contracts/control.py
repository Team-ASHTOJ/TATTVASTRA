"""Additive v1 request contracts for the persistent prototype APIs."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, JsonValue

from jocky_contracts.common import Contract, Hash, Provenance, Signature
from jocky_contracts.compiler import Budget


class LoginRequest(Contract):
    organization_id: UUID
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class UserCreate(Contract):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=256)
    role: Literal["ADMIN", "ANALYST", "VIEWER"]


class CaseCreate(Provenance):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)


class CasePatch(Contract):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["OPEN", "CLOSED"] | None = None


class ScriptCreate(Contract):
    case_id: UUID
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=262144)


class VersionCreate(Contract):
    source: str = Field(min_length=1, max_length=262144)


class BuildCreate(Contract):
    compilation_id: UUID
    count: int = Field(default=3, ge=1, le=8)
    target: Literal["host"] = "host"
    execution_mode: Literal["memory"] = "memory"
    seed: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    expected_semantic_hash: Hash | None = None


class TargetBuildCreate(Contract):
    targets: list[Literal["linux-x86_64", "linux-aarch64", "windows-x86_64"]] = Field(
        min_length=1, max_length=3
    )


class VariantCreate(Contract):
    count: int = Field(default=3, ge=1, le=16)


class VariantCompare(Contract):
    variant_ids: list[UUID] = Field(min_length=2, max_length=16)


class EnrollmentCreate(Provenance):
    capabilities: list[str] = Field(min_length=1, max_length=100)
    validity_seconds: int = Field(default=600, ge=60, le=3600)


class HuntCreate(Contract):
    case_id: UUID
    compilation_id: UUID
    endpoint_ids: list[UUID] = Field(min_length=1, max_length=1000)
    execution_mode: Literal["memory", "native"] = "memory"
    endpoint_modes: dict[UUID, Literal["memory", "native"]] = Field(default_factory=dict)
    enforcement_mode: Literal["MONITORED", "STRICT"] = "MONITORED"
    diverse: bool = True
    retry_limit: int = Field(default=0, ge=0, le=3)


class BenchmarkCreate(Contract):
    compilation_id: UUID
    repetitions: int = Field(default=3, ge=1, le=16)


class CompatibilityCreate(Contract):
    variant_id: UUID
    environment: str = Field(min_length=1, max_length=1000)
    security_product_label: str = Field(min_length=1, max_length=200)
    correctness: Literal["PASS", "FAIL", "NOT_MEASURED"]
    alert_observed: Literal["YES", "NO", "NOT_OBSERVED"]
    notes: str = Field(max_length=10000)
    endpoint_id: UUID | None = None


class ReportCreate(Contract):
    case_id: UUID
    format: Literal["json"] = "json"


class JobProgress(Contract):
    job_id: UUID
    state: Literal["RUNNING", "SUCCESS", "FAILED", "CANCELLED"]
    detail: str = Field(default="", max_length=4096)
    measurements: dict[str, JsonValue] = Field(default_factory=dict)


class ArtifactUpload(Provenance):
    job_id: UUID
    content_base64: str = Field(max_length=800000)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = Field(default="application/octet-stream", max_length=128)


class RemoteJobEnvelope(Provenance):
    transport_mode: Literal["DIRECT", "TRUSTED_RELAY", "UNKNOWN"] = "UNKNOWN"
    job_id: UUID
    case_id: UUID
    organization_id: UUID
    endpoint_id: UUID
    plan_id: UUID
    variant_id: UUID
    artifact_hash: Hash
    source_hash: Hash
    jir_hash: Hash
    execution_mode: Literal["memory", "native"]
    enforcement_mode: Literal["MONITORED", "STRICT"]
    build_manifest: dict[str, JsonValue]
    required_capabilities: list[str]
    budget: Budget
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    signature: Signature
