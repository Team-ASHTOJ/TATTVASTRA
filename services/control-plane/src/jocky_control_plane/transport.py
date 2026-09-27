"""TLS enrollment and mutually authenticated bidirectional agent transport."""

import base64
import importlib
import json
import queue
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import grpc  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from fastapi import HTTPException
from jocky_contracts.control import ArtifactUpload, JobProgress
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane import hunts
from jocky_control_plane.config import Settings
from jocky_control_plane.ingestion import ingest_manifest, ingest_observation
from jocky_control_plane.models import (
    AgentReceipt,
    Artifact,
    Endpoint,
    EvidenceManifest,
    Hunt,
    Job,
    Organization,
    Role,
    State,
    User,
    Variant,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.pki import enroll
from jocky_control_plane.security import aware, digest, owned, provenance, publish, sign

wire: Any = importlib.import_module("jocky_control_plane.generated.jocky.v1.agent_pb2")
service: Any = importlib.import_module("jocky_control_plane.generated.jocky.v1.agent_pb2_grpc")


class AgentControl:
    def __init__(
        self, factory: sessionmaker[Session], settings: Settings, transport_mode: str = "DIRECT"
    ) -> None:
        self.transport_mode = transport_mode
        self.factory = factory
        self.settings = settings

    def FetchJobArtifact(self, request: Any, context: Any) -> Any:
        fingerprint = self.identity(context)
        try:
            with self.factory.begin() as db:
                endpoint, user = self.peer(db, fingerprint)
                job = owned(db, Job, UUID(request.job_id), user)
                if job.endpoint_id != endpoint.id or job.status not in {
                    State.DISPATCHED,
                    State.RUNNING,
                }:
                    raise HTTPException(403, "Artifact is not assigned to this active endpoint job")
                if job.deadline and aware(job.deadline) <= datetime.now(UTC):
                    raise HTTPException(403, "Job expired")
                variant = owned(db, Variant, job.variant_id, user)
                content = ObjectStore(self.settings.object_root).get(variant.storage_key)
                if digest(content) != variant.content_hash:
                    raise HTTPException(409, "Stored compiler artifact integrity mismatch")
                hashed = variant.content_hash
                publish(
                    db,
                    user,
                    "artifact.agent_access",
                    variant.id,
                    {"job_id": str(job.id)},
                    simulation=job.simulation,
                    simulation_label=job.simulation_label,
                )
            for offset in range(0, len(content), 32768):
                yield wire.ArtifactChunk(
                    content_hash=hashed,
                    size_bytes=len(content),
                    offset=offset,
                    content=content[offset : offset + 32768],
                )
        except (HTTPException, ValueError, OSError) as error:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, str(error))

    def Enroll(self, request: Any, context: Any) -> Any:
        try:
            with self.factory.begin() as db:
                response = enroll(db, request, self.settings)
            return wire.EnrollmentResponse(**response)
        except (HTTPException, ValueError, OSError, InvalidSignature) as error:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, str(error))

    def identity(self, context: Any) -> str:
        certificate = context.auth_context().get("x509_pem_cert", [])
        if not certificate:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Enrolled client certificate required")
        parsed = x509.load_pem_x509_certificate(certificate[0])
        return parsed.fingerprint(hashes.SHA256()).hex()

    def peer(self, db: Session, fingerprint: str) -> tuple[Endpoint, User]:
        endpoint = db.scalar(
            select(Endpoint).where(Endpoint.certificate_fingerprint == fingerprint)
        )
        if endpoint is None or endpoint.status == State.REVOKED:
            raise HTTPException(401, "Endpoint identity revoked or unknown")
        # All distributed mutations acquire locks in tenant -> endpoint -> job order.
        db.scalar(
            select(Organization)
            .where(Organization.id == endpoint.organization_id)
            .with_for_update()
        )
        db.refresh(endpoint, with_for_update=True)
        user = db.scalar(
            select(User)
            .where(
                User.organization_id == endpoint.organization_id,
                User.role == Role.ADMIN,
                User.disabled.is_(False),
            )
            .limit(1)
        )
        if user is None:
            raise HTTPException(403, "Organization has no active authority")
        return endpoint, user

    def accept(self, frame: Any, fingerprint: str) -> Any:
        with self.factory.begin() as db:
            endpoint, user = self.peer(db, fingerprint)
            if (
                frame.schema_version != "1.0.0"
                or not frame.HasField("simulation")
                or frame.simulation != endpoint.simulation
                or frame.endpoint_id != str(endpoint.id)
                or frame.sequence < 1
            ):
                raise HTTPException(403, "Frame identity, version or simulation mismatch")
            frame_hash = digest(frame.SerializeToString(deterministic=True))
            existing = db.scalar(
                select(AgentReceipt).where(
                    AgentReceipt.endpoint_id == endpoint.id, AgentReceipt.sequence == frame.sequence
                )
            )
            if existing:
                if existing.frame_hash != frame_hash:
                    raise HTTPException(409, "Sequence replay contains changed bytes")
                receipt_id = existing.id
            else:
                if frame.sequence != endpoint.last_sequence + 1:
                    raise HTTPException(409, "Frame sequence is not contiguous")
                body = frame.WhichOneof("body")
                if body == "heartbeat":
                    timestamp = datetime.fromisoformat(
                        frame.heartbeat.timestamp.replace("Z", "+00:00")
                    )
                    if (
                        timestamp.tzinfo is None
                        or abs((datetime.now(UTC) - timestamp).total_seconds()) > 300
                    ):
                        raise HTTPException(422, "Heartbeat timestamp exceeds clock skew")
                    endpoint.transport_mode = self.transport_mode
                    endpoint.last_seen = datetime.now(UTC)
                    endpoint.status = State.ONLINE
                    publish(
                        db,
                        user,
                        "agent.state",
                        endpoint.id,
                        {"state": "ONLINE"},
                        simulation=endpoint.simulation,
                        simulation_label=endpoint.simulation_label,
                    )
                elif body in {"observation", "evidence_manifest", "job_progress", "artifact"}:
                    payload = json.loads(getattr(frame, body).json_utf8)
                    if body == "observation":
                        ingest_observation(db, endpoint, payload, user)
                    elif body == "evidence_manifest":
                        ingest_manifest(
                            db, endpoint, payload, user, ObjectStore(self.settings.object_root)
                        )
                    elif body == "artifact":
                        upload = ArtifactUpload.model_validate(payload)
                        job = owned(db, Job, upload.job_id, user)
                        if db.scalar(
                            select(EvidenceManifest.id).where(EvidenceManifest.job_id == job.id)
                        ):
                            raise HTTPException(
                                409, "Job evidence is sealed by its immutable manifest"
                            )
                        if (
                            job.endpoint_id != endpoint.id
                            or upload.simulation != job.simulation
                            or upload.simulation_label != job.simulation_label
                            or job.status not in {State.RUNNING, State.CANCEL_REQUESTED}
                        ):
                            raise HTTPException(403, "Artifact job provenance mismatch")
                        content = base64.b64decode(upload.content_base64, validate=True)
                        if digest(content) != upload.content_hash:
                            raise HTTPException(422, "Artifact content hash mismatch")
                        key = ObjectStore(self.settings.object_root).put(content)
                        hunt = owned(db, Hunt, job.hunt_id, user)
                        existing_artifact = db.scalar(
                            select(Artifact).where(
                                Artifact.job_id == job.id, Artifact.content_hash == key
                            )
                        )
                        if existing_artifact and (
                            existing_artifact.media_type != upload.media_type
                            or existing_artifact.size_bytes != len(content)
                        ):
                            raise HTTPException(
                                409, "Artifact hash was reused with conflicting metadata"
                            )
                        if existing_artifact is None:
                            artifact = Artifact(
                                **provenance(job),
                                case_id=hunt.case_id,
                                job_id=job.id,
                                content_hash=key,
                                size_bytes=len(content),
                                media_type=upload.media_type,
                                storage_key=key,
                            )
                            db.add(artifact)
                            db.flush()
                            publish(
                                db,
                                user,
                                "artifact.created",
                                artifact.id,
                                simulation=job.simulation,
                                simulation_label=job.simulation_label,
                            )
                    else:
                        progress = JobProgress.model_validate(payload)
                        job = owned(db, Job, progress.job_id, user)
                        if job.endpoint_id != endpoint.id:
                            raise HTTPException(403, "Job is assigned to another endpoint")
                        if progress.state == "SUCCESS" and not db.scalar(
                            select(EvidenceManifest).where(
                                EvidenceManifest.job_id == job.id,
                                EvidenceManifest.signature_verified.is_(True),
                            )
                        ):
                            raise HTTPException(
                                409, "Completion requires a verified evidence manifest"
                            )
                        job.progress = progress.measurements
                        hunts.transition(
                            db, job, State(progress.state), user, self.settings, progress.detail
                        )
                else:
                    raise HTTPException(422, "Unknown agent frame body")
                endpoint.last_sequence = frame.sequence
                receipt = AgentReceipt(
                    endpoint_id=endpoint.id, sequence=frame.sequence, frame_hash=frame_hash
                )
                db.add(receipt)
                db.flush()
                receipt_id = receipt.id
        # The transaction context has committed before a receipt is constructed.
        return wire.ControlFrame(
            schema_version="1.0.0",
            acknowledgement=wire.Acknowledgement(
                accepted_sequence=frame.sequence, receipt_id=str(receipt_id)
            ),
        )

    def dispatch(self, fingerprint: str, delivered: set[str]) -> list[Any]:
        outgoing = []
        with self.factory.begin() as db:
            endpoint, user = self.peer(db, fingerprint)
            jobs = db.scalars(
                select(Job)
                .where(
                    Job.endpoint_id == endpoint.id,
                    Job.status.in_(
                        [State.QUEUED, State.DISPATCHED, State.RUNNING, State.CANCEL_REQUESTED]
                    ),
                )
                .order_by(Job.created_at)
                .with_for_update()
            ).all()
            for job in jobs:
                if job.deadline and aware(job.deadline) <= datetime.now(UTC):
                    hunts.transition(
                        db, job, State.FAILED, user, self.settings, "Job deadline exceeded"
                    )
                    continue
                key = str(job.id) + ":" + job.status
                if key in delivered:
                    continue
                if job.status == State.CANCEL_REQUESTED:
                    cancellation = sign(
                        self.settings.signing_key_path,
                        {
                            "schema_version": "1.0.0",
                            "job_id": str(job.id),
                            "endpoint_id": str(endpoint.id),
                            "organization_id": str(endpoint.organization_id),
                            "simulation": job.simulation,
                            "simulation_label": job.simulation_label,
                            "issued_at": datetime.now(UTC).isoformat(),
                            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                            "nonce": secrets.token_hex(32),
                        },
                        b"JOCKY:cancel:v1\n",
                    )
                    outgoing.append(
                        wire.ControlFrame(
                            schema_version="1.0.0",
                            signed_cancellation=wire.CanonicalDocument(
                                json_utf8=json.dumps(cancellation).encode()
                            ),
                        )
                    )
                elif job.status in {State.QUEUED, State.DISPATCHED} and job.envelope:
                    if job.status == State.QUEUED:
                        hunts.transition(db, job, State.DISPATCHED, user, self.settings)
                    outgoing.append(
                        wire.ControlFrame(
                            schema_version="1.0.0",
                            signed_job=wire.CanonicalDocument(
                                json_utf8=json.dumps(job.envelope).encode()
                            ),
                        )
                    )
                delivered.add(str(job.id) + ":" + job.status)
        return outgoing

    def Exchange(self, request_iterator: Any, context: Any) -> Any:
        fingerprint = self.identity(context)
        incoming: queue.Queue[Any] = queue.Queue(maxsize=32)
        finished = threading.Event()

        def read() -> None:
            try:
                for frame in request_iterator:
                    while context.is_active():
                        try:
                            incoming.put(frame, timeout=0.2)
                            break
                        except queue.Full:
                            continue
            finally:
                finished.set()

        threading.Thread(target=read, daemon=True).start()
        delivered: set[str] = set()
        try:
            while context.is_active():
                try:
                    frame = incoming.get(timeout=0.25)
                    yield self.accept(frame, fingerprint)
                except queue.Empty:
                    if finished.is_set():
                        break
                yield from self.dispatch(fingerprint, delivered)
        except (HTTPException, ValueError, ValidationError) as error:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(error))


def serve(factory: sessionmaker[Session], settings: Settings) -> None:
    certificate = settings.tls_cert_path.read_bytes()
    key = settings.tls_key_path.read_bytes()
    ca = settings.tls_ca_path.read_bytes()
    servers = []
    listeners = [
        (settings.grpc_enrollment_bind, False, "DIRECT"),
        (settings.grpc_bind, True, "DIRECT"),
    ]
    if settings.grpc_relay_bind and settings.grpc_relay_enrollment_bind:
        listeners.extend(
            [
                (settings.grpc_relay_enrollment_bind, False, "TRUSTED_RELAY"),
                (settings.grpc_relay_bind, True, "TRUSTED_RELAY"),
            ]
        )
    for address, mutual, transport_mode in listeners:
        server = grpc.server(
            ThreadPoolExecutor(max_workers=32),
            maximum_concurrent_rpcs=32,
            options=[("grpc.max_receive_message_length", 1048576)],
        )
        service.add_AgentControlServicer_to_server(
            AgentControl(factory, settings, transport_mode), server
        )
        credentials = grpc.ssl_server_credentials(
            [(key, certificate)],
            root_certificates=ca if mutual else None,
            require_client_auth=mutual,
        )
        if not server.add_secure_port(address, credentials):
            raise RuntimeError(f"Could not bind TLS agent listener {address}")
        server.start()
        servers.append(server)
    try:
        servers[0].wait_for_termination()
    finally:
        for server in servers:
            server.stop(5).wait()
