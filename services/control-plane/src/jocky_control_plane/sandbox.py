"""Deterministic Windows sandbox endpoint for cross-platform demonstration.

This is explicitly NOT a native Windows agent. The sandbox endpoint is an ordinary
persisted ``Endpoint`` row carrying ``simulation=True`` and ``transport_mode="SANDBOX"``;
its liveness is derived on read so the demo stays visually ONLINE without touching
the authenticated AgentControl heartbeat, TLS enrolment, or execution workers.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.models import Endpoint, State, User
from jocky_control_plane.security import digest

HOSTNAME = "WINDOWS-SANDBOX-01"
LABEL = "WINDOWS SANDBOX"
TRANSPORT = "SANDBOX"
TARGET_OS = "windows"
TARGET_ARCH = "x86_64"
AGENT_VERSION = "SANDBOX"
EXECUTION_MODES = ["sandbox"]
CAPABILITIES = ["system.read", "process.read", "network.read"]


def is_sandbox(row: dict[str, Any]) -> bool:
    return bool(row.get("simulation")) and row.get("transport_mode") == TRANSPORT


def project(row: dict[str, Any]) -> dict[str, Any]:
    """Derive simulated liveness. Real endpoints are returned untouched."""
    if is_sandbox(row):
        row["status"] = str(State.ONLINE)
        row["last_seen"] = datetime.now(UTC).isoformat()
    return row


def ensure(db: Session, user: User) -> tuple[Endpoint, bool]:
    """Return the organization's single sandbox endpoint, creating it at most once.

    The caller holds the organization row lock for non-GET requests, so repeated or
    concurrent starts serialize and can never produce a second WINDOWS-SANDBOX-01.
    """
    row = db.scalar(
        select(Endpoint).where(
            Endpoint.organization_id == user.organization_id,
            Endpoint.hostname == HOSTNAME,
        )
    )
    if row is not None:
        return row, False
    row = Endpoint(
        organization_id=user.organization_id,
        simulation=True,
        simulation_label=LABEL,
        transport_mode=TRANSPORT,
        hostname=HOSTNAME,
        target_os=TARGET_OS,
        target_arch=TARGET_ARCH,
        agent_version=AGENT_VERSION,
        # Organization-scoped so identity/ fingerprint stay unique across tenants.
        identity=digest(f"{HOSTNAME}:{user.organization_id}".encode()),
        public_key="",
        certificate_fingerprint=digest(f"sandbox:{HOSTNAME}:{user.organization_id}".encode()),
        capabilities=list(CAPABILITIES),
        execution_modes=list(EXECUTION_MODES),
        status=State.ONLINE,
        last_seen=datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return row, True
