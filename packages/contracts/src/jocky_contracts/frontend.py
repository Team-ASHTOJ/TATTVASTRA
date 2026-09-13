"""Static frontend documents. These contain plans and types, never endpoint observations."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from .common import Contract, Hash
from .compiler import Budget


class FrontendNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class SourcePosition(FrontendNode):
    offset: int = Field(ge=0, le=262144)
    line: int = Field(ge=1)
    column: int = Field(ge=1)


class SourceSpan(FrontendNode):
    start: SourcePosition
    end: SourcePosition

    @model_validator(mode="after")
    def ordered(self) -> "SourceSpan":
        if self.end.offset < self.start.offset:
            raise ValueError("Source span must be ordered")
        return self


class FrontendDiagnostic(FrontendNode):
    code: Annotated[str, Field(pattern=r"^[EW][0-9]{3}$")]
    message: str
    severity: Literal["error", "warning"]
    span: SourceSpan
    help: str
    source_line: str | None = None


class JirType(FrontendNode):
    name: str
    nullable: bool
    domain: str
    fields: dict[str, "JirType"]


class FrontendTarget(FrontendNode):
    kind: Literal["target", "host", "group"]
    value: str = Field(min_length=1)


class FrontendVariant(FrontendNode):
    enabled: bool
    seed: Annotated[str, Field(pattern=r"^(auto|[0-9a-f]{16})$")]
    profile: Literal["minimal", "balanced"]
    seed_resolution: Literal["EXPLICIT", "DEFERRED_TO_BUILD_FORGE"]


class FrontendRuntime(FrontendNode):
    backend: Literal["llvm"]
    execution: Literal["native", "memory"]
    variant: FrontendVariant


class JirInstruction(FrontendNode):
    id: int = Field(ge=0)
    opcode: str
    family: Literal[
        "SYSTEM",
        "PROCESS",
        "NETWORK",
        "FILESYSTEM",
        "LOGS",
        "PERSISTENCE",
        "DRIVER",
        "ANALYSIS",
        "EVIDENCE",
    ]
    inputs: list[int]
    result_type: JirType
    attributes: dict[str, JsonValue]
    span: SourceSpan
    required_capabilities: list[str]
    resource_class: Literal[
        "bounded_inventory",
        "bounded_content_io",
        "bounded_materialization",
        "bounded_output",
        "linear_transform",
    ]
    effect: Literal["pure", "read", "emit"]
    effect_predecessor: int | None
    target_os: list[Literal["windows", "linux"]]


class JirModule(Contract):
    kind: Literal["JIRModule"]
    compiler_version: Literal["0.3.0"]
    source_hash: Hash
    hunt: str
    case: str
    targets: list[FrontendTarget]
    target_os: list[Literal["windows", "linux"]] = Field(min_length=1)
    required_capabilities: list[str]
    budget: Budget
    runtime: FrontendRuntime
    instructions: list[JirInstruction] = Field(max_length=65536)
    executable: Literal[False]

    @model_validator(mode="after")
    def ssa_and_effects(self) -> "JirModule":
        previous: int | None = None
        for index, instruction in enumerate(self.instructions):
            if instruction.id != index or any(i < 0 or i >= index for i in instruction.inputs):
                raise ValueError("JIR requires sequential IDs and earlier SSA operands")
            expected = None if instruction.effect == "pure" else previous
            if instruction.effect_predecessor != expected:
                raise ValueError("JIR effect chain is invalid")
            if instruction.effect != "pure":
                previous = index
            if not set(instruction.required_capabilities) <= set(self.required_capabilities):
                raise ValueError("Instruction capability missing from module")
            if instruction.target_os != self.target_os:
                raise ValueError("Instruction target constraints differ from module")
        return self


class PushdownCandidate(FrontendNode):
    collector_instruction_id: int = Field(ge=0)
    branch_instruction_id: int = Field(ge=0)
    kind: Literal["filter", "project"]
    scope: Literal["BRANCH_LOCAL"]
    applied: Literal[False]
    attributes: dict[str, JsonValue]
    condition: Literal["REQUIRES_ADAPTER_SUPPORT_AND_BRANCH_DEPENDENCY_PRESERVATION"]


class ProjectedFields(FrontendNode):
    instruction_id: int = Field(ge=0)
    fields: list[str]


class ResultSchema(FrontendNode):
    instruction_id: int = Field(ge=0)
    result_type: JirType


class FrontendExecutionPlan(Contract):
    kind: Literal["FrontendExecutionPlan"]
    source_hash: Hash
    jir_hash: Hash
    targets: list[FrontendTarget]
    target_os: list[Literal["windows", "linux"]] = Field(min_length=1)
    required_collectors: list[str]
    required_capabilities: list[str]
    pushdown: list[PushdownCandidate]
    projected_fields: list[ProjectedFields]
    expected_result_schemas: list[ResultSchema]
    budget: Budget
    runtime: FrontendRuntime
    warnings: list[FrontendDiagnostic]
    dispatchable: Literal[False]
    admission_status: Literal["REQUIRES_ENDPOINT_POLICY_AND_LLVM_LOWERING"]


class FrontendCheck(Contract):
    kind: Literal["FrontendCheck"]
    valid: Literal[True]
    hunt: str
    source_hash: Hash
    jir_hash: Hash
    instruction_count: int = Field(ge=0, le=65536)
    warnings: list[FrontendDiagnostic]
    executable: Literal[False]


class FrontendFailure(Contract):
    kind: Literal["FrontendFailure"]
    valid: Literal[False]
    diagnostics: list[FrontendDiagnostic] = Field(min_length=1)
