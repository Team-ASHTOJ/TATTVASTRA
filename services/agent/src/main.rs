use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use chrono::Duration;
use clap::{Parser, Subcommand};
use jocky_agent::collectors::{collect, CollectorContext};
use jocky_agent::error::{AgentError, Result};
use jocky_agent::identity::AgentState;
use jocky_agent::model::{CollectorRequest, ResourceBudget, WorkerRequest, SCHEMA_VERSION};
use jocky_agent::policy::create_local_job;
use jocky_agent::runner::{execute_worker, request_cancellation, run_job};
use jocky_agent::spool::Spool;
use serde_json::{json, Value};

#[derive(Parser)]
#[command(
    name = "jocky-agent",
    version,
    about = "JOCKY endpoint forensic agent and local standalone runner"
)]
struct Cli {
    #[arg(long, global = true, default_value = ".jocky-agent")]
    state_dir: PathBuf,
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Bind this evidence identity to an ECDSA transport identity over TLS.
    Enroll {
        #[arg(long)]
        enrollment_server: String,
        #[arg(long)]
        server: String,
        #[arg(long)]
        ca: PathBuf,
        #[arg(long)]
        token_file: PathBuf,
        #[arg(long, default_value = "/usr/local/bin/jocky-worker")]
        worker: PathBuf,
    },
    /// Connect with mTLS, replay durable frames and execute authorized compiler jobs.
    Connect,
    #[command(name = "__remote-worker", hide = true)]
    __RemoteWorker {
        #[arg(long)]
        request: PathBuf,
    },
    /// Create a stable local endpoint identity and encrypted spool.
    Init {
        #[arg(long, default_value = "local-development")]
        organization_id: String,
    },
    /// Report actual host, policy, collector, runner, and transport status.
    Doctor,
    /// List real collector and optional-adapter availability.
    Collectors,
    /// Run one real collector through a locally signed isolated job.
    Collect {
        collector: String,
        #[arg(long)]
        path: Option<String>,
        #[arg(long)]
        recursive: bool,
        #[arg(long)]
        hash: bool,
        #[arg(long, default_value_t = 1_000)]
        limit: usize,
    },
    /// Create a signed local-development job fixture without contacting a server.
    FixtureJob {
        #[arg(long)]
        output: PathBuf,
        #[arg(
            long,
            value_delimiter = ',',
            default_value = "system,processes,connections"
        )]
        collectors: Vec<String>,
        #[arg(long)]
        path: Option<String>,
        #[arg(long, default_value = "local-case")]
        case_id: String,
        #[arg(long, default_value_t = 300)]
        validity_seconds: i64,
        #[arg(long, default_value_t = 120_000)]
        duration_ms: u64,
        #[arg(long, default_value_t = 32_000_000)]
        max_result_bytes: u64,
    },
    /// Verify and run a signed job fixture in a dedicated child process.
    Run {
        #[arg(long)]
        job: PathBuf,
    },
    /// Emit a local heartbeat snapshot; no server delivery is claimed.
    Heartbeat,
    /// Show durable local agent counters.
    Metrics,
    /// Request cooperative/supervisor cancellation for a local job.
    Cancel { job_id: String },
    /// Inspect or export the encrypted disconnected spool.
    Spool {
        #[command(subcommand)]
        command: SpoolCommand,
    },
    #[command(name = "__worker", hide = true)]
    __Worker {
        #[arg(long)]
        request: PathBuf,
    },
}

#[derive(Subcommand)]
enum SpoolCommand {
    /// List pending encrypted records without decrypting their payload to stdout.
    List,
    /// Export records to an explicit local sink and acknowledge only durable writes.
    FlushLocal {
        #[arg(long)]
        output: PathBuf,
    },
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .json()
        .with_writer(std::io::stderr)
        .with_target(false)
        .init();
    if let Err(error) = execute(Cli::parse()).await {
        let (code, detail) = match error {
            AgentError::Rejected { code, message } => (code, message),
            other => ("AGENT_FAILURE", other.to_string()),
        };
        eprintln!(
            "{}",
            serde_json::to_string(&json!({
                "schema_version": SCHEMA_VERSION,
                "kind": "AgentError",
                "code": code,
                "detail": detail,
                "simulation": false,
            }))
            .unwrap_or_else(|_| "JOCKY agent failure".to_owned())
        );
        std::process::exit(1);
    }
}

async fn execute(cli: Cli) -> Result<()> {
    match cli.command {
        Command::Enroll {
            enrollment_server,
            server,
            ca,
            token_file,
            worker,
        } => print_json(
            &jocky_agent::remote::enroll(
                &cli.state_dir,
                &enrollment_server,
                &server,
                &ca,
                &token_file,
                &worker,
            )
            .await?,
        ),
        Command::Connect => jocky_agent::remote::connect(&cli.state_dir).await,
        Command::__RemoteWorker { request } => {
            print_json(&jocky_agent::remote_worker::run_child(&request)?)
        }
        Command::Init { organization_id } => {
            let state = AgentState::initialize(&cli.state_dir, &organization_id)?;
            let spool = Spool::open(&cli.state_dir)?;
            print_json(&json!({
                "schema_version": SCHEMA_VERSION,
                "kind": "LocalEnrollment",
                "mode": "LOCAL_STANDALONE",
                "endpoint_id": state.config.endpoint_id,
                "organization_id": state.config.organization_id,
                "identity_fingerprint": sha256_text(&state.config.identity_public_key_base64),
                "key_storage": state.config.key_storage,
                "spool_database": spool.database_path(),
                "remote_connectivity": false,
                "simulation": false,
            }))
        }
        Command::Doctor => print_json(&jocky_agent::doctor(&cli.state_dir)),
        Command::Collectors => print_json(&json!({
            "schema_version": SCHEMA_VERSION,
            "kind": "CollectorCatalog",
            "platform": jocky_agent::model::Platform::current(),
            "collectors": jocky_agent::collectors::catalog(),
            "simulation": false,
        })),
        Command::Collect {
            collector,
            path,
            recursive,
            hash,
            limit,
        } => {
            let state = AgentState::load(&cli.state_dir)?;
            let mut spool = Spool::open(&cli.state_dir)?;
            let request = CollectorRequest {
                collector,
                path,
                recursive,
                hash,
                limit,
            };
            let job = create_local_job(
                &state,
                "local-case",
                vec![request],
                ResourceBudget::default(),
                Duration::minutes(5),
            )?;
            let cancelled = cancellation_flag()?;
            print_json(&run_job(&state, &mut spool, &job, cancelled)?)
        }
        Command::FixtureJob {
            output,
            collectors,
            path,
            case_id,
            validity_seconds,
            duration_ms,
            max_result_bytes,
        } => {
            let state = AgentState::load(&cli.state_dir)?;
            let requests = collectors
                .into_iter()
                .map(|collector| CollectorRequest {
                    path: matches!(collector.as_str(), "files" | "file_metadata" | "file_hash")
                        .then(|| path.clone())
                        .flatten(),
                    collector,
                    recursive: false,
                    hash: false,
                    limit: 1_000,
                })
                .collect();
            let budget = ResourceBudget {
                duration_ms,
                max_result_bytes,
                ..ResourceBudget::default()
            };
            let job = create_local_job(
                &state,
                &case_id,
                requests,
                budget,
                Duration::seconds(validity_seconds),
            )?;
            write_new_json(&output, &job)?;
            print_json(&json!({
                "schema_version": SCHEMA_VERSION,
                "kind": "SignedLocalJobFixture",
                "job_id": job.job_id,
                "output": output,
                "expires_at": job.expires_at,
                "simulation": false,
            }))
        }
        Command::Run { job } => {
            let state = AgentState::load(&cli.state_dir)?;
            let mut spool = Spool::open(&cli.state_dir)?;
            let bytes = fs::read(job)?;
            if bytes.len() > 4_000_000 {
                return Err(AgentError::rejected(
                    "JOB_TOO_LARGE",
                    "signed job exceeded 4 MB",
                ));
            }
            let job = serde_json::from_slice(&bytes)?;
            print_json(&run_job(&state, &mut spool, &job, cancellation_flag()?)?)
        }
        Command::Heartbeat => {
            let state = AgentState::load(&cli.state_dir)?;
            let mut context =
                CollectorContext::new(ResourceBudget::default(), &state.config.allowed_roots);
            let system = collect(&CollectorRequest::new("system"), &mut context);
            print_json(&json!({
                "schema_version": SCHEMA_VERSION,
                "kind": "LocalHeartbeat",
                "endpoint_id": state.config.endpoint_id,
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "state": "IDLE",
                "system": system,
                "delivered": false,
                "delivery_reason": "remote transport is not configured",
                "simulation": false,
            }))
        }
        Command::Metrics => {
            let spool = Spool::open(&cli.state_dir)?;
            let counters = spool.metrics()?.into_iter().collect::<BTreeMap<_, _>>();
            print_json(&json!({
                "schema_version": SCHEMA_VERSION,
                "kind": "AgentMetrics",
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "counters": counters,
                "pending_spool_records": spool.pending_count()?,
                "network_bytes": Value::Null,
                "simulation": false,
            }))
        }
        Command::Cancel { job_id } => {
            let state = AgentState::load(&cli.state_dir)?;
            request_cancellation(&state, &job_id)?;
            print_json(&json!({
                "schema_version": SCHEMA_VERSION,
                "kind": "LocalCancellation",
                "job_id": job_id,
                "status": "REQUESTED",
                "remote_signed_cancellation": false,
                "simulation": false,
            }))
        }
        Command::Spool { command } => {
            let spool = Spool::open(&cli.state_dir)?;
            match command {
                SpoolCommand::List => {
                    let records = spool
                        .pending()?
                        .into_iter()
                        .map(|record| {
                            json!({
                                "record_id": record.record_id,
                                "kind": record.kind,
                                "payload_bytes": record.payload.len(),
                            })
                        })
                        .collect::<Vec<_>>();
                    print_json(&json!({
                        "schema_version": SCHEMA_VERSION,
                        "kind": "SpoolStatus",
                        "encrypted_at_rest": true,
                        "records": records,
                        "simulation": false,
                    }))
                }
                SpoolCommand::FlushLocal { output } => {
                    fs::create_dir_all(&output)?;
                    let mut acknowledged = 0;
                    for record in spool.pending()? {
                        let path = output.join(format!("{}.json", record.record_id));
                        durable_write_or_verify(&path, &record.payload)?;
                        if spool.acknowledge(&record.record_id)? {
                            acknowledged += 1;
                        }
                    }
                    print_json(&json!({
                        "schema_version": SCHEMA_VERSION,
                        "kind": "LocalSpoolFlush",
                        "sink": output,
                        "acknowledged": acknowledged,
                        "remaining": spool.pending_count()?,
                        "remote_connectivity": false,
                        "simulation": false,
                    }))
                }
            }
        }
        Command::__Worker { request } => {
            apply_worker_test_fault()?;
            let bytes = fs::read(request)?;
            if bytes.len() > 4_000_000 {
                return Err(AgentError::rejected(
                    "WORKER_REQUEST_TOO_LARGE",
                    "worker request exceeded 4 MB",
                ));
            }
            let request: WorkerRequest = serde_json::from_slice(&bytes)?;
            if request.schema_version != SCHEMA_VERSION {
                return Err(AgentError::rejected(
                    "WORKER_VERSION_MISMATCH",
                    "worker request schema mismatch",
                ));
            }
            print_json(&execute_worker(request))
        }
    }
}

#[cfg(debug_assertions)]
fn apply_worker_test_fault() -> Result<()> {
    let Ok(fault) = std::env::var("JOCKY_AGENT_TEST_WORKER_FAULT") else {
        return Ok(());
    };
    if fault == "crash" {
        return Err(AgentError::rejected(
            "TEST_WORKER_CRASH",
            "debug-only worker crash fault was requested",
        ));
    }
    if let Some(milliseconds) = fault.strip_prefix("delay:") {
        let milliseconds = milliseconds.parse::<u64>().map_err(|_| {
            AgentError::rejected(
                "INVALID_TEST_FAULT",
                "debug worker delay must be an unsigned millisecond value",
            )
        })?;
        std::thread::sleep(std::time::Duration::from_millis(milliseconds.min(5_000)));
        return Ok(());
    }
    Err(AgentError::rejected(
        "INVALID_TEST_FAULT",
        "unknown debug-only worker fault",
    ))
}

#[cfg(not(debug_assertions))]
fn apply_worker_test_fault() -> Result<()> {
    Ok(())
}

fn cancellation_flag() -> Result<Arc<AtomicBool>> {
    let cancelled = Arc::new(AtomicBool::new(false));
    let signal = Arc::clone(&cancelled);
    ctrlc::set_handler(move || signal.store(true, Ordering::Relaxed)).map_err(|error| {
        AgentError::rejected(
            "SIGNAL_HANDLER_UNAVAILABLE",
            format!("cannot install shutdown handler: {error}"),
        )
    })?;
    Ok(cancelled)
}

fn print_json(value: &impl serde::Serialize) -> Result<()> {
    println!("{}", serde_json::to_string_pretty(value)?);
    Ok(())
}

fn write_new_json(path: &Path, value: &impl serde::Serialize) -> Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(&serde_json::to_vec_pretty(value)?)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}

fn durable_write_or_verify(path: &Path, bytes: &[u8]) -> Result<()> {
    match OpenOptions::new().write(true).create_new(true).open(path) {
        Ok(mut file) => {
            file.write_all(bytes)?;
            file.sync_all()?;
            Ok(())
        }
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
            if fs::read(path)? == bytes {
                Ok(())
            } else {
                Err(AgentError::rejected(
                    "SINK_CONFLICT",
                    format!("{} exists with different bytes", path.display()),
                ))
            }
        }
        Err(error) => Err(error.into()),
    }
}

fn sha256_text(value: &str) -> String {
    use sha2::{Digest, Sha256};
    hex::encode(Sha256::digest(value.as_bytes()))
}
