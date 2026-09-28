"""Durable, organization-scoped control-plane entities (PostgreSQL authority)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from jocky_control_plane.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class State(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    INCOMPATIBLE = "INCOMPATIBLE"
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    REVOKED = "REVOKED"


class Entity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Scoped(Entity):
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    simulation: Mapped[bool] = mapped_column(Boolean, default=False)
    simulation_label: Mapped[str | None] = mapped_column(String(128))


class Organization(Entity, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))
    audit_sequence: Mapped[int] = mapped_column(default=0)
    audit_head: Mapped[str] = mapped_column(String(64), default="0" * 64)


class User(Scoped, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "username"),)
    username: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, create_constraint=True))
    disabled: Mapped[bool] = mapped_column(default=False)


class SessionToken(Entity, Base):
    __tablename__ = "session_tokens"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentReceipt(Entity, Base):
    __tablename__ = "agent_receipts"
    __table_args__ = (UniqueConstraint("endpoint_id", "sequence"),)
    endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("endpoints.id"))
    sequence: Mapped[int]
    frame_hash: Mapped[str] = mapped_column(String(64))


class Case(Scoped, Base):
    __tablename__ = "cases"
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.OPEN)


class Endpoint(Scoped, Base):
    __tablename__ = "endpoints"
    transport_mode: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    hostname: Mapped[str] = mapped_column(String(255))
    target_os: Mapped[str] = mapped_column(String(16))
    target_arch: Mapped[str] = mapped_column(String(16))
    agent_version: Mapped[str] = mapped_column(String(64))
    identity: Mapped[str] = mapped_column(String(128), unique=True)
    public_key: Mapped[str] = mapped_column(Text)
    certificate_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    execution_modes: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sequence: Mapped[int] = mapped_column(default=0)
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.OFFLINE)


class EndpointEnrollment(Scoped, Base):
    __tablename__ = "endpoint_enrollments"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("endpoints.id"))
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)


class WindowsBootstrap(Scoped, Base):
    """Preinstalled Windows supervisor registration and bounded desired state."""

    __tablename__ = "windows_bootstraps"
    __table_args__ = (UniqueConstraint("organization_id", "hostname"),)
    hostname: Mapped[str] = mapped_column(String(255), default="WINDOWS-01")
    credential_hash: Mapped[str] = mapped_column(String(64), unique=True)
    desired_state: Mapped[str] = mapped_column(String(32), default="STOPPED")
    reported_state: Mapped[str] = mapped_column(String(32), default="READY")
    activation_id: Mapped[UUID | None]
    endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("endpoints.id"))
    enrollment_id: Mapped[UUID | None] = mapped_column(ForeignKey("endpoint_enrollments.id"))
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class Script(Scoped, Base):
    __tablename__ = "scripts"
    name: Mapped[str] = mapped_column(String(200))
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"))


class ScriptVersion(Scoped, Base):
    __tablename__ = "script_versions"
    __table_args__ = (UniqueConstraint("script_id", "version"),)
    script_id: Mapped[UUID] = mapped_column(ForeignKey("scripts.id"))
    version: Mapped[int]
    source: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))


class Compilation(Scoped, Base):
    __tablename__ = "compilations"
    script_version_id: Mapped[UUID] = mapped_column(ForeignKey("script_versions.id"))
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.CREATED)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class BuildState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"


class BuildRun(Scoped, Base):
    __tablename__ = "build_runs"
    compilation_id: Mapped[UUID] = mapped_column(ForeignKey("compilations.id"))
    status: Mapped[BuildState] = mapped_column(
        Enum(BuildState, native_enum=False), default=BuildState.QUEUED
    )
    seed: Mapped[str] = mapped_column(String(16))
    variant_count: Mapped[int]
    target: Mapped[str] = mapped_column(String(128), default="host")
    execution_mode: Mapped[str] = mapped_column(String(16), default="memory")
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Variant(Scoped, Base):
    __tablename__ = "variants"
    build_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("build_runs.id"))
    compilation_id: Mapped[UUID] = mapped_column(ForeignKey("compilations.id"))
    seed: Mapped[str] = mapped_column(String(16))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(Text)


class ExecutionPlan(Scoped, Base):
    __tablename__ = "execution_plans"
    compilation_id: Mapped[UUID] = mapped_column(ForeignKey("compilations.id"))
    document: Mapped[dict[str, Any]] = mapped_column(JSON)


class Hunt(Scoped, Base):
    __tablename__ = "hunts"
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"))
    compilation_id: Mapped[UUID] = mapped_column(ForeignKey("compilations.id"))
    endpoint_ids: Mapped[list[str]] = mapped_column(JSON)
    execution_mode: Mapped[str] = mapped_column(String(16))
    endpoint_modes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    enforcement_mode: Mapped[str] = mapped_column(String(16), default="MONITORED")
    diverse: Mapped[bool] = mapped_column(default=True)
    retry_limit: Mapped[int] = mapped_column(default=0)
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.CREATED)


class Job(Scoped, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("hunt_id", "endpoint_id", "attempt"),)
    hunt_id: Mapped[UUID] = mapped_column(ForeignKey("hunts.id"))
    endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("endpoints.id"))
    variant_id: Mapped[UUID | None] = mapped_column(ForeignKey("variants.id"))
    plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("execution_plans.id"))
    attempt: Mapped[int] = mapped_column(default=1)
    retry_of: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.QUEUED)
    envelope: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Observation(Scoped, Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("endpoint_id", "producer_id"),)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"))
    endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("endpoints.id"))
    producer_id: Mapped[str] = mapped_column(String(128))
    collector: Mapped[str] = mapped_column(String(128))
    integrity_hash: Mapped[str] = mapped_column(String(64))
    document: Mapped[dict[str, Any]] = mapped_column(JSON)


class Artifact(Scoped, Base):
    __tablename__ = "artifacts"
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"))
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    content_hash: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int]
    media_type: Mapped[str] = mapped_column(String(128))
    storage_key: Mapped[str] = mapped_column(Text)


class EvidenceManifest(Scoped, Base):
    __tablename__ = "evidence_manifests"
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"), unique=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    signature_verified: Mapped[bool]


class Finding(Scoped, Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("case_id", "rule_key"),)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"))
    rule_key: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(16))
    observation_ids: Mapped[list[str]] = mapped_column(JSON)


class TimelineEvent(Scoped, Base):
    __tablename__ = "timeline_events"
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("endpoints.id"))
    observation_id: Mapped[UUID] = mapped_column(ForeignKey("observations.id"), unique=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    time_basis: Mapped[str] = mapped_column(String(16))
    collector: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16))
    type: Mapped[str] = mapped_column(String(128))


class AuditEvent(Entity, Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("organization_id", "sequence"),)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    sequence: Mapped[int]
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    integrity_hash: Mapped[str] = mapped_column(String(64))


class EventOutbox(Scoped, Base):
    __tablename__ = "event_outbox"
    __table_args__ = (UniqueConstraint("organization_id", "sequence"),)
    sequence: Mapped[int]
    topic: Mapped[str] = mapped_column(String(128))
    resource_id: Mapped[UUID]
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class BenchmarkRun(Scoped, Base):
    __tablename__ = "benchmark_runs"
    compilation_id: Mapped[UUID] = mapped_column(ForeignKey("compilations.id"))
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.CREATED)
    measurements: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


class CompatibilityRun(Scoped, Base):
    __tablename__ = "compatibility_runs"
    variant_id: Mapped[UUID] = mapped_column(ForeignKey("variants.id"))
    endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("endpoints.id"))
    observations: Mapped[dict[str, Any]] = mapped_column(JSON)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class Report(Scoped, Base):
    __tablename__ = "reports"
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"))
    artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("artifacts.id"))
    status: Mapped[State] = mapped_column(Enum(State, native_enum=False), default=State.CREATED)
    format: Mapped[str] = mapped_column(String(16), default="json")
