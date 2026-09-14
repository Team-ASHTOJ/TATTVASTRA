"""Prototype password sessions, Ed25519 signing and transactional audit/outbox."""

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.models import (
    AuditEvent,
    EventOutbox,
    Organization,
    Scoped,
    SessionToken,
    User,
)


def session_user(db: Session, authorization: str | None) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer session required")
    token = db.scalar(
        select(SessionToken).where(SessionToken.token_hash == digest(authorization[7:].encode()))
    )
    if token is None or aware(token.expires_at) <= datetime.now(UTC):
        raise HTTPException(401, "Session expired or invalid")
    user = db.get(User, token.user_id)
    if user is None or user.disabled:
        raise HTTPException(401, "Session expired or invalid")
    return user


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def password_hash(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${hashed.hex()}"


def password_matches(password: str, encoded: str) -> bool:
    _, salt, expected = encoded.split("$")
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(actual.hex(), expected)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def provenance(row: Scoped) -> dict[str, Any]:
    return {
        "organization_id": row.organization_id,
        "simulation": row.simulation,
        "simulation_label": row.simulation_label,
    }


def owned(db: Session, model: Any, identifier: UUID, user: User) -> Any:
    row = db.scalar(
        select(model).where(model.id == identifier, model.organization_id == user.organization_id)
    )
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row


def publish(
    db: Session,
    user: User,
    action: str,
    resource: UUID,
    data: dict[str, Any] | None = None,
    simulation: bool = False,
    simulation_label: str | None = None,
) -> None:
    # Lock the tenant head BEFORE allocating the offset; this makes commit order
    # match SSE/audit sequence order even across independent API/agent workers.
    organization = db.scalar(
        select(Organization).where(Organization.id == user.organization_id).with_for_update()
    )
    if organization is None:
        raise HTTPException(404, "Organization not found")
    document: dict[str, Any] = {
        "schema_version": "1.0.0",
        "organization_id": str(organization.id),
        "actor_id": str(user.id),
        "sequence": organization.audit_sequence,
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "resource_id": str(resource),
        "data": data or {},
        "previous_hash": organization.audit_head,
        "simulation": simulation,
        "simulation_label": simulation_label,
    }
    hashed = digest(rfc8785.dumps(document))
    db.add(
        AuditEvent(
            organization_id=organization.id,
            sequence=organization.audit_sequence,
            document=document,
            integrity_hash=hashed,
        )
    )
    db.add(
        EventOutbox(
            organization_id=organization.id,
            sequence=organization.audit_sequence,
            topic=action,
            resource_id=resource,
            data=data or {},
            simulation=simulation,
            simulation_label=simulation_label,
        )
    )
    organization.audit_sequence += 1
    organization.audit_head = hashed


def verify_audit(db: Session, user: User) -> dict[str, Any]:
    organization = db.scalar(
        select(Organization).where(Organization.id == user.organization_id).with_for_update()
    )
    assert organization is not None
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.organization_id == user.organization_id)
        .order_by(AuditEvent.sequence)
    ).all()
    previous = "0" * 64
    for sequence, event in enumerate(events):
        if (
            event.sequence != sequence
            or event.document.get("sequence") != sequence
            or event.document.get("previous_hash") != previous
            or event.document.get("organization_id") != str(user.organization_id)
            or digest(rfc8785.dumps(event.document)) != event.integrity_hash
        ):
            return {
                "integrity_valid": False,
                "first_invalid_sequence": sequence,
                "externally_anchored": False,
            }
        previous = event.integrity_hash
    return {
        "integrity_valid": bool(events)
        and previous == organization.audit_head
        and len(events) == organization.audit_sequence,
        "checked_events": len(events),
        "head": previous,
        "externally_anchored": False,
    }


def sign(path: Path, document: dict[str, Any], domain: bytes = b"JOCKY:job:v1\n") -> dict[str, Any]:
    if not path.is_file():
        raise HTTPException(503, "Control-plane signing authority is not initialized")
    key = Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    body = {k: v for k, v in document.items() if k != "signature"}
    signature = key.sign(domain + rfc8785.dumps(body))
    return {
        **body,
        "signature": {
            "status": "SIGNED",
            "algorithm": "Ed25519",
            "key_id": "control-plane",
            "value_base64": base64.b64encode(signature).decode(),
        },
    }
