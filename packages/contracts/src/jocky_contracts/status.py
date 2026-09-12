from typing import Literal

from pydantic import AwareDatetime, Field

from jocky_contracts.common import ImplementationStatus, Mode, Provenance


class CapabilityStatus(Provenance):
    id: str
    title: str
    implementation: str
    subsystem: str
    demo_evidence: str
    status: ImplementationStatus
    phase: str
    safety_environment_note: str


class PlatformStatus(Provenance):
    name: Literal["JOCKY"] = "JOCKY"
    version: str
    tagline: Literal["One Language. Every Endpoint. No Noise."]
    phase: str
    mode: Mode
    operational: bool
    observed_at: AwareDatetime
    capabilities: list[CapabilityStatus]


class EndpointList(Provenance):
    available: Literal[False] = False
    reason: str
    items: list[dict[str, str]] = Field(default_factory=list, max_length=0)


class Health(Provenance):
    status: Literal["alive", "not_ready"]
    service: str
    version: str
    reason: str | None = None
