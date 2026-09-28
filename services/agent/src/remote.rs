//! TLS enrollment, authenticated job admission, durable protobuf replay and
//! supervision of compiler-generated execution workers.
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use base64::{engine::general_purpose::STANDARD, Engine};
use chrono::{DateTime, Utc};
use fs2::FileExt;
use prost::Message;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tonic::transport::{Certificate, Channel, ClientTlsConfig, Identity};

use crate::error::{AgentError, Result};
use crate::evidence::domain_bytes;
use crate::identity::AgentState;
use crate::remote_worker::{budget, hash};
use crate::spool::Spool;
use crate::wire::{self, agent_control_client::AgentControlClient, agent_frame, control_frame};

#[derive(Serialize, Deserialize)]
struct Binding {
    endpoint_id: String,
    organization_id: String,
    server: String,
    authority: String,
    worker: PathBuf,
}

/// Operator-supplied transport material.
///
/// The default enrollment path shells out to the OpenSSL CLI to create a
/// P-256 key and PKCS#10 request. A Windows host has no such binary, so the
/// bootstrap generates an equivalent P-256 key and PKCS#10 request with the
/// platform crypto provider and hands the PEM files to the agent instead. The
/// TLS identity, the CSR contents and every server-side check are unchanged:
/// the control plane still signs the request and the endpoint still proves
/// possession of the matching private key in the mTLS handshake.
pub struct SuppliedTransport {
    pub key: PathBuf,
    pub csr: PathBuf,
}

pub fn supplied_transport(
    key: Option<PathBuf>,
    csr: Option<PathBuf>,
) -> Result<Option<SuppliedTransport>> {
    match (key, csr) {
        (None, None) => Ok(None),
        (Some(key), Some(csr)) => Ok(Some(SuppliedTransport { key, csr })),
        _ => Err(AgentError::rejected(
            "INCOMPLETE_TRANSPORT_MATERIAL",
            "--transport-key and --csr must be supplied together",
        )),
    }
}

fn failure(detail: impl ToString) -> AgentError {
    AgentError::rejected("REMOTE_TRANSPORT", detail.to_string())
}

/// Install operator-supplied PEM material into the state directory, refusing
/// anything that is not a PEM private key plus a PEM PKCS#10 request. A key
/// that does not match the request is rejected by the mTLS handshake, so no
/// verification is skipped here.
fn install_supplied_transport(root: &Path, key_path: &Path, csr_path: &Path) -> Result<Vec<u8>> {
    let key = fs::read(key_path)?;
    let csr = fs::read(csr_path)?;
    let key_is_pem = key.starts_with(b"-----BEGIN ") && contains(&key, b"PRIVATE KEY-----");
    let csr_is_pem = csr.starts_with(b"-----BEGIN CERTIFICATE REQUEST-----");
    if !key_is_pem || !csr_is_pem {
        return Err(AgentError::rejected(
            "INVALID_TRANSPORT_MATERIAL",
            "supplied transport key must be a PEM private key and the CSR a PEM PKCS#10 request",
        ));
    }
    let destination = root.join("transport.key");
    fs::write(&destination, &key)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&destination, fs::Permissions::from_mode(0o600))?;
    }
    fs::write(root.join("transport.csr"), &csr)?;
    Ok(csr)
}

fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    haystack
        .windows(needle.len())
        .any(|window| window == needle)
}

async fn channel(server: &str, root: &Path, mutual: bool) -> Result<Channel> {
    if !server.starts_with("https://") {
        return Err(failure("TLS is required"));
    }
    let mut tls = ClientTlsConfig::new()
        .ca_certificate(Certificate::from_pem(fs::read(root.join("remote-ca.pem"))?));
    if mutual {
        tls = tls.identity(Identity::from_pem(
            fs::read(root.join("remote-cert.pem"))?,
            fs::read(root.join("transport.key"))?,
        ));
    }
    Channel::from_shared(server.to_owned())
        .map_err(failure)?
        .tls_config(tls)
        .map_err(failure)?
        .connect_timeout(Duration::from_secs(10))
        .connect()
        .await
        .map_err(failure)
}

pub async fn enroll(
    root: &Path,
    enrollment_server: &str,
    server: &str,
    ca: &Path,
    token_file: &Path,
    worker: &Path,
    supplied: Option<SuppliedTransport>,
) -> Result<Value> {
    if !cfg!(any(target_os = "linux", windows)) {
        return Err(failure("Unsupported endpoint platform"));
    }
    let state = AgentState::load(root)?;
    if root.join("remote.json").exists() {
        return Err(failure("Endpoint already enrolled"));
    }
    fs::copy(ca, root.join("remote-ca.pem"))?;
    let key = root.join("transport.key");
    if key.exists() {
        return Err(failure(
            "Transport key already exists; preserve it and inspect incomplete enrollment",
        ));
    }
    let csr = match supplied {
        Some(material) => install_supplied_transport(root, &material.key, &material.csr)?,
        None => generate_transport_csr(root, &key)?,
    };
    let mut proof = b"JOCKY:enroll:v1\n".to_vec();
    proof.extend(&csr);
    let signed = state.sign_identity(&proof)?;
    let mut client = AgentControlClient::new(channel(enrollment_server, root, false).await?);
    let response = client
        .enroll(wire::EnrollmentRequest {
            schema_version: "1.0.0".into(),
            one_time_token: fs::read_to_string(token_file)?.trim().to_owned(),
            certificate_signing_request_pem: csr,
            agent_version: env!("CARGO_PKG_VERSION").into(),
            target_os: std::env::consts::OS.into(),
            target_arch: std::env::consts::ARCH.into(),
            simulation: Some(false),
            hostname: std::env::var("COMPUTERNAME")
                .or_else(|_| fs::read_to_string("/etc/hostname"))
                .unwrap_or_else(|_| "jocky-agent".into())
                .trim()
                .to_owned(),
            execution_modes: vec!["memory".into(), "native".into()],
            evidence_public_key: STANDARD
                .decode(&state.config.identity_public_key_base64)
                .map_err(|_| AgentError::Crypto)?,
            evidence_key_proof: STANDARD
                .decode(signed.value_base64)
                .map_err(|_| AgentError::Crypto)?,
        })
        .await
        .map_err(failure)?
        .into_inner();
    fs::write(root.join("remote-cert.pem"), response.certificate_chain_pem)?;
    // Keep the operator-provided trust root; enrollment cannot silently replace it.
    let binding = Binding {
        endpoint_id: response.endpoint_id.clone(),
        organization_id: response.organization_id,
        server: server.into(),
        authority: STANDARD.encode(response.job_authority_public_key),
        worker: worker.into(),
    };
    fs::write(
        root.join("remote.json"),
        serde_json::to_vec_pretty(&binding)?,
    )?;
    // Compiler-artifact execution needs the LLVM worker, which some endpoint
    // platforms legitimately cannot build. Enrollment records whether it is
    // present instead of refusing to connect; job admission enforces it.
    Ok(json!({
        "endpoint_id": response.endpoint_id,
        "remote_transport_configured": true,
        "execution_worker_available": worker.is_file(),
        "simulation": false
    }))
}

/// Default Linux path: the OpenSSL CLI creates a P-256 key and PKCS#10 request.
fn generate_transport_csr(root: &Path, key: &Path) -> Result<Vec<u8>> {
    let status = Command::new("openssl")
        .args([
            "req",
            "-new",
            "-newkey",
            "ec",
            "-pkeyopt",
            "ec_paramgen_curve:P-256",
            "-nodes",
            "-subj",
            "/CN=jocky-agent",
        ])
        .arg("-keyout")
        .arg(key)
        .arg("-out")
        .arg(root.join("transport.csr"))
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map_err(|_| {
            failure("OpenSSL is unavailable; supply --transport-key and --csr instead")
        })?;
    if !status.success() {
        return Err(failure("ECDSA CSR generation failed"));
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(key, fs::Permissions::from_mode(0o600))?;
    }
    Ok(fs::read(root.join("transport.csr"))?)
}

fn verify(state: &AgentState, binding: &Binding, value: &Value, domain: &str) -> Result<()> {
    if value["schema_version"] != "1.0.0"
        || value["simulation"] != false
        || !value["simulation_label"].is_null()
        || value["endpoint_id"] != binding.endpoint_id
        || value["organization_id"] != binding.organization_id
    {
        return Err(failure("Signed message audience or provenance mismatch"));
    }
    let mut config = state.config.clone();
    config.trusted_job_authorities.clear();
    config
        .trusted_job_authorities
        .insert("control-plane".into(), binding.authority.clone());
    let verifier = AgentState {
        root: state.root.clone(),
        config,
    };
    if value["signature"]["status"] != "SIGNED" || value["signature"]["algorithm"] != "Ed25519" {
        return Err(failure("Ed25519 signature required"));
    }
    verifier.verify_job_signature(
        value["signature"]["key_id"].as_str().unwrap_or(""),
        &domain_bytes(domain, value, "signature")?,
        value["signature"]["value_base64"].as_str().unwrap_or(""),
    )?;
    let expires = DateTime::parse_from_rfc3339(value["expires_at"].as_str().unwrap_or(""))
        .map_err(failure)?;
    let issued =
        DateTime::parse_from_rfc3339(value["issued_at"].as_str().unwrap_or("")).map_err(failure)?;
    if expires <= Utc::now()
        || expires <= issued
        || issued > Utc::now() + chrono::Duration::minutes(5)
    {
        return Err(failure("Signed message expired or clock invalid"));
    }
    Ok(())
}

fn admit(state: &AgentState, binding: &Binding, job: &Value) -> Result<()> {
    verify(state, binding, job, "JOCKY:job:v1\n")?;
    require_worker(binding)?;
    if job["enforcement_mode"] != "MONITORED" {
        return Err(failure("Strict budget enforcement unavailable"));
    }
    crate::policy::validate_budget(&budget(job)?, &state.config.max_budget)?;
    let capabilities = job["required_capabilities"]
        .as_array()
        .ok_or_else(|| failure("Missing capabilities"))?;
    if capabilities
        .iter()
        .any(|c| !state.config.capabilities.contains(c.as_str().unwrap_or("")))
    {
        return Err(failure("Capability denied"));
    }
    let manifest = &job["build_manifest"];
    let triple = manifest["target_triple"].as_str().unwrap_or("");
    if !triple.starts_with(std::env::consts::ARCH)
        || !triple.contains(std::env::consts::OS)
        || manifest["artifact_hash"] != job["artifact_hash"]
        || manifest["source_hash"] != job["source_hash"]
        || manifest["jir_hash"] != job["jir_hash"]
        || manifest["execution_mode"] != job["execution_mode"]
    {
        return Err(failure("Compiler build provenance mismatch"));
    }
    if !matches!(
        (
            job["execution_mode"].as_str(),
            manifest["artifact_format"].as_str()
        ),
        (Some("memory"), Some("llvm-object" | "llvm-ir")) | (Some("native"), Some("native-worker"))
    ) {
        return Err(failure("Unsupported execution artifact format"));
    }
    for field in ["job_id", "case_id", "variant_id"] {
        uuid::Uuid::parse_str(job[field].as_str().unwrap_or("")).map_err(failure)?;
    }
    let nonce = job["nonce"].as_str().unwrap_or("");
    if nonce.len() != 64 || hex::decode(nonce).is_err() {
        return Err(failure("Invalid nonce"));
    }
    Ok(())
}

/// Compiler-artifact execution needs the LLVM worker. Some endpoint platforms
/// genuinely cannot build it, and a missing worker must not stop the endpoint
/// from enrolling and heartbeating, so it is enforced when a job is admitted
/// rather than when the endpoint connects.
fn require_worker(binding: &Binding) -> Result<()> {
    if binding.worker.is_file() {
        Ok(())
    } else {
        Err(failure("LLVM execution worker is unavailable"))
    }
}

fn frame(endpoint: &str, body: agent_frame::Body) -> wire::AgentFrame {
    wire::AgentFrame {
        schema_version: "1.0.0".into(),
        endpoint_id: endpoint.into(),
        sequence: 0,
        simulation: Some(false),
        body: Some(body),
    }
}
fn progress(endpoint: &str, job: &str, state: &str, detail: &str) -> wire::AgentFrame {
    frame(endpoint,agent_frame::Body::JobProgress(wire::CanonicalDocument { json_utf8:serde_json::to_vec(&json!({
        "schema_version":"1.0.0","job_id":job,"state":state,"detail":detail,"measurements":{}
    })).expect("fixed progress document") }))
}

fn queue_terminal(
    spool: &mut Spool,
    endpoint: &str,
    job: &str,
    state: &str,
    detail: &str,
) -> Result<()> {
    spool.queue_remote(&mut [progress(endpoint, job, state, detail)], Some(job))
}
fn documents(endpoint: &str, values: Vec<Value>) -> Result<Vec<wire::AgentFrame>> {
    values
        .into_iter()
        .map(|value| {
            let document = wire::CanonicalDocument {
                json_utf8: serde_jcs::to_vec(&value["document"]).map_err(|_| AgentError::Crypto)?,
            };
            let body = match value["kind"].as_str() {
                Some("observation") => agent_frame::Body::Observation(document),
                Some("artifact") => agent_frame::Body::Artifact(document),
                Some("manifest") => agent_frame::Body::EvidenceManifest(document),
                Some("progress") => agent_frame::Body::JobProgress(document),
                _ => return Err(failure("Unknown worker output")),
            };
            Ok(frame(endpoint, body))
        })
        .collect()
}

pub async fn connect(root: &Path) -> Result<()> {
    let lock = fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(root.join("remote.lock"))?;
    lock.try_lock_exclusive()
        .map_err(|_| failure("Remote supervisor already running"))?;
    let binding: Binding = serde_json::from_slice(&fs::read(root.join("remote.json"))?)?;
    let state = AgentState::load(root)?;
    let mut spool = Spool::open(root)?;
    for job in spool.interrupted_remote_jobs()? {
        spool.queue_remote(
            &mut [progress(
                &binding.endpoint_id,
                &job,
                "FAILED",
                "Agent restarted during execution; no automatic re-execution",
            )],
            Some(&job),
        )?;
    }
    let (finished_tx, mut finished_rx) = mpsc::channel::<(String, Result<Vec<Value>>)>(1);
    let mut active: Option<(String, Arc<AtomicBool>)> = None;
    loop {
        let connection = channel(&binding.server, root, true).await;
        let channel = match connection {
            Ok(value) => value,
            Err(_) => {
                tokio::time::sleep(Duration::from_secs(2)).await;
                continue;
            }
        };
        let mut client = AgentControlClient::new(channel);
        let (sender, receiver) = mpsc::channel(32);
        let mut last_sent = 0;
        let mut heartbeat_at = std::time::Instant::now() - Duration::from_secs(30);
        // This opening heartbeat is sent before the exchange starts, and the
        // control plane only answers once it has accepted a frame. Opening the
        // stream with nothing to send therefore deadlocks rather than merely
        // delaying liveness, so the endpoint always queues this frame first.
        // It is also the oldest frame the spool can hold across a restart,
        // which is why an unacknowledged heartbeat must stay replayable.
        spool.queue_remote(
            &mut [frame(
                &binding.endpoint_id,
                agent_frame::Body::Heartbeat(wire::Heartbeat {
                    timestamp: Utc::now().to_rfc3339(),
                    state: if active.is_some() { "BUSY" } else { "IDLE" }.into(),
                    cpu_percent: None,
                    memory_bytes: None,
                    active_job_id: active
                        .as_ref()
                        .map_or_else(String::new, |value| value.0.clone()),
                }),
            )],
            None,
        )?;
        for record in spool
            .pending()?
            .into_iter()
            .filter(|record| record.kind == "remote")
            .take(32)
        {
            let pending = wire::AgentFrame::decode(record.payload.as_slice()).map_err(failure)?;
            last_sent = pending.sequence;
            if sender.send(pending).await.is_err() {
                break;
            }
        }
        let response = client.exchange(ReceiverStream::new(receiver)).await;
        let mut stream = match response {
            Ok(value) => value.into_inner(),
            Err(_) => {
                tokio::time::sleep(Duration::from_secs(2)).await;
                continue;
            }
        };
        let mut tick = tokio::time::interval(Duration::from_secs(2));
        loop {
            // Only a bounded window of encrypted frames is sent; durable ACKs
            // remove exact bytes. A new stream replays unacknowledged sequences.
            for record in spool
                .pending()?
                .into_iter()
                .filter(|r| r.kind == "remote")
                .take(32)
            {
                let frame = wire::AgentFrame::decode(record.payload.as_slice()).map_err(failure)?;
                if frame.sequence > last_sent {
                    last_sent = frame.sequence;
                    if sender.send(frame).await.is_err() {
                        break;
                    }
                }
            }
            tokio::select! {
                _ = tick.tick() => {
                    if heartbeat_at.elapsed() >= Duration::from_secs(15) {
                        spool.queue_remote(&mut [frame(&binding.endpoint_id,agent_frame::Body::Heartbeat(wire::Heartbeat {
                            timestamp:Utc::now().to_rfc3339(),state:if active.is_some(){"BUSY"}else{"IDLE"}.into(),cpu_percent:None,memory_bytes:None,
                            active_job_id:active.as_ref().map_or_else(String::new,|v|v.0.clone()),
                        }))],None)?;
                        heartbeat_at=std::time::Instant::now();
                    }
                }
                Some((job,result)) = finished_rx.recv() => {
                    let cancelled = active.as_ref().is_some_and(|v|v.1.load(Ordering::Relaxed));
                    let mut frames = match result {
                        Ok(values) if !cancelled => match documents(&binding.endpoint_id, values) {
                            Ok(frames) => frames,
                            Err(error) => vec![progress(
                                &binding.endpoint_id,
                                &job,
                                "FAILED",
                                &format!("Worker output rejected: {error}"),
                            )],
                        },
                        _ => vec![progress(&binding.endpoint_id,&job,if cancelled{"CANCELLED"}else{"FAILED"},"Compiler worker stopped; inspect agent limitations")],
                    };
                    spool.queue_remote(&mut frames,Some(&job))?;
                    active=None;
                }
                received = stream.message() => {
                    let message = match received { Ok(Some(message))=>message,_=>break };
                    if message.schema_version != "1.0.0" { return Err(failure("Unsupported control frame schema")); }
                    match message.body {
                        Some(control_frame::Body::Acknowledgement(ack)) => { spool.acknowledge(&format!("remote-{:020}",ack.accepted_sequence))?; }
                        Some(control_frame::Body::SignedCancellation(document)) => {
                            let cancellation:Value = serde_json::from_slice(&document.json_utf8)?;
                            verify(&state,&binding,&cancellation,"JOCKY:cancel:v1\n")?;
                            if let Some((id,cancelled)) = &active {
                                if cancellation["job_id"]==*id {
                                    cancelled.store(true,Ordering::Relaxed);
                                }
                            } else if let Some(id) = cancellation["job_id"].as_str() {
                                if uuid::Uuid::parse_str(id).is_ok() && !spool.remote_job_done(id)? {
                                    queue_terminal(&mut spool, &binding.endpoint_id, id, "CANCELLED", "Cancellation acknowledged before execution")?;
                                }
                            }
                        }
                        Some(control_frame::Body::SignedJob(document)) => {
                            let job: Value = serde_json::from_slice(&document.json_utf8)?;
                            let id = job["job_id"].as_str().ok_or_else(||failure("Missing job ID"))?.to_owned();
                            if let Err(error) = admit(&state,&binding,&job) {
                                queue_terminal(&mut spool, &binding.endpoint_id, &id, "FAILED", &format!("Job admission failed: {error}"))?;
                                continue;
                            }
                            if !spool.claim_remote_job(&id,&hash(&document.json_utf8),job["nonce"].as_str().unwrap_or(""))? { continue; }
                            if active.is_some() {
                                spool.queue_remote(&mut [progress(&binding.endpoint_id,&id,"FAILED","Endpoint concurrency limit reached")],Some(&id))?; continue;
                            }
                            let mut bytes = Vec::new();
                            let artifact = async {
                                let mut chunks = client
                                    .fetch_job_artifact(wire::JobArtifactRequest { job_id: id.clone() })
                                    .await
                                    .map_err(failure)?
                                    .into_inner();
                                while let Some(chunk) = chunks.message().await.map_err(failure)? {
                                    if chunk.offset != bytes.len() as u64
                                        || chunk.size_bytes > 64_000_000
                                        || chunk.content_hash != job["artifact_hash"].as_str().unwrap_or("")
                                    {
                                        return Err(failure("Artifact stream provenance mismatch"));
                                    }
                                    bytes.extend(chunk.content);
                                    if bytes.len() > 64_000_000 {
                                        return Err(failure("Artifact size limit"));
                                    }
                                }
                                if hash(&bytes) != job["artifact_hash"].as_str().unwrap_or("") {
                                    return Err(failure("Artifact SHA-256 mismatch"));
                                }
                                Ok::<(), AgentError>(())
                            }
                            .await;
                            if let Err(error) = artifact {
                                queue_terminal(&mut spool, &binding.endpoint_id, &id, "FAILED", &format!("Artifact retrieval failed: {error}"))?;
                                continue;
                            }
                            let artifact=root.join(format!("build-{id}")); fs::write(&artifact,bytes)?;
                            #[cfg(unix)] { use std::os::unix::fs::PermissionsExt; fs::set_permissions(&artifact,fs::Permissions::from_mode(0o500))?; }
                            spool.queue_remote(&mut [progress(&binding.endpoint_id,&id,"RUNNING","Compiler artifact verified; dedicated worker acknowledged")],None)?;
                            let cancelled=Arc::new(AtomicBool::new(false)); active=Some((id.clone(),cancelled.clone()));
                            let request=crate::remote_worker::Request{state_dir:root.into(),artifact:artifact.clone(),worker:binding.worker.clone(),job};
                            let finished=finished_tx.clone();
                            std::thread::spawn(move || { let result=crate::remote_worker::supervise(request,cancelled); let _=fs::remove_file(artifact); let _=finished.blocking_send((id,result)); });
                        }
                        None=>return Err(failure("Empty control frame")),
                    }
                }
                _ = tokio::signal::ctrl_c() => { if let Some((_,cancelled))=&active{cancelled.store(true,Ordering::Relaxed);} return Ok(()); }
            }
        }
        tokio::time::sleep(Duration::from_secs(2)).await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const KEY: &str = "-----BEGIN PRIVATE KEY-----\nAA\n-----END PRIVATE KEY-----";
    const CSR: &str = "-----BEGIN CERTIFICATE REQUEST-----\nAA\n-----END CERTIFICATE REQUEST-----";

    fn stage(root: &Path, key: &str, csr: &str) -> (PathBuf, PathBuf) {
        let key_path = root.join("staged.key");
        let csr_path = root.join("staged.csr");
        fs::write(&key_path, key).unwrap();
        fs::write(&csr_path, csr).unwrap();
        (key_path, csr_path)
    }

    fn binding(worker: &Path) -> Binding {
        Binding {
            endpoint_id: "endpoint-test".into(),
            organization_id: "org-test".into(),
            server: "https://127.0.0.1:50051".into(),
            authority: "unused".into(),
            worker: worker.to_path_buf(),
        }
    }

    #[test]
    fn supplied_transport_requires_both_halves() {
        assert!(supplied_transport(None, None).unwrap().is_none());
        assert!(supplied_transport(Some("key.pem".into()), None).is_err());
        assert!(supplied_transport(None, Some("csr.pem".into())).is_err());
        assert!(
            supplied_transport(Some("key.pem".into()), Some("csr.pem".into()))
                .unwrap()
                .is_some()
        );
    }

    #[test]
    fn supplied_material_is_installed_or_rejected() {
        let root = tempfile::tempdir().unwrap();
        let (key_path, csr_path) = stage(root.path(), KEY, CSR);
        assert_eq!(
            install_supplied_transport(root.path(), &key_path, &csr_path).unwrap(),
            CSR.as_bytes()
        );
        assert_eq!(
            fs::read(root.path().join("transport.csr")).unwrap(),
            CSR.as_bytes()
        );
        assert_eq!(
            fs::read(root.path().join("transport.key")).unwrap(),
            KEY.as_bytes()
        );
        assert!(
            install_supplied_transport(root.path(), &key_path, &csr_path).is_err(),
            "an existing transport key must never be overwritten"
        );
    }

    #[test]
    fn non_pem_material_is_rejected() {
        let root = tempfile::tempdir().unwrap();
        let (key_path, csr_path) = stage(root.path(), "not a key", CSR);
        assert!(install_supplied_transport(root.path(), &key_path, &csr_path).is_err());
        assert!(!root.path().join("transport.key").exists());

        let (key_path, csr_path) = stage(root.path(), KEY, "not a request");
        assert!(install_supplied_transport(root.path(), &key_path, &csr_path).is_err());
        assert!(!root.path().join("transport.csr").exists());
    }

    #[test]
    fn admission_requires_a_present_execution_worker() {
        let root = tempfile::tempdir().unwrap();
        let missing = root.path().join("jocky-worker");
        let error = require_worker(&binding(&missing)).unwrap_err();
        assert!(
            error.to_string().contains("LLVM execution worker is unavailable"),
            "{error}"
        );
        fs::write(&missing, b"worker").unwrap();
        assert!(require_worker(&binding(&missing)).is_ok());
    }
}
