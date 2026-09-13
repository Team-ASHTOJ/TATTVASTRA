from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from jocky_contracts.common import Contract, Hash, Identifier, Provenance, Signature


class ExecutionMode(StrEnum):
    NATIVE = "native"
    MEMORY = "memory"
    VM = "vm"


class Target(Contract):
    os: Literal["windows", "linux"]
    arch: Literal["x86_64", "aarch64"]


class Budget(Contract):
    cpu_percent: int = Field(gt=0, le=100)
    memory_bytes: int = Field(gt=0, le=9007199254740991)
    io_bytes: int = Field(ge=0, le=9007199254740991)
    duration_ms: int = Field(gt=0, le=86400000)


class CompilerMetrics(Contract):
    lex_ms: float | None = Field(default=None, ge=0)
    parse_ms: float | None = Field(default=None, ge=0)
    semantic_ms: float | None = Field(default=None, ge=0)
    jir_ms: float | None = Field(default=None, ge=0)
    variant_ms: float | None = Field(default=None, ge=0)
    llvm_generation_ms: float | None = Field(default=None, ge=0)
    optimize_ms: float | None = Field(default=None, ge=0)
    optimization_ms: float | None = Field(default=None, ge=0)
    aot_compile_ms: float | None = Field(default=None, ge=0)
    aot_ms: float | None = Field(default=None, ge=0)
    jit_compile_ms: float | None = Field(default=None, ge=0)
    execution_ms: float | None = Field(default=None, ge=0)
    peak_memory_bytes: int | None = Field(default=None, ge=0)


class LiteralEncryption(Contract):
    enabled: bool
    algorithm: Literal["AES-256-GCM", "ChaCha20-Poly1305"] | None = None
    key_id: Identifier | None = None
    pool_hash: Hash | None = None
    nonce_policy: Literal["unique-per-key-and-build"] | None = None

    @model_validator(mode="after")
    def validate_encryption_metadata(self) -> "LiteralEncryption":
        fields = (self.algorithm, self.key_id, self.pool_hash, self.nonce_policy)
        if self.enabled and not all(fields):
            raise ValueError("Enabled literal encryption requires complete non-secret metadata")
        if not self.enabled and any(fields):
            raise ValueError("Disabled encryption cannot claim encryption metadata")
        return self


class VariantManifest(Provenance):
    source_hash: Hash
    jir_hash: Hash
    llvm_ir_hash: Hash
    variant_id: Identifier
    variant_seed: str = Field(pattern=r"^[0-9a-f]{16}$")
    compiler_version: str
    llvm_version: str
    target_os: Literal["windows", "linux"]
    target_arch: Literal["x86_64", "aarch64"]
    execution_mode: ExecutionMode
    artifact_hash: Hash
    semantic_test_hash: Hash | None
    semantic_test_status: Literal["NOT_RUN", "PASS", "FAIL"]
    created_at: AwareDatetime
    signature: Signature
    literal_encryption: LiteralEncryption

    @model_validator(mode="after")
    def validate_semantics(self) -> "VariantManifest":
        if (self.semantic_test_status == "NOT_RUN") != (self.semantic_test_hash is None):
            raise ValueError("Semantic test hash must match whether equivalence was tested")
        return self


class Diagnostic(Contract):
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    line: int = Field(ge=1)
    column: int = Field(ge=1)
    end_line: int = Field(ge=1)
    end_column: int = Field(ge=1)


class CompileRequest(Provenance):
    source: str = Field(min_length=1, max_length=262144)
    target: Target
    execution_mode: ExecutionMode
    variant_seed: str = Field(default="0000000000000000", pattern=r"^[0-9a-f]{16}$")
    profile: Literal["minimal", "balanced"] = "balanced"


class ExecutionPlan(Provenance):
    plan_id: Identifier
    case_id: Identifier
    source_hash: Hash
    jir_hash: Hash
    endpoint_ids: list[Identifier] = Field(min_length=1, max_length=1000)
    required_capabilities: list[str]
    execution_mode: ExecutionMode
    budget: Budget
    policy_version: str
    expires_at: AwareDatetime
