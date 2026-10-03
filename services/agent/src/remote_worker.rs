//! Compiler-generated code executes in an agent-owned child. The fixed C ABI
//! invokes existing collectors over pipes; source/JIR are never interpreted here.
use std::collections::BTreeSet;
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

use base64::{engine::general_purpose::STANDARD, Engine};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::collectors::{collect, required_capability, CollectorContext};
use crate::error::{AgentError, Result};
use crate::evidence::domain_bytes;
use crate::identity::AgentState;
use crate::model::{Availability, CollectorRequest, ResourceBudget};

#[derive(Serialize, Deserialize)]
pub struct Request {
    pub state_dir: PathBuf,
    pub artifact: PathBuf,
    pub worker: PathBuf,
    pub job: Value,
}

pub fn hash(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

pub fn budget(job: &Value) -> Result<ResourceBudget> {
    let mut value = serde_json::to_value(ResourceBudget::default())?;
    for key in ["cpu_percent", "memory_bytes", "io_bytes", "duration_ms"] {
        value[key] = job["budget"][key].clone();
    }
    Ok(serde_json::from_value(value)?)
}

pub fn supervise(request: Request, cancelled: Arc<AtomicBool>) -> Result<Vec<Value>> {
    let directory = tempfile::tempdir_in(&request.state_dir)?;
    let input = directory.path().join("request.json");
    fs::write(&input, serde_json::to_vec(&request)?)?;
    let limits = budget(&request.job)?;
    let mut child = Command::new(std::env::current_exe()?)
        .arg("__remote-worker")
        .arg("--request")
        .arg(input)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| AgentError::rejected("WORKER_PIPE", "Worker pipe missing"))?;
    let max = limits.max_result_bytes;
    let reader = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        stdout.take(max + 1).read_to_end(&mut bytes).map(|_| bytes)
    });
    let start = Instant::now();
    let status = loop {
        if cancelled.load(Ordering::Relaxed)
            || start.elapsed().as_millis() > limits.duration_ms as u128
        {
            let _ = child.kill();
            let _ = child.wait();
            return Err(AgentError::rejected(
                if cancelled.load(Ordering::Relaxed) {
                    "CANCELLED"
                } else {
                    "TIMEOUT"
                },
                "Compiler worker stopped by supervisor",
            ));
        }
        if let Some(status) = child.try_wait()? {
            break status;
        }
        std::thread::sleep(Duration::from_millis(20));
    };
    let bytes = reader
        .join()
        .map_err(|_| AgentError::rejected("WORKER_PIPE", "Worker reader failed"))??;
    if !status.success() || bytes.len() as u64 > max {
        return Err(AgentError::rejected(
            "WORKER_FAILED",
            "Compiler worker failed or exceeded result budget",
        ));
    }
    Ok(serde_json::from_slice(&bytes)?)
}

pub fn run_child(path: &Path) -> Result<Vec<Value>> {
    let request: Request = serde_json::from_slice(&fs::read(path)?)?;
    let state = AgentState::load(&request.state_dir)?;
    let job = &request.job;
    if hash(&fs::read(&request.artifact)?) != job["artifact_hash"].as_str().unwrap_or("") {
        return Err(AgentError::rejected(
            "ARTIFACT_HASH",
            "Compiler artifact changed before execution",
        ));
    }
    let mut command = if job["execution_mode"] == "memory" {
        let mut command = Command::new(&request.worker);
        command
            .arg(&request.artifact)
            .arg(job["build_manifest"]["entry_symbol"].as_str().unwrap_or(""));
        command
    } else {
        Command::new(&request.artifact)
    };
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()?;
    let mut input = child
        .stdin
        .take()
        .ok_or_else(|| AgentError::rejected("WORKER_PIPE", "ABI input missing"))?;
    let output = child
        .stdout
        .take()
        .ok_or_else(|| AgentError::rejected("WORKER_PIPE", "ABI output missing"))?;
    let worker_pid = child.id();
    let measured_start = Instant::now();
    let execution_engine = if job["execution_mode"] == "native" {
        "NATIVE_AOT"
    } else if job["build_manifest"]["artifact_format"] == "llvm-ir" {
        "LLVM_ORC_JIT"
    } else {
        "LLVM_ORC_OBJECT"
    };
    let started = Utc::now().to_rfc3339();
    let mut context = CollectorContext::new(budget(job)?, &state.config.allowed_roots);
    let mut frames = Vec::new();
    let mut observations = Vec::new();
    let mut issues = Vec::new();
    let mut handles = BTreeSet::new();
    let mut failed = false;
    for line in BufReader::new(output).lines() {
        let line = line?;
        if line.len() > 262144 {
            let _ = child.kill();
            return Err(AgentError::rejected("ABI_LIMIT", "ABI request too large"));
        }
        let call: Value = serde_json::from_str(&line)?;
        let collector = match call["operation"].as_u64() {
            Some(1) => "system",
            Some(2) => "users",
            Some(3) => "processes",
            Some(4) => "interfaces",
            Some(5) => "connections",
            Some(6) => "routes",
            Some(7) => "file_metadata",
            Some(8) => "file_hash",
            Some(9) => "services",
            Some(10) => "events",
            Some(11) => "drivers",
            Some(12) => "yara",
            _ => "",
        };
        let capability = required_capability(collector).unwrap_or("");
        let mut authorized = state.config.capabilities.contains(capability)
            && job["required_capabilities"]
                .as_array()
                .is_some_and(|items| items.iter().any(|item| item == capability));
        if collector == "yara" {
            authorized &= state.config.capabilities.contains("filesystem.content")
                && job["required_capabilities"]
                    .as_array()
                    .is_some_and(|items| items.iter().any(|item| item == "filesystem.content"));
        }
        let options = &call["config"]["options"];
        // Current REAL bridge supports bounded inventory only. Reject richer
        // operations rather than silently ignoring DSL predicates or options.
        if !authorized || (collector != "yara" && options.as_object().is_some_and(|items| !items.is_empty())) {
            writeln!(input, "2 0")?;
            failed = true;
            break;
        }
        let mut collector_request = CollectorRequest::new(collector);
        if collector == "yara" {
            let map = options.as_object();
            let valid_keys = map.is_some_and(|items| items.keys().all(|key| matches!(key.as_str(), "path" | "ruleset" | "recursive")));
            let path = options["path"]["children"][0]["value"].as_str();
            let ruleset = options["ruleset"]["value"].as_str();
            let recursive = options["recursive"]["value"].as_str();
            let limit = call["config"]["scan_limit"].as_i64();
            if !valid_keys
                || options["path"]["kind"] != "call"
                || options["path"]["value"] != "path"
                || options["path"]["children"][0]["kind"] != "literal"
                || options["ruleset"]["kind"] != "literal"
                || options["ruleset"]["literal_kind"] != "string"
                || (recursive.is_some() && (options["recursive"]["kind"] != "literal" || options["recursive"]["literal_kind"] != "bool"))
                || !path.is_some_and(|value| !value.is_empty())
                || !ruleset.is_some_and(|value| !value.is_empty())
                || (recursive.is_some() && !matches!(recursive, Some("true" | "false")))
                || !limit.is_some_and(|value| (1..=100_000).contains(&value)) {
                writeln!(input, "2 0")?;
                failed = true;
                break;
            }
            collector_request.path = path.map(str::to_owned);
            collector_request.ruleset = ruleset.map(str::to_owned);
            collector_request.recursive = recursive == Some("true");
            collector_request.limit = limit.unwrap_or(0) as usize;
        }
        let output = collect(&collector_request, &mut context);
        failed |= output.availability != Availability::Available;
        issues.push(serde_json::to_value(&output)?);
        for data in &output.records {
            let mut observation = json!({
                "schema_version":"1.0.0", "simulation":false, "simulation_label":null,
                "observation_id":uuid::Uuid::new_v4().to_string(),
                "case_id":job["case_id"], "endpoint_id":job["endpoint_id"], "job_id":job["job_id"],
                "collector_id":collector, "timestamp":Utc::now().to_rfc3339(), "source_time":null,
                "type":collector, "data":data, "variant_id":job["variant_id"],
                "source_hash":job["source_hash"], "jir_hash":job["jir_hash"],
            });
            observation["integrity_hash"] =
                hash(&serde_jcs::to_vec(&observation).map_err(|_| AgentError::Crypto)?).into();
            observations.push(observation["integrity_hash"].clone());
            frames.push(json!({"kind":"observation","document":observation}));
        }
        let handle = call["instruction"].as_u64().unwrap_or(0) + 1;
        handles.insert(handle);
        writeln!(input, "0 {handle}")?;
    }
    drop(input);
    let status = child.wait()?;
    failed |= !status.success();
    let execution_duration_ms = measured_start.elapsed().as_secs_f64() * 1000.0;
    // Store actual collector output/limitations in bounded JSON artifacts. These
    // remain useful evidence even when another collector/endpoint fails.
    let mut artifact_hashes = Vec::new();
    for output in issues {
        let content = serde_jcs::to_vec(&json!({"schema_version":"1.0.0", "simulation":false,
            "simulation_label":null, "job_id":job["job_id"], "output":output}))
        .map_err(|_| AgentError::Crypto)?;
        if content.len() > 590000 {
            return Err(AgentError::rejected(
                "ARTIFACT_LIMIT",
                "Collector artifact exceeds upload limit",
            ));
        }
        let digest = hash(&content);
        artifact_hashes.push(digest.clone());
        frames.push(json!({"kind":"artifact", "document":{
            "schema_version":"1.0.0", "simulation":false, "simulation_label":null,
            "job_id":job["job_id"], "content_hash":digest, "content_base64":STANDARD.encode(content), "media_type":"application/json"
        }}));
    }
    let public = STANDARD
        .decode(&state.config.identity_public_key_base64)
        .map_err(|_| AgentError::Crypto)?;
    let mut manifest = json!({
        "schema_version":"1.0.0", "simulation":false,"simulation_label":null,
        "case_id":job["case_id"], "endpoint_id":job["endpoint_id"], "job_id":job["job_id"],
        "agent_identity":hash(&public), "source_hash":job["source_hash"], "jir_hash":job["jir_hash"],
        "llvm_ir_hash":job["build_manifest"]["llvm_ir_hash"], "variant_id":job["variant_id"],
        "variant_seed":job["build_manifest"]["variant_seed"], "artifact_hash":job["artifact_hash"],
        "execution_mode":job["execution_mode"], "worker_pid":worker_pid,
        "execution_engine":execution_engine,"execution_duration_ms":execution_duration_ms,
        "transport_mode":job["transport_mode"], "started_at":started, "completed_at":Utc::now().to_rfc3339(),
        "observation_hashes":observations,"artifact_hashes":artifact_hashes,
    });
    manifest["signature"] = serde_json::to_value(state.sign_identity(&domain_bytes(
        "JOCKY:manifest:v1\n",
        &manifest,
        "signature",
    )?)?)?;
    frames.push(json!({"kind":"manifest", "document":manifest}));
    frames.push(json!({"kind":"progress", "document":{
        "schema_version":"1.0.0", "job_id":job["job_id"], "state":if failed {"FAILED"} else {"SUCCESS"},
        "detail":if failed {"Collector limitations or worker failure; collected evidence retained"} else {"Compiler artifact execution completed"},
        "measurements":{"worker_pid":worker_pid,"execution_engine":execution_engine,
            "execution_duration_ms":execution_duration_ms,"transport_mode":job["transport_mode"],
            "bytes_read":context.bytes_read,"files_examined":context.files_examined,"enforcement":"MONITORED"}
    }}));
    Ok(frames)
}
