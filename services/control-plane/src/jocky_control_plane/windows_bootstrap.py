"""Bounded Windows bootstrap credential and activation lifecycle helpers."""

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from sqlalchemy.orm import Session

from jocky_control_plane.config import Settings
from jocky_control_plane.models import WindowsBootstrap
from jocky_control_plane.security import digest


def credential(db: Session, authorization: str | None) -> WindowsBootstrap:
    if authorization is None or not authorization.startswith("Bootstrap "):
        raise HTTPException(401, "Windows bootstrap credential required")
    try:
        identifier, secret = authorization[10:].split(".", 1)
        row = db.get(WindowsBootstrap, UUID(identifier))
    except (ValueError, TypeError):
        row = None
        secret = ""
    if row is None or not secrets.compare_digest(row.credential_hash, digest(secret.encode())):
        raise HTTPException(401, "Windows bootstrap credential invalid")
    return row


def activation_token(settings: Settings, row: WindowsBootstrap) -> str:
    if row.activation_id is None:
        raise RuntimeError("activation is not initialized")
    private = Ed25519PrivateKey.from_private_bytes(settings.signing_key_path.read_bytes())
    key = private.private_bytes_raw()
    message = f"JOCKY:windows-bootstrap:v1:{row.id}:{row.activation_id}".encode()
    value = hmac.new(key, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def polled(row: WindowsBootstrap) -> bool:
    return (
        row.last_poll_at is not None
        and (datetime.now(UTC) - row.last_poll_at).total_seconds() <= 30
    )
