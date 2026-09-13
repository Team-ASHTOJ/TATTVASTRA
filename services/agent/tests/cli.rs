use std::fs;
use std::path::Path;
use std::process::{Command, Output};

use serde_json::Value;

fn agent(state: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_jocky-agent"))
        .arg("--state-dir")
        .arg(state)
        .args(arguments)
        .output()
        .expect("agent process should start")
}

fn initialize(state: &Path) {
    let result = agent(state, &["init", "--organization-id", "test-org"]);
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
}

fn fixture(state: &Path, path: &Path, extra: &[&str]) {
    let mut arguments = vec!["fixture-job", "--output", path.to_str().unwrap()];
    arguments.extend_from_slice(extra);
    let result = agent(state, &arguments);
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
}

fn json(output: &Output) -> Value {
    serde_json::from_slice(&output.stdout).expect("stdout should contain one JSON document")
}

#[test]
fn signed_job_runs_once_and_replay_is_idempotent() {
    let temp = tempfile::tempdir().unwrap();
    let state = temp.path().join("state");
    let job = temp.path().join("job.json");
    initialize(&state);
    fixture(&state, &job, &["--collectors", "system"]);

    let first = agent(&state, &["run", "--job", job.to_str().unwrap()]);
    assert!(
        first.status.success(),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    let first = json(&first);
    assert_eq!(first["status"], "SUCCESS");
    assert_eq!(first["observations"][0]["simulation"], false);

    let replay = agent(&state, &["run", "--job", job.to_str().unwrap()]);
    assert!(replay.status.success());
    let replay = json(&replay);
    assert_eq!(replay["status"], "DUPLICATE");
    assert!(replay["duplicate_receipt"].as_str().is_some());
}

#[test]
fn expired_and_malformed_jobs_are_rejected() {
    let temp = tempfile::tempdir().unwrap();
    let state = temp.path().join("state");
    let expired = temp.path().join("expired.json");
    initialize(&state);
    fixture(
        &state,
        &expired,
        &["--validity-seconds=-1", "--collectors", "system"],
    );

    let result = agent(&state, &["run", "--job", expired.to_str().unwrap()]);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("JOB_EXPIRED"));

    let malformed = temp.path().join("malformed.json");
    fs::write(&malformed, b"{\"schema_version\":").unwrap();
    let result = agent(&state, &["run", "--job", malformed.to_str().unwrap()]);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("AGENT_FAILURE"));
}

#[test]
fn supervisor_enforces_timeout_and_reports_worker_crash() {
    let temp = tempfile::tempdir().unwrap();
    let state = temp.path().join("state");
    initialize(&state);

    let timeout_job = temp.path().join("timeout.json");
    fixture(
        &state,
        &timeout_job,
        &["--duration-ms", "5", "--collectors", "system"],
    );
    let timeout = Command::new(env!("CARGO_BIN_EXE_jocky-agent"))
        .arg("--state-dir")
        .arg(&state)
        .args(["run", "--job", timeout_job.to_str().unwrap()])
        .env("JOCKY_AGENT_TEST_WORKER_FAULT", "delay:200")
        .output()
        .unwrap();
    assert!(!timeout.status.success());
    assert!(String::from_utf8_lossy(&timeout.stderr).contains("TIMEOUT"));

    let crash_job = temp.path().join("crash.json");
    fixture(&state, &crash_job, &["--collectors", "system"]);
    let crash = Command::new(env!("CARGO_BIN_EXE_jocky-agent"))
        .arg("--state-dir")
        .arg(&state)
        .args(["run", "--job", crash_job.to_str().unwrap()])
        .env("JOCKY_AGENT_TEST_WORKER_FAULT", "crash")
        .output()
        .unwrap();
    assert!(!crash.status.success());
    assert!(String::from_utf8_lossy(&crash.stderr).contains("RUNNER_CRASH"));

    let size_job = temp.path().join("size.json");
    fixture(
        &state,
        &size_job,
        &["--max-result-bytes", "128", "--collectors", "system"],
    );
    let size = agent(&state, &["run", "--job", size_job.to_str().unwrap()]);
    assert!(!size.status.success());
    assert!(String::from_utf8_lossy(&size.stderr).contains("RESULT_SIZE_EXCEEDED"));
}

#[test]
fn cancellation_marker_stops_an_authorized_job_before_collection() {
    let temp = tempfile::tempdir().unwrap();
    let state = temp.path().join("state");
    let job = temp.path().join("job.json");
    initialize(&state);
    fixture(&state, &job, &["--collectors", "system"]);
    let document: Value = serde_json::from_slice(&fs::read(&job).unwrap()).unwrap();
    let job_id = document["job_id"].as_str().unwrap();

    assert!(agent(&state, &["cancel", job_id]).status.success());
    let result = agent(&state, &["run", "--job", job.to_str().unwrap()]);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("CANCELLED"));
}

#[test]
fn encrypted_spool_survives_process_reconnect_and_flushes_durably() {
    let temp = tempfile::tempdir().unwrap();
    let state = temp.path().join("state");
    let sink = temp.path().join("sink");
    let job = temp.path().join("job.json");
    initialize(&state);
    fixture(&state, &job, &["--collectors", "system"]);
    assert!(agent(&state, &["run", "--job", job.to_str().unwrap()])
        .status
        .success());

    let pending = json(&agent(&state, &["spool", "list"]));
    assert!(pending["records"].as_array().unwrap().len() >= 2);
    let flushed = agent(
        &state,
        &["spool", "flush-local", "--output", sink.to_str().unwrap()],
    );
    assert!(
        flushed.status.success(),
        "{}",
        String::from_utf8_lossy(&flushed.stderr)
    );
    assert_eq!(json(&flushed)["remaining"], 0);
    assert!(fs::read_dir(sink).unwrap().count() >= 2);
}

#[cfg(target_os = "linux")]
#[test]
fn linux_p0_collectors_return_real_host_observations() {
    let temp = tempfile::tempdir().unwrap();
    let state = temp.path().join("state");
    initialize(&state);
    for collector in ["system", "processes", "connections"] {
        let result = agent(&state, &["collect", collector, "--limit", "5"]);
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let result = json(&result);
        assert!(matches!(
            result["status"].as_str(),
            Some("SUCCESS" | "PARTIAL")
        ));
        for observation in result["observations"].as_array().unwrap() {
            assert_eq!(observation["simulation"], false);
            assert_eq!(observation["collector"], collector);
            assert_eq!(observation["integrity_hash"].as_str().unwrap().len(), 64);
        }
        if collector != "connections" {
            assert!(!result["observations"].as_array().unwrap().is_empty());
        }
    }
}
