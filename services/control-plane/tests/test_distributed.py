"""Database and wire invariants. Synthetic records exist only inside tests."""

import base64
import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import grpc
import pytest
import rfc8785
from alembic import command
from alembic.config import Config
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jocky_control_plane.app import create_app
from jocky_control_plane.cli import initialize_keys
from jocky_control_plane.config import Settings
from jocky_control_plane.db import sessions
from jocky_control_plane.generated.jocky.v1 import agent_pb2 as wire
from jocky_control_plane.generated.jocky.v1 import agent_pb2_grpc as rpc
from jocky_control_plane.hunts import cancel, envelope, summarize, transition
from jocky_control_plane.ingestion import (
    ingest_manifest,
    ingest_observation,
    verify_manifest_document,
)
from jocky_control_plane.investigation import graph
from jocky_control_plane.models import (
    Artifact,
    AuditEvent,
    Case,
    Compilation,
    Endpoint,
    EventOutbox,
    EvidenceManifest,
    ExecutionPlan,
    Hunt,
    Job,
    Organization,
    Role,
    Script,
    ScriptVersion,
    State,
    User,
    Variant,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest, password_hash, provenance, publish, verify_audit
from jocky_control_plane.transport import AgentControl
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

ROOT = Path(__file__).resolve().parents[3]
PASSWORD = "test-only-long-password"


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'control.db').as_posix()}"
    pg_url = os.environ.get("JOCKY_TEST_DATABASE_URL")
    admin_engine = None
    schema = "test_jocky_" + uuid4().hex
    if pg_url:
        admin_engine = create_engine(pg_url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = (
            make_url(pg_url)
            .update_query_dict({"options": f"-csearch_path={schema}"})
            .render_as_string(hide_password=False)
        )
    monkeypatch.setenv("JOCKY_DATABASE_URL", url)
    command.upgrade(Config(str(ROOT / "services/control-plane/alembic.ini")), "head")
    settings = Settings(
        environment="test",
        database_url=url,
        object_root=tmp_path / "objects",
        signing_key_path=tmp_path / "signing.key",
        tls_ca_path=tmp_path / "ca.pem",
        tls_ca_key_path=tmp_path / "ca.key",
        tls_cert_path=tmp_path / "server.pem",
        tls_key_path=tmp_path / "server.key",
        event_stream_seconds=0.1,
    )
    initialize_keys(settings)
    factory = sessions(url)
    with factory.begin() as db:
        org = Organization(name="Test tenant")
        db.add(org)
        db.flush()
        admin = User(
            organization_id=org.id,
            username="admin",
            password_hash=password_hash(PASSWORD),
            role=Role.ADMIN,
        )
        viewer = User(
            organization_id=org.id,
            username="viewer",
            password_hash=password_hash(PASSWORD),
            role=Role.VIEWER,
        )
        db.add_all([admin, viewer])
        db.flush()
        org_id, admin_id = org.id, admin.id
        publish(db, admin, "test.initialized", org.id)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/auth/login",
            json={"organization_id": str(org_id), "username": "admin", "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        yield factory, settings, client, org_id, admin_id
    factory.kw["bind"].dispose()
    if admin_engine:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_migrations_and_rbac_tenant_isolation(runtime):
    factory, _, client, org_id, _ = runtime
    assert len(inspect(factory.kw["bind"]).get_table_names()) >= 25
    assert client.get("/api/cases", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": ""}).status_code == 401
    case = client.post("/api/cases", json={"title": "Evidence case", "simulation": False})
    assert case.status_code == 201, case.text
    identifier = case.json()["id"]
    login = client.post(
        "/api/auth/login",
        json={"organization_id": str(org_id), "username": "viewer", "password": PASSWORD},
    )
    viewer = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(f"/api/cases/{identifier}", headers=viewer).status_code == 200
    assert (
        client.patch(
            f"/api/cases/{identifier}", json={"status": "CLOSED"}, headers=viewer
        ).status_code
        == 403
    )
    with factory.begin() as db:
        analyst = User(
            organization_id=org_id,
            username="analyst",
            password_hash=password_hash(PASSWORD),
            role=Role.ANALYST,
        )
        db.add(analyst)
        db.flush()
        other = Organization(name="Other tenant")
        db.add(other)
        db.flush()
        private = Case(organization_id=other.id, title="Private")
        db.add(private)
        db.flush()
        private_id = private.id
    assert client.get(f"/api/cases/{private_id}").status_code == 404
    assert len(client.get("/api/cases").json()) == 1
    assert (
        client.post(
            "/api/cases",
            json={"title": "Wrong mode", "simulation": True, "simulation_label": "DEMO"},
        ).status_code
        == 409
    )
    legacy_payload = {
        "simulation": False,
        "source": 'hunt "auth-bound" {}',
        "target": {"os": "linux", "arch": "x86_64"},
        "execution_mode": "memory",
    }
    assert (
        client.post(
            "/api/v1/compilations",
            json=legacy_payload,
            headers={"Authorization": ""},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/compilations",
            json=legacy_payload,
            headers=viewer,
        ).status_code
        == 403
    )
    analyst_login = client.post(
        "/api/auth/login",
        json={"organization_id": str(org_id), "username": "analyst", "password": PASSWORD},
    )
    assert analyst_login.status_code == 200
    assert (
        client.post(
            "/api/v1/compilations",
            json=legacy_payload,
            headers={"Authorization": "Bearer " + analyst_login.json()["access_token"]},
        ).status_code
        == 501
    )


def test_script_versions_and_failed_compiler_are_durable(runtime):
    factory, _, client, _, _ = runtime
    case = client.post("/api/cases", json={"title": "Scripts", "simulation": False}).json()
    script = client.post(
        "/api/scripts", json={"case_id": case["id"], "name": "Baseline", "source": 'hunt "x" {}'}
    ).json()
    second = client.post(f"/api/scripts/{script['id']}/versions", json={"source": 'hunt "new" {}'})
    assert second.status_code == 201, second.text
    assert second.json()["version"] == 2
    compilation = client.post(f"/api/scripts/{script['id']}/compile")
    assert compilation.status_code == 201, compilation.text
    assert compilation.json()["status"] == "FAILED"
    assert compilation.json()["outputs"] == {}
    with factory() as db:
        assert len(db.scalars(select(ScriptVersion)).all()) == 2
        assert db.scalar(select(Compilation)).error


def setup_job(factory, org_id, simulation=False):
    """Explicit protocol fixture, not a compiler result or a live endpoint."""
    key = Ed25519PrivateKey.generate()
    with factory.begin() as db:
        case = Case(
            organization_id=org_id,
            title="Protocol fixture",
            simulation=simulation,
            simulation_label="TEST_FIXTURE" if simulation else None,
        )
        db.add(case)
        db.flush()
        script = Script(**provenance(case), case_id=case.id, name="Protocol fixture")
        db.add(script)
        db.flush()
        version = ScriptVersion(
            **provenance(case),
            script_id=script.id,
            source="test protocol bytes",
            source_hash=digest(b"test protocol bytes"),
            version=1,
        )
        db.add(version)
        db.flush()
        compilation = Compilation(
            **provenance(case), script_version_id=version.id, status=State.SUCCESS, outputs={}
        )
        db.add(compilation)
        db.flush()
        variant = Variant(
            **provenance(case),
            compilation_id=compilation.id,
            seed="0" * 16,
            manifest={"llvm_ir_hash": digest(b"fixture-llvm")},
            content_hash=digest(b"fixture"),
            storage_key=digest(b"fixture"),
        )
        plan = ExecutionPlan(
            **provenance(case),
            compilation_id=compilation.id,
            document={
                "source_hash": version.source_hash,
                "jir_hash": digest(b"fixture-jir"),
                "required_capabilities": ["process.read", "network.read"],
                "budget": {
                    "schema_version": "1.0.0",
                    "cpu_percent": 20,
                    "memory_bytes": 256000000,
                    "io_bytes": 150000000,
                    "duration_ms": 120000,
                },
            },
        )
        endpoint = Endpoint(
            **provenance(case),
            hostname="TEST-ONLY",
            target_os="linux",
            target_arch="x86_64",
            agent_version="TEST_FIXTURE",
            identity=digest(key.public_key().public_bytes_raw()),
            public_key=base64.b64encode(key.public_key().public_bytes_raw()).decode(),
            certificate_fingerprint=digest(b"test-cert"),
            capabilities=[],
            execution_modes=[],
        )
        db.add_all([variant, plan, endpoint])
        db.flush()
        hunt = Hunt(
            **provenance(case),
            case_id=case.id,
            compilation_id=compilation.id,
            endpoint_ids=[str(endpoint.id)],
            execution_mode="native",
            status=State.RUNNING,
        )
        db.add(hunt)
        db.flush()
        job = Job(
            **provenance(case),
            hunt_id=hunt.id,
            endpoint_id=endpoint.id,
            plan_id=plan.id,
            variant_id=variant.id,
            status=State.RUNNING,
            attempt=1,
            envelope={
                "source_hash": version.source_hash,
                "jir_hash": digest(b"fixture-jir"),
                "artifact_hash": variant.content_hash,
                "variant_id": str(variant.id),
                "execution_mode": "native",
            },
        )
        db.add(job)
        db.flush()
        return case.id, hunt.id, job.id, endpoint.id, variant.id, key


def observation_payload(db, identifiers, collector, data):
    case_id, _, job_id, endpoint_id, variant_id, _ = identifiers
    job = db.get(Job, job_id)
    value = {
        "schema_version": "1.0.0",
        "simulation": job.simulation,
        "simulation_label": job.simulation_label,
        "observation_id": str(uuid4()),
        "case_id": str(case_id),
        "endpoint_id": str(endpoint_id),
        "job_id": str(job_id),
        "collector_id": collector,
        "timestamp": datetime.now(UTC).isoformat(),
        "source_time": None,
        "type": collector,
        "data": data,
        "variant_id": str(variant_id),
        "source_hash": job.envelope["source_hash"],
        "jir_hash": job.envelope["jir_hash"],
    }
    value["integrity_hash"] = digest(rfc8785.dumps(value))
    return value


def test_observation_hash_simulation_and_correlation(runtime):
    factory, _, client, org_id, admin_id = runtime
    ids = setup_job(factory, org_id)
    with factory.begin() as db:
        user, endpoint = db.get(User, admin_id), db.get(Endpoint, ids[3])
        payload = observation_payload(
            db, ids, "processes", {"pid": 123, "signed": False, "user": "test"}
        )
        ingested = ingest_observation(db, endpoint, payload, user)
        assert ingest_observation(db, endpoint, payload, user).id == ingested.id
        connection = observation_payload(
            db, ids, "connections", {"pid": 123, "remote_address": "8.8.8.8"}
        )
        ingest_observation(db, endpoint, connection, user)
        graph(db, ids[0], user)
    findings = client.get("/api/findings", params={"case_id": str(ids[0])}).json()
    assert len(findings) == 1
    assert findings[0]["title"] == "Unsigned process with external connection"
    timeline = client.get(
        "/api/timeline", params={"case_id": str(ids[0]), "collector": "connections"}
    ).json()
    assert len(timeline) == 1
    for corrupt in ("hash", "simulation", "endpoint"):
        changed = copy.deepcopy(payload)
        if corrupt == "hash":
            changed["data"]["pid"] = 99
        elif corrupt == "simulation":
            changed.update(simulation=True, simulation_label="TEST_FIXTURE")
        else:
            changed["endpoint_id"] = str(uuid4())
        with factory.begin() as db, pytest.raises(HTTPException):
            ingest_observation(db, db.get(Endpoint, ids[3]), changed, db.get(User, admin_id))


def test_manifest_signature_actual_hashes_and_tampering(runtime):
    factory, _, _, org_id, admin_id = runtime
    ids = setup_job(factory, org_id)
    with factory.begin() as db:
        user, endpoint = db.get(User, admin_id), db.get(Endpoint, ids[3])
        payload = observation_payload(db, ids, "system", {"hostname": "test-only"})
        ingest_observation(db, endpoint, payload, user)
        job = db.get(Job, ids[2])
        now = datetime.now(UTC).isoformat()
        manifest = {
            "schema_version": "1.0.0",
            "simulation": False,
            "simulation_label": None,
            "case_id": str(ids[0]),
            "job_id": str(ids[2]),
            "endpoint_id": str(ids[3]),
            "agent_identity": endpoint.identity,
            **job.envelope,
            "llvm_ir_hash": digest(b"fixture-llvm"),
            "variant_seed": "0" * 16,
            "started_at": now,
            "completed_at": now,
            "observation_hashes": [payload["integrity_hash"]],
        }
        manifest["signature"] = {
            "status": "SIGNED",
            "algorithm": "Ed25519",
            "key_id": "test",
            "value_base64": base64.b64encode(
                ids[5].sign(b"JOCKY:manifest:v1\n" + rfc8785.dumps(manifest))
            ).decode(),
        }
        row = ingest_manifest(db, endpoint, manifest, user)
        assert verify_manifest_document(db, row, user)["integrity_valid"]
        tampered = EvidenceManifest(
            **provenance(row),
            job_id=row.job_id,
            document={**manifest, "observation_hashes": []},
            signature_verified=True,
        )
        assert not verify_manifest_document(db, tampered, user)["integrity_valid"]


def test_partial_hunt_and_cancellation_ack(runtime):
    factory, settings, _, org_id, admin_id = runtime
    ids = setup_job(factory, org_id)
    with factory.begin() as db:
        user, hunt, job = db.get(User, admin_id), db.get(Hunt, ids[1]), db.get(Job, ids[2])
        other_endpoint = Endpoint(
            **provenance(job),
            hostname="OTHER-TEST",
            target_os="windows",
            target_arch="x86_64",
            agent_version="TEST",
            identity=digest(b"other"),
            public_key="test-only",
            certificate_fingerprint=digest(b"other-cert"),
        )
        db.add(other_endpoint)
        db.flush()
        other = Job(
            **provenance(job),
            hunt_id=hunt.id,
            endpoint_id=other_endpoint.id,
            status=State.FAILED,
            attempt=1,
        )
        db.add(other)
        job.status = State.SUCCESS
        db.flush()
        summarize(db, hunt)
        assert hunt.status == State.PARTIAL
        job.status = State.RUNNING
        hunt.status = State.RUNNING
        cancel(db, hunt, user)
        assert job.status == State.CANCEL_REQUESTED
        transition(db, job, State.CANCELLED, user, settings)
        assert job.status == State.CANCELLED
        with pytest.raises(HTTPException):
            transition(db, job, State.RUNNING, user, settings)


def test_objects_reports_audit_and_modified_bytes(runtime):
    factory, settings, client, org_id, admin_id = runtime
    case = client.post("/api/cases", json={"title": "Report", "simulation": False}).json()
    report = client.post("/api/reports", json={"case_id": case["id"]})
    assert report.status_code == 201, report.text
    report_status = client.get(f"/api/reports/{report.json()['id']}")
    assert report_status.status_code == 200
    assert report_status.json()["status"] == "SUCCESS"
    identifier = report.json()["artifact_id"]
    downloaded = client.get(f"/api/artifacts/{identifier}/content")
    assert downloaded.status_code == 200
    assert b'"audit_verification"' in downloaded.content
    assert client.post(f"/api/artifacts/{identifier}/verify").json()["integrity_valid"]
    with factory() as db:
        artifact = db.get(Artifact, UUID(identifier))
        ObjectStore(settings.object_root).path(artifact.storage_key).write_bytes(b"modified")
    assert not client.post(f"/api/artifacts/{identifier}/verify").json()["integrity_valid"]
    assert client.get(f"/api/artifacts/{identifier}/content").status_code == 409
    assert client.get("/api/audit/verify").json()["integrity_valid"]
    with factory.begin() as db:
        user = db.get(User, admin_id)
        event = db.scalar(select(AuditEvent).where(AuditEvent.organization_id == org_id))
        if db.bind.dialect.name == "postgresql":
            with pytest.raises(DBAPIError), db.begin_nested():
                event.document = {**event.document, "action": "modified"}
                db.flush()
            assert verify_audit(db, user)["integrity_valid"]
            organization = db.get(Organization, org_id)
            organization.audit_head = "f" * 64
            db.flush()
            assert not verify_audit(db, user)["integrity_valid"]
        else:
            event.document = {**event.document, "action": "modified"}
            db.flush()
            assert not verify_audit(db, user)["integrity_valid"]


def test_grpc_tls_enrollment_heartbeat_replay_and_wrong_identity(runtime):
    factory, settings, client, org_id, admin_id = runtime
    token = client.post(
        "/api/endpoints/enrollments", json={"simulation": False, "capabilities": ["system.read"]}
    ).json()["one_time_token"]
    authority = AgentControl(factory, settings)
    servers = []
    for mutual in (False, True):
        server = grpc.server(ThreadPoolExecutor(max_workers=4))
        rpc.add_AgentControlServicer_to_server(authority, server)
        port = server.add_secure_port(
            "127.0.0.1:0",
            grpc.ssl_server_credentials(
                [(settings.tls_key_path.read_bytes(), settings.tls_cert_path.read_bytes())],
                root_certificates=settings.tls_ca_path.read_bytes() if mutual else None,
                require_client_auth=mutual,
            ),
        )
        server.start()
        servers.append((server, port))
    key = ec.generate_private_key(ec.SECP256R1())
    evidence_key = Ed25519PrivateKey.generate()
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .sign(key, hashes.SHA256())
    )
    request = wire.EnrollmentRequest(
        schema_version="1.0.0",
        one_time_token=token,
        certificate_signing_request_pem=csr.public_bytes(serialization.Encoding.PEM),
        agent_version="test",
        target_os="linux",
        target_arch="x86_64",
        simulation=False,
        hostname="TEST",
        evidence_public_key=evidence_key.public_key().public_bytes_raw(),
        evidence_key_proof=evidence_key.sign(
            b"JOCKY:enroll:v1\n" + csr.public_bytes(serialization.Encoding.PEM)
        ),
    )
    try:
        with grpc.secure_channel(
            f"localhost:{servers[0][1]}",
            grpc.ssl_channel_credentials(settings.tls_ca_path.read_bytes()),
        ) as channel:
            peer = rpc.AgentControlStub(channel)
            response = peer.Enroll(request, timeout=5)
            with pytest.raises(grpc.RpcError):
                peer.Enroll(request, timeout=5)
            with pytest.raises(grpc.RpcError):
                list(peer.Exchange(iter([]), timeout=5))
        credentials = grpc.ssl_channel_credentials(
            settings.tls_ca_path.read_bytes(),
            private_key=key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
            certificate_chain=response.certificate_chain_pem,
        )
        with grpc.secure_channel(f"localhost:{servers[1][1]}", credentials) as channel:
            peer = rpc.AgentControlStub(channel)
            frame = wire.AgentFrame(
                schema_version="1.0.0",
                endpoint_id=response.endpoint_id,
                sequence=1,
                simulation=False,
                heartbeat=wire.Heartbeat(timestamp=datetime.now(UTC).isoformat(), state="IDLE"),
            )
            first = list(peer.Exchange(iter([frame]), timeout=5))[0]
            replay = list(peer.Exchange(iter([frame]), timeout=5))[0]
            assert first.acknowledgement.receipt_id == replay.acknowledgement.receipt_id
            frame.endpoint_id = str(uuid4())
            with pytest.raises(grpc.RpcError):
                list(peer.Exchange(iter([frame]), timeout=5))
            # A protocol fixture tests transport, not native artifact execution.
            ids = list(setup_job(factory, org_id))
            ids[3], ids[5] = UUID(response.endpoint_id), evidence_key
            with factory.begin() as db:
                job = db.get(Job, ids[2])
                job.endpoint_id, job.status = ids[3], State.QUEUED
                hunt = db.get(Hunt, ids[1])
                hunt.endpoint_ids = [response.endpoint_id]
                variant = db.get(Variant, ids[4])
                ObjectStore(settings.object_root).put(b"fixture")
                job.envelope = envelope(
                    job, hunt, db.get(ExecutionPlan, job.plan_id), variant, settings
                )
                assigned = job.envelope
            frame.endpoint_id = response.endpoint_id
            dispatch = list(peer.Exchange(iter([frame]), timeout=5))
            signed = next(item for item in dispatch if item.WhichOneof("body") == "signed_job")
            assert json.loads(signed.signed_job.json_utf8) == assigned
            # Reconnect resends the identical signed job, not a new job/nonce.
            reconnect = list(peer.Exchange(iter([frame]), timeout=5))
            assert any(item == signed for item in reconnect)
            chunks = list(
                peer.FetchJobArtifact(wire.JobArtifactRequest(job_id=str(ids[2])), timeout=5)
            )
            assert b"".join(chunk.content for chunk in chunks) == b"fixture"
            assert chunks[0].content_hash == digest(b"fixture")
            with pytest.raises(grpc.RpcError):
                list(peer.FetchJobArtifact(wire.JobArtifactRequest(job_id=str(uuid4())), timeout=5))

            def send(sequence, kind, payload):
                outgoing = wire.AgentFrame(
                    schema_version="1.0.0",
                    endpoint_id=response.endpoint_id,
                    sequence=sequence,
                    simulation=False,
                    **{kind: wire.CanonicalDocument(json_utf8=json.dumps(payload).encode())},
                )
                return list(peer.Exchange(iter([outgoing]), timeout=5))

            send(2, "job_progress", {"job_id": str(ids[2]), "state": "RUNNING"})
            with pytest.raises(grpc.RpcError):
                send(3, "job_progress", {"job_id": str(ids[2]), "state": "SUCCESS"})
            with factory() as db:
                observed = observation_payload(db, ids, "system", {"hostname": "protocol-fixture"})
                endpoint_identity = db.get(Endpoint, ids[3]).identity
            send(3, "observation", observed)
            now = datetime.now(UTC).isoformat()
            manifest = {
                "schema_version": "1.0.0",
                "simulation": False,
                "simulation_label": None,
                "case_id": str(ids[0]),
                "job_id": str(ids[2]),
                "endpoint_id": str(ids[3]),
                "agent_identity": endpoint_identity,
                "variant_seed": "0" * 16,
                "llvm_ir_hash": digest(b"fixture-llvm"),
                "started_at": now,
                "completed_at": now,
                "observation_hashes": [observed["integrity_hash"]],
                **{
                    field: assigned[field]
                    for field in (
                        "source_hash",
                        "jir_hash",
                        "variant_id",
                        "artifact_hash",
                        "execution_mode",
                    )
                },
            }
            manifest["signature"] = {
                "status": "SIGNED",
                "algorithm": "Ed25519",
                "key_id": "test",
                "value_base64": base64.b64encode(
                    evidence_key.sign(b"JOCKY:manifest:v1\n" + rfc8785.dumps(manifest))
                ).decode(),
            }
            send(4, "evidence_manifest", manifest)
            send(5, "job_progress", {"job_id": str(ids[2]), "state": "SUCCESS"})
            with factory() as db:
                assert db.get(Hunt, ids[1]).status == State.SUCCESS
            # Cancellation is requested by an operator and becomes terminal only on agent ACK.
            with factory.begin() as db:
                hunt = db.get(Hunt, ids[1])
                hunt.status = State.RUNNING
                job = Job(
                    **provenance(hunt),
                    hunt_id=hunt.id,
                    endpoint_id=ids[3],
                    attempt=2,
                    status=State.RUNNING,
                    plan_id=db.get(Job, ids[2]).plan_id,
                    variant_id=ids[4],
                )
                db.add(job)
                db.flush()
                cancelled_id = job.id
                cancel(db, hunt, db.get(User, admin_id))
            cancellation = list(peer.Exchange(iter([frame]), timeout=5))
            assert any(item.WhichOneof("body") == "signed_cancellation" for item in cancellation)
            send(6, "job_progress", {"job_id": str(cancelled_id), "state": "CANCELLED"})
            with factory() as db:
                assert db.get(Hunt, ids[1]).status == State.CANCELLED
    finally:
        for server, _ in servers:
            server.stop(0).wait()
    assert client.get("/api/endpoints").json()[0]["status"] == "ONLINE"


def test_transaction_rollback_does_not_publish_events(runtime):
    factory, _, _, org_id, admin_id = runtime
    with factory() as db:
        before = len(db.scalars(select(EventOutbox)).all())
    with pytest.raises(RuntimeError), factory.begin() as db:
        publish(db, db.get(User, admin_id), "test.rollback", org_id)
        raise RuntimeError("Injected transaction failure")
    with factory() as db:
        assert len(db.scalars(select(EventOutbox)).all()) == before


def test_sse_committed_cursor_and_retry_identity(runtime):
    factory, settings, client, org_id, admin_id = runtime
    result = client.get("/api/events")
    assert result.status_code == 200
    assert "event: auth.login" in result.text
    cursor = max(int(line[4:]) for line in result.text.splitlines() if line.startswith("id: "))
    resumed = client.get("/api/events", headers={"Last-Event-ID": str(cursor)})
    assert "event: auth.login" not in resumed.text
    ids = setup_job(factory, org_id)
    with factory.begin() as db:
        hunt = db.get(Hunt, ids[1])
        hunt.retry_limit = 1
        job = db.get(Job, ids[2])
        transition(db, job, State.FAILED, db.get(User, admin_id), settings, "Test disconnect")
        retry = db.scalar(select(Job).where(Job.retry_of == job.id))
        assert retry.id != job.id and retry.attempt == 2
        assert retry.endpoint_id == job.endpoint_id and retry.variant_id == job.variant_id
        assert retry.envelope["job_id"] == str(retry.id) and retry.envelope["nonce"]
        assert hunt.status == State.RUNNING
