"""Local prototype CA; service listeners never fall back to plaintext."""

import base64
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from jocky_control_plane.config import Settings
from jocky_control_plane.models import Endpoint, EndpointEnrollment, State
from jocky_control_plane.security import aware, digest


def enroll(db: Session, request: Any, settings: Settings) -> dict[str, Any]:
    if (
        request.schema_version != "1.0.0"
        or not request.HasField("simulation")
        or request.target_os not in {"windows", "linux"}
        or request.target_arch not in {"x86_64", "aarch64"}
        or not request.hostname
        or not set(request.execution_modes).issubset({"native", "memory"})
    ):
        raise HTTPException(422, "Invalid enrollment contract")
    token = db.scalar(
        select(EndpointEnrollment)
        .where(EndpointEnrollment.token_hash == digest(request.one_time_token.encode()))
        .with_for_update()
    )
    if token is None or token.consumed_at or aware(token.expires_at) <= datetime.now(UTC):
        raise HTTPException(401, "Enrollment token expired or consumed")
    if token.simulation != request.simulation:
        raise HTTPException(403, "Enrollment simulation mismatch")
    csr = x509.load_pem_x509_csr(request.certificate_signing_request_pem)
    public = csr.public_key()
    if not csr.is_signature_valid or not isinstance(public, ec.EllipticCurvePublicKey):
        raise HTTPException(422, "Enrollment requires a valid ECDSA TLS CSR")
    evidence_key = ed25519.Ed25519PublicKey.from_public_bytes(request.evidence_public_key)
    evidence_key.verify(
        request.evidence_key_proof, b"JOCKY:enroll:v1\n" + request.certificate_signing_request_pem
    )
    identifier = uuid4()
    ca = x509.load_pem_x509_certificate(settings.tls_ca_path.read_bytes())
    key = serialization.load_pem_private_key(settings.tls_ca_key_path.read_bytes(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise HTTPException(503, "Invalid CA key configuration")
    expiry = datetime.now(UTC) + timedelta(days=1)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, str(identifier))]))
        .issuer_name(ca.subject)
        .public_key(public)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(expiry)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.UniformResourceIdentifier(f"urn:jocky:endpoint:{identifier}")]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    raw_public = evidence_key.public_bytes_raw()
    endpoint = Endpoint(
        id=identifier,
        organization_id=token.organization_id,
        simulation=token.simulation,
        simulation_label=token.simulation_label,
        hostname=request.hostname[:255],
        target_os=request.target_os,
        target_arch=request.target_arch,
        agent_version=request.agent_version[:64],
        identity=digest(raw_public),
        public_key=base64.b64encode(raw_public).decode(),
        certificate_fingerprint=certificate.fingerprint(hashes.SHA256()).hex(),
        capabilities=token.capabilities,
        execution_modes=list(request.execution_modes),
        status=State.OFFLINE,
    )
    db.add(endpoint)
    db.flush()
    token.consumed_at = datetime.now(UTC)
    token.endpoint_id = endpoint.id
    signing = ed25519.Ed25519PrivateKey.from_private_bytes(settings.signing_key_path.read_bytes())
    return {
        "endpoint_id": str(identifier),
        "organization_id": str(endpoint.organization_id),
        "certificate_chain_pem": certificate.public_bytes(serialization.Encoding.PEM),
        "trust_bundle_pem": settings.tls_ca_path.read_bytes(),
        "expires_at": expiry.isoformat(),
        "job_authority_public_key": signing.public_key().public_bytes_raw(),
    }
