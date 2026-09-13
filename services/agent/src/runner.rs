use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use chrono::Utc;
use fs2::FileExt;

use crate::collectors::{collect, CollectorContext};
use crate::error::{AgentError, Result};
use crate::evidence;
use crate::identity::AgentState;
use crate::model::{
    Availability, EnforcementReport, JobResult, RuntimeMetrics, SignedJob, WorkerRequest,
    WorkerResponse, SCHEMA_VERSION,
};
use crate::policy;
use crate::spool::{NonceOutcome, Spool};

pub fn execute_worker(request: WorkerRequest) -> WorkerResponse {
    let mut context = CollectorContext::new(request.budget, &request.allowed_roots);
    let outputs = request
        .requests
        .iter()
        .map(|request| collect(request, &mut context))
        .collect();
    WorkerResponse {
        schema_version: SCHEMA_VERSION.to_owned(),
        outputs,
    }
}

pub fn run_job(
    state: &AgentState,
    spool: &mut Spool,
    job: &SignedJob,
    cancelled: Arc<AtomicBool>,
) -> Result<JobResult> {
    match policy::admit(state, spool, job)? {
        NonceOutcome::Duplicate(receipt) => {
            return Ok(JobResult {
                schema_version: SCHEMA_VERSION.to_owned(),
                status: "DUPLICATE".to_owned(),
                duplicate_receipt: Some(receipt),
                collector_outputs: Vec::new(),
                observations: Vec::new(),
                manifest: None,
                metrics: RuntimeMetrics::default(),
                enforcement: EnforcementReport::current(),
                spooled_records: spool.pending_count()?,
            });
        }
        NonceOutcome::New(_) => {}
    }
    let started_at = Utc::now().to_rfc3339();
    let (response, metrics) = supervise(state, job, cancelled)?;
    let observed_at = Utc::now().to_rfc3339();
    let mut observations = Vec::new();
    for output in &response.outputs {
        observations.extend(evidence::normalize(job, output, &observed_at)?);
    }
    let manifest = evidence::manifest(state, job, &started_at, &observations)?;
    for observation in &observations {
        spool.enqueue("observation", &serde_json::to_vec(observation)?)?;
    }
    spool.enqueue("evidence_manifest", &serde_json::to_vec(&manifest)?)?;
    spool.increment("completed_jobs", 1)?;
    spool.increment("observations", observations.len() as u64)?;
    spool.increment("bytes_read", metrics.bytes_read)?;
    let partial = response
        .outputs
        .iter()
        .any(|output| output.availability != Availability::Available);
    Ok(JobResult {
        schema_version: SCHEMA_VERSION.to_owned(),
        status: if partial { "PARTIAL" } else { "SUCCESS" }.to_owned(),
        duplicate_receipt: None,
        collector_outputs: response.outputs,
        observations,
        manifest: Some(manifest),
        metrics,
        enforcement: EnforcementReport::current(),
        spooled_records: spool.pending_count()?,
    })
}

pub fn request_cancellation(state: &AgentState, job_id: &str) -> Result<()> {
    validate_id(job_id)?;
    fs::write(state.root.join(format!("cancel-{job_id}")), b"cancelled\n")?;
    Ok(())
}

fn supervise(
    state: &AgentState,
    job: &SignedJob,
    cancelled: Arc<AtomicBool>,
) -> Result<(WorkerResponse, RuntimeMetrics)> {
    let lock_path = state.root.join("runner.lock");
    let lock = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(lock_path)?;
    lock.try_lock_exclusive().map_err(|_| {
        AgentError::rejected(
            "CONCURRENCY_EXCEEDED",
            "another execution worker already owns the agent runner slot",
        )
    })?;

    let worker_request = WorkerRequest {
        schema_version: SCHEMA_VERSION.to_owned(),
        requests: job.collectors.clone(),
        budget: job.budget.clone(),
        allowed_roots: state.config.allowed_roots.clone(),
    };
    let mut request_file = tempfile::Builder::new()
        .prefix("jocky-worker-")
        .suffix(".json")
        .tempfile_in(&state.root)?;
    request_file.write_all(&serde_json::to_vec(&worker_request)?)?;
    request_file.flush()?;

    let executable = std::env::current_exe()?;
    let mut child = Command::new(executable)
        .arg("__worker")
        .arg("--request")
        .arg(request_file.path())
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    let child_id = child.id();
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| AgentError::rejected("RUNNER_PIPE", "runner stdout was unavailable"))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| AgentError::rejected("RUNNER_PIPE", "runner stderr was unavailable"))?;
    let result_limit = job.budget.max_result_bytes.saturating_add(1) as usize;
    let output_reader = thread::spawn(move || read_limited(stdout, result_limit));
    let error_reader = thread::spawn(move || read_limited(stderr, 256 * 1024));
    let started = Instant::now();
    let deadline = Duration::from_millis(job.budget.duration_ms);
    let cancel_path = state.root.join(format!("cancel-{}", job.job_id));
    let mut peak_memory = None;
    let mut child_cpu_ms = None;
    let ticks_per_second = clock_ticks();
    let status = loop {
        if cancelled.load(Ordering::Relaxed) || cancel_path.exists() {
            let _ = child.kill();
            let _ = child.wait();
            let _ = fs::remove_file(&cancel_path);
            return Err(AgentError::rejected(
                "CANCELLED",
                "execution worker was cancelled",
            ));
        }
        if started.elapsed() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            return Err(AgentError::rejected(
                "TIMEOUT",
                "execution worker exceeded its monotonic deadline",
            ));
        }
        let (memory, cpu) = child_usage(child_id, ticks_per_second);
        if let Some(memory) = memory {
            peak_memory = Some(peak_memory.map_or(memory, |peak: u64| peak.max(memory)));
        }
        if cpu.is_some() {
            child_cpu_ms = cpu;
        }
        if let Some(status) = child.try_wait()? {
            break status;
        }
        thread::sleep(Duration::from_millis(20));
    };
    let output = output_reader
        .join()
        .map_err(|_| AgentError::rejected("RUNNER_PIPE", "runner output reader panicked"))??;
    let errors = error_reader
        .join()
        .map_err(|_| AgentError::rejected("RUNNER_PIPE", "runner error reader panicked"))??;
    if output.len() as u64 > job.budget.max_result_bytes {
        return Err(AgentError::rejected(
            "RESULT_SIZE_EXCEEDED",
            "worker output exceeded the result-size budget",
        ));
    }
    if !status.success() {
        return Err(AgentError::rejected(
            "RUNNER_CRASH",
            format!(
                "worker exited with {}; stderr={}",
                status,
                String::from_utf8_lossy(&errors).trim()
            ),
        ));
    }
    let response: WorkerResponse = serde_json::from_slice(&output)?;
    if response.schema_version != SCHEMA_VERSION {
        return Err(AgentError::rejected(
            "RUNNER_VERSION_MISMATCH",
            "worker response schema does not match the supervisor",
        ));
    }
    let metrics = RuntimeMetrics {
        duration_ms: started.elapsed().as_millis() as u64,
        peak_memory_bytes: peak_memory,
        child_cpu_ms,
        bytes_read: response.outputs.iter().map(|item| item.bytes_read).sum(),
        result_bytes: output.len() as u64,
        network_bytes: None,
        files_examined: response
            .outputs
            .iter()
            .map(|item| item.files_examined)
            .sum(),
    };
    Ok((response, metrics))
}

fn read_limited(mut input: impl Read, maximum: usize) -> Result<Vec<u8>> {
    let mut output = Vec::new();
    input
        .by_ref()
        .take(maximum as u64)
        .read_to_end(&mut output)?;
    Ok(output)
}

fn validate_id(value: &str) -> Result<()> {
    if value.is_empty()
        || value.len() > 128
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"_.:-".contains(&byte))
    {
        return Err(AgentError::rejected(
            "INVALID_IDENTIFIER",
            "identifier contains unsupported characters",
        ));
    }
    Ok(())
}

#[cfg(target_os = "linux")]
fn child_usage(pid: u32, ticks_per_second: Option<u64>) -> (Option<u64>, Option<u64>) {
    let memory = fs::read_to_string(format!("/proc/{pid}/status"))
        .ok()
        .and_then(|status| {
            status.lines().find_map(|line| {
                let value = line.strip_prefix("VmRSS:")?.trim();
                value
                    .split_whitespace()
                    .next()?
                    .parse::<u64>()
                    .ok()
                    .map(|kb| kb.saturating_mul(1024))
            })
        });
    let cpu = fs::read_to_string(format!("/proc/{pid}/stat"))
        .ok()
        .and_then(|stat| {
            let fields = stat
                .rsplit_once(')')?
                .1
                .split_whitespace()
                .collect::<Vec<_>>();
            let user = fields.get(11)?.parse::<u64>().ok()?;
            let system = fields.get(12)?.parse::<u64>().ok()?;
            let ticks = user.saturating_add(system);
            Some(ticks.saturating_mul(1_000) / ticks_per_second?)
        });
    (memory, cpu)
}

#[cfg(not(target_os = "linux"))]
fn child_usage(_pid: u32, _ticks_per_second: Option<u64>) -> (Option<u64>, Option<u64>) {
    (None, None)
}

#[cfg(target_os = "linux")]
fn clock_ticks() -> Option<u64> {
    let result = Command::new("getconf").arg("CLK_TCK").output().ok()?;
    if !result.status.success() {
        return None;
    }
    String::from_utf8(result.stdout)
        .ok()?
        .trim()
        .parse::<u64>()
        .ok()
        .filter(|value| *value != 0)
}

#[cfg(not(target_os = "linux"))]
fn clock_ticks() -> Option<u64> {
    None
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::*;

    #[test]
    fn linux_worker_usage_has_real_cpu_and_memory_samples() {
        let ticks = clock_ticks();
        assert!(ticks.is_some());
        let (memory, cpu) = child_usage(std::process::id(), ticks);
        assert!(memory.is_some_and(|value| value > 0));
        assert!(cpu.is_some());
    }
}
