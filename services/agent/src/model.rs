use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const SCHEMA_VERSION: &str = "1.0.0";

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Platform {
    pub os: String,
    pub arch: String,
}

impl Platform {
    pub fn current() -> Self {
        Self {
            os: std::env::consts::OS.to_owned(),
            arch: std::env::consts::ARCH.to_owned(),
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Availability {
    Available,
    Partial,
    Unavailable,
    Denied,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EnforcementStatus {
    Enforced,
    ObservedOnly,
    Unsupported,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EnforcementReport {
    pub timeout: EnforcementStatus,
    pub result_size: EnforcementStatus,
    pub file_count: EnforcementStatus,
    pub file_bytes: EnforcementStatus,
    pub concurrency: EnforcementStatus,
    pub cpu: EnforcementStatus,
    pub memory: EnforcementStatus,
    pub network_bytes: EnforcementStatus,
}

impl EnforcementReport {
    pub fn current() -> Self {
        Self {
            timeout: EnforcementStatus::Enforced,
            result_size: EnforcementStatus::Enforced,
            file_count: EnforcementStatus::Enforced,
            file_bytes: EnforcementStatus::Enforced,
            concurrency: EnforcementStatus::Enforced,
            cpu: if cfg!(target_os = "linux") {
                EnforcementStatus::ObservedOnly
            } else {
                EnforcementStatus::Unsupported
            },
            memory: if cfg!(target_os = "linux") {
                EnforcementStatus::ObservedOnly
            } else {
                EnforcementStatus::Unsupported
            },
            network_bytes: EnforcementStatus::Unsupported,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CollectorDescriptor {
    pub name: String,
    pub capability: String,
    pub availability: Availability,
    pub reason: Option<String>,
    pub platform: Platform,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CollectorRequest {
    pub collector: String,
    #[serde(default)]
    pub path: Option<String>,
    #[serde(default)]
    pub ruleset: Option<String>,
    #[serde(default)]
    pub recursive: bool,
    #[serde(default)]
    pub hash: bool,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

const fn default_limit() -> usize {
    1_000
}

impl CollectorRequest {
    pub fn new(collector: impl Into<String>) -> Self {
        Self {
            collector: collector.into(),
            path: None,
            ruleset: None,
            recursive: false,
            hash: false,
            limit: default_limit(),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CollectorIssue {
    pub code: String,
    pub message: String,
    pub path: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CollectorOutput {
    pub collector: String,
    pub availability: Availability,
    pub records: Vec<Value>,
    pub issues: Vec<CollectorIssue>,
    pub files_examined: u64,
    pub bytes_read: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Value>,
}

impl CollectorOutput {
    pub fn unavailable(collector: &str, code: &str, message: impl Into<String>) -> Self {
        Self {
            collector: collector.to_owned(),
            availability: Availability::Unavailable,
            records: Vec::new(),
            issues: vec![CollectorIssue {
                code: code.to_owned(),
                message: message.into(),
                path: None,
            }],
            files_examined: 0,
            bytes_read: 0,
            metadata: None,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ResourceBudget {
    pub cpu_percent: u8,
    pub memory_bytes: u64,
    pub io_bytes: u64,
    pub duration_ms: u64,
    pub max_result_bytes: u64,
    pub max_file_count: u64,
    pub max_file_bytes: u64,
}

impl Default for ResourceBudget {
    fn default() -> Self {
        Self {
            cpu_percent: 20,
            memory_bytes: 256_000_000,
            io_bytes: 150_000_000,
            duration_ms: 120_000,
            max_result_bytes: 32_000_000,
            max_file_count: 10_000,
            max_file_bytes: 150_000_000,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EnforcementPolicy {
    Strict,
    Monitored,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct JobSignature {
    pub status: String,
    pub algorithm: String,
    pub key_id: String,
    pub value_base64: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SignedJob {
    pub schema_version: String,
    pub simulation: bool,
    pub simulation_label: Option<String>,
    pub job_id: String,
    pub case_id: String,
    pub organization_id: String,
    pub endpoint_id: String,
    pub required_capabilities: Vec<String>,
    pub collectors: Vec<CollectorRequest>,
    pub budget: ResourceBudget,
    pub enforcement_policy: EnforcementPolicy,
    pub nonce: String,
    pub issued_at: String,
    pub expires_at: String,
    pub signature: JobSignature,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Observation {
    pub schema_version: String,
    pub observation_id: String,
    pub endpoint_id: String,
    pub job_id: String,
    pub case_id: String,
    pub collector: String,
    pub observed_at: String,
    pub source_time: Option<String>,
    pub platform: Platform,
    pub data: BTreeMap<String, Value>,
    pub integrity_hash: String,
    pub simulation: bool,
    pub simulation_label: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceManifest {
    pub schema_version: String,
    pub endpoint_id: String,
    pub job_id: String,
    pub case_id: String,
    pub agent_identity: String,
    pub started_at: String,
    pub completed_at: String,
    pub observation_hashes: Vec<String>,
    pub simulation: bool,
    pub simulation_label: Option<String>,
    pub signature: JobSignature,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeMetrics {
    pub duration_ms: u64,
    pub peak_memory_bytes: Option<u64>,
    pub child_cpu_ms: Option<u64>,
    pub bytes_read: u64,
    pub result_bytes: u64,
    pub network_bytes: Option<u64>,
    pub files_examined: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerRequest {
    pub schema_version: String,
    pub requests: Vec<CollectorRequest>,
    pub budget: ResourceBudget,
    pub allowed_roots: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerResponse {
    pub schema_version: String,
    pub outputs: Vec<CollectorOutput>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct JobResult {
    pub schema_version: String,
    pub status: String,
    pub duplicate_receipt: Option<String>,
    pub collector_outputs: Vec<CollectorOutput>,
    pub observations: Vec<Observation>,
    pub manifest: Option<EvidenceManifest>,
    pub metrics: RuntimeMetrics,
    pub enforcement: EnforcementReport,
    pub spooled_records: usize,
}
