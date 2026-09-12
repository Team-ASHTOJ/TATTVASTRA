from typing import Literal

from pydantic import AwareDatetime, Field

from jocky_contracts.common import Hash, Identifier, Provenance, Severity
from jocky_contracts.compiler import CompilerMetrics, ExecutionMode


class Organization(Provenance):
    organization_id: Identifier
    name: str


class User(Provenance):
    user_id: Identifier
    organization_id: Identifier
    subject: str
    role: Literal["viewer", "analyst", "operator", "administrator"]


class Case(Provenance):
    case_id: Identifier
    organization_id: Identifier
    title: str
    created_at: AwareDatetime
    state: Literal["OPEN", "CLOSED", "ARCHIVED"]


class Script(Provenance):
    script_id: Identifier
    organization_id: Identifier
    name: str


class ScriptVersion(Provenance):
    script_version_id: Identifier
    script_id: Identifier
    source: str
    source_hash: Hash
    version: int = Field(ge=1)
    created_at: AwareDatetime


class Compilation(Provenance):
    compilation_id: Identifier
    script_version_id: Identifier
    source_hash: Hash
    state: Literal["REQUESTED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]
    metrics: CompilerMetrics
    variant_ids: list[Identifier]


class Artifact(Provenance):
    artifact_id: Identifier
    case_id: Identifier
    job_id: Identifier
    endpoint_id: Identifier
    collector_id: Identifier
    variant_id: Identifier
    content_hash: Hash
    size_bytes: int = Field(ge=0)
    storage_key: str
    media_type: str
    timestamp: AwareDatetime


class Finding(Provenance):
    finding_id: Identifier
    case_id: Identifier
    title: str
    severity: Severity
    observation_ids: list[Identifier] = Field(min_length=1)
    timestamp: AwareDatetime


class TimelineEvent(Provenance):
    event_id: Identifier
    case_id: Identifier
    endpoint_id: Identifier
    observation_id: Identifier
    timestamp: AwareDatetime
    time_basis: Literal["source", "collection"]
    severity: Severity
    summary: str


class Report(Provenance):
    report_id: Identifier
    case_id: Identifier
    format: Literal["json", "pdf"]
    artifact_id: Identifier
    generated_at: AwareDatetime


class BenchmarkRun(Provenance):
    benchmark_run_id: Identifier
    environment: str
    variant_id: Identifier
    execution_mode: ExecutionMode
    repetitions: int = Field(ge=1)
    compiler_metrics: CompilerMetrics
    runtime_ms: float | None = Field(default=None, ge=0)
    peak_memory_bytes: int | None = Field(default=None, ge=0)


class CompatibilityRun(Provenance):
    compatibility_run_id: Identifier
    environment: str
    security_product_label: str
    variant_id: Identifier
    execution_mode: ExecutionMode
    completed: bool | None
    correctness: Literal["PASS", "FAIL", "NOT_MEASURED"]
    alert_observed: Literal["YES", "NO", "NOT_OBSERVED"]
    runtime_ms: float | None = Field(default=None, ge=0)
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    peak_memory_bytes: int | None = Field(default=None, ge=0)
    notes: str
