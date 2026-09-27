"""Explicit local provisioning, migration and server commands."""

import argparse
import ipaddress
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from sqlalchemy import select

from jocky_control_plane.config import Settings
from jocky_control_plane.db import sessions
from jocky_control_plane.models import Organization, Role, User
from jocky_control_plane.security import password_hash, publish


def secret(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def initialize_keys(settings: Settings) -> None:
    if not settings.signing_key_path.exists():
        secret(settings.signing_key_path, ed25519.Ed25519PrivateKey.generate().private_bytes_raw())
    if settings.tls_ca_path.exists():
        # Preserve previously issued identities; never silently regenerate a CA.
        for path in (settings.tls_ca_key_path, settings.tls_key_path, settings.tls_cert_path):
            if not path.exists():
                raise RuntimeError("Incomplete TLS provisioning; restore the original key material")
        ensure_relay_name(settings)
        return
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "JOCKY local prototype CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_key = ec.generate_private_key(ec.SECP256R1())
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=90))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("control-plane"),
                    x509.DNSName("agent-control"),
                    x509.DNSName("trusted-relay"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    secret(
        settings.tls_ca_key_path,
        ca_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    secret(
        settings.tls_key_path,
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    secret(settings.tls_cert_path, certificate.public_bytes(serialization.Encoding.PEM))
    secret(settings.tls_ca_path, ca.public_bytes(serialization.Encoding.PEM))


def ensure_relay_name(settings: Settings) -> None:
    """Renew only the server certificate; keep the CA and all endpoint identities."""
    old = x509.load_pem_x509_certificate(settings.tls_cert_path.read_bytes())
    san = old.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if "trusted-relay" in san.get_values_for_type(x509.DNSName):
        return
    ca = x509.load_pem_x509_certificate(settings.tls_ca_path.read_bytes())
    key = serialization.load_pem_private_key(settings.tls_ca_key_path.read_bytes(), None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise RuntimeError("Expected the provisioned ECDSA CA")
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(old.subject)
        .issuer_name(ca.subject)
        .public_key(old.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=90))
    )
    for extension in old.extensions:
        value = (
            x509.SubjectAlternativeName([*san, x509.DNSName("trusted-relay")])
            if isinstance(extension.value, x509.SubjectAlternativeName)
            else extension.value
        )
        builder = builder.add_extension(value, extension.critical)
    replacement = settings.tls_cert_path.with_suffix(".renewed")
    replacement.write_bytes(
        builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)
    )
    replacement.chmod(0o600)
    replacement.replace(settings.tls_cert_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="JOCKY control-plane administration")
    parser.add_argument("command", choices=["init", "grpc", "sweep", "demo"])
    arguments = parser.parse_args()
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("JOCKY_DATABASE_URL is required")
    factory = sessions(settings.database_url)
    if arguments.command == "init":
        initialize_keys(settings)
        with factory.begin() as db:
            organization = db.scalar(
                select(Organization).where(Organization.name == "Local development")
            )
            if organization is None:
                password = os.environ.get("JOCKY_BOOTSTRAP_PASSWORD", "")
                if len(password) < 12:
                    raise SystemExit(
                        "Set JOCKY_BOOTSTRAP_PASSWORD (12+ characters); no default password"
                    )
                organization = Organization(name="Local development")
                db.add(organization)
                db.flush()
                user = User(
                    organization_id=organization.id,
                    username="admin",
                    password_hash=password_hash(password),
                    role=Role.ADMIN,
                )
                db.add(user)
                db.flush()
                publish(db, user, "organization.initialized", organization.id)
            print(f"Organization: {organization.id}; login username: admin")
    elif arguments.command == "grpc":
        from jocky_control_plane.transport import serve

        serve(factory, settings)
    elif arguments.command == "sweep":
        from jocky_control_plane.scheduler import run

        run(factory, settings)
    elif arguments.command == "demo":
        from jocky_control_plane.demo import load

        load(factory, settings)


if __name__ == "__main__":
    main()
