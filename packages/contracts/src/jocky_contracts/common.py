from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal["1.0.0"] = "1.0.0"


class Provenance(Contract):
    simulation: StrictBool
    simulation_label: str | None = None

    @model_validator(mode="after")
    def require_simulation_label(self) -> "Provenance":
        if self.simulation and not (self.simulation_label or "").strip():
            raise ValueError("Simulated data requires an explicit DEMO/SIMULATED label")
        if not self.simulation and self.simulation_label is not None:
            raise ValueError("Real data must not carry a simulation label")
        return self


class Mode(StrEnum):
    REAL = "REAL"
    DEMO = "DEMO"


class ImplementationStatus(StrEnum):
    PLANNED = "PLANNED"
    SCAFFOLDED = "SCAFFOLDED"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    BLOCKED_ENVIRONMENT = "BLOCKED_ENVIRONMENT"


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Signature(Contract):
    status: Literal["UNSIGNED", "SIGNED", "VERIFIED", "INVALID", "UNAVAILABLE"]
    algorithm: Literal["Ed25519"] | None = None
    key_id: Identifier | None = None
    value_base64: str | None = None

    @model_validator(mode="after")
    def require_signature_material(self) -> "Signature":
        material = (self.algorithm, self.key_id, self.value_base64)
        if self.status in {"SIGNED", "VERIFIED", "INVALID"} and not all(material):
            raise ValueError("Signature status requires algorithm, key ID, and signature bytes")
        if self.status in {"UNSIGNED", "UNAVAILABLE"} and any(material):
            raise ValueError("Unsigned/unavailable status cannot contain signature material")
        return self


class Problem(Provenance):
    code: str
    detail: str
    status: int = Field(ge=400, le=599)
    retryable: bool = False
    request_id: str | None = None


class Timestamped(Provenance):
    timestamp: AwareDatetime
