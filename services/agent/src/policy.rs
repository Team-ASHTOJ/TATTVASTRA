use std::collections::BTreeSet;

use chrono::{DateTime, Duration, Utc};
use rand_core::{OsRng, RngCore};

use crate::collectors::required_capability;
use crate::error::{AgentError, Result};
use crate::evidence::domain_bytes;
use crate::identity::AgentState;
use crate::model::{
    CollectorRequest, EnforcementPolicy, EnforcementReport, JobSignature, ResourceBudget,
    SignedJob, SCHEMA_VERSION,
};
use crate::spool::{NonceOutcome, Spool};

pub fn create_local_job(
    state: &AgentState,
    case_id: &str,
    collectors: Vec<CollectorRequest>,
    budget: ResourceBudget,
    validity: Duration,
) -> Result<SignedJob> {
    if collectors.is_empty() {
        return Err(AgentError::rejected(
            "EMPTY_JOB",
            "job must request at least one collector",
        ));
    }
    let now = Utc::now();
    let mut nonce = [0_u8; 32];
    OsRng.fill_bytes(&mut nonce);
    let required_capabilities = capabilities_for(&collectors)?.into_iter().collect();
    let mut job = SignedJob {
        schema_version: SCHEMA_VERSION.to_owned(),
        simulation: false,
        simulation_label: None,
        job_id: format!("job-{}", uuid::Uuid::new_v4().simple()),
        case_id: case_id.to_owned(),
        organization_id: state.config.organization_id.clone(),
        endpoint_id: state.config.endpoint_id.clone(),
        required_capabilities,
        collectors,
        budget,
        enforcement_policy: EnforcementPolicy::Monitored,
        nonce: hex::encode(nonce),
        issued_at: now.to_rfc3339(),
        expires_at: (now + validity).to_rfc3339(),
        signature: JobSignature {
            status: "UNSIGNED".to_owned(),
            algorithm: "Ed25519".to_owned(),
            key_id: "local-dev-authority".to_owned(),
            value_base64: String::new(),
        },
    };
    let bytes = domain_bytes("JOCKY:job:v1\n", &job, "signature")?;
    job.signature = state.sign_local_job(&bytes)?;
    Ok(job)
}

pub fn admit(state: &AgentState, spool: &mut Spool, job: &SignedJob) -> Result<NonceOutcome> {
    if job.schema_version != SCHEMA_VERSION {
        return Err(AgentError::rejected(
            "JOB_VERSION_MISMATCH",
            "unsupported signed-job schema",
        ));
    }
    if job.simulation || job.simulation_label.is_some() {
        return Err(AgentError::rejected(
            "SIMULATION_REJECTED",
            "REAL agent jobs cannot contain simulated provenance",
        ));
    }
    if job.endpoint_id != state.config.endpoint_id
        || job.organization_id != state.config.organization_id
    {
        return Err(AgentError::rejected(
            "JOB_AUDIENCE_MISMATCH",
            "job endpoint or organization does not match this identity",
        ));
    }
    if job.nonce.len() != 64 || hex::decode(&job.nonce).map_or(true, |value| value.len() != 32) {
        return Err(AgentError::rejected(
            "INVALID_NONCE",
            "job nonce must be 256-bit lowercase hexadecimal",
        ));
    }
    let issued = parse_time(&job.issued_at)?;
    let expires = parse_time(&job.expires_at)?;
    let now = Utc::now();
    if expires <= issued || expires <= now {
        return Err(AgentError::rejected("JOB_EXPIRED", "job has expired"));
    }
    if issued > now + Duration::minutes(5) {
        return Err(AgentError::rejected(
            "JOB_NOT_YET_VALID",
            "job issuance is beyond allowed clock skew",
        ));
    }
    if job.signature.status != "SIGNED" || job.signature.algorithm != "Ed25519" {
        return Err(AgentError::rejected(
            "SIGNATURE_REQUIRED",
            "job must carry an Ed25519 signature",
        ));
    }
    let bytes = domain_bytes("JOCKY:job:v1\n", job, "signature")?;
    state.verify_job_signature(&job.signature.key_id, &bytes, &job.signature.value_base64)?;

    let actual = capabilities_for(&job.collectors)?;
    let declared = job
        .required_capabilities
        .iter()
        .cloned()
        .collect::<BTreeSet<_>>();
    if actual != declared {
        return Err(AgentError::rejected(
            "CAPABILITY_ENVELOPE_MISMATCH",
            "declared capabilities do not exactly match collector requirements",
        ));
    }
    if !actual.is_subset(&state.config.capabilities) {
        return Err(AgentError::rejected(
            "CAPABILITY_DENIED",
            "endpoint policy does not grant every requested capability",
        ));
    }
    validate_budget(&job.budget, &state.config.max_budget)?;
    if job.enforcement_policy == EnforcementPolicy::Strict {
        let enforcement = EnforcementReport::current();
        if enforcement.cpu != crate::model::EnforcementStatus::Enforced
            || enforcement.memory != crate::model::EnforcementStatus::Enforced
        {
            return Err(AgentError::rejected(
                "STRICT_BUDGET_UNENFORCEABLE",
                "CPU and memory are observed-only on this agent build",
            ));
        }
    }
    spool.consume_nonce(&job.nonce, &job.job_id, &job.expires_at)
}

fn capabilities_for(collectors: &[CollectorRequest]) -> Result<BTreeSet<String>> {
    let mut capabilities = BTreeSet::new();
    for request in collectors {
        let capability = required_capability(&request.collector).ok_or_else(|| {
            AgentError::rejected(
                "UNKNOWN_COLLECTOR",
                format!(
                    "collector `{}` is not in the fixed registry",
                    request.collector
                ),
            )
        })?;
        capabilities.insert(capability.to_owned());
        if request.hash && request.collector == "processes" {
            capabilities.insert("filesystem.content".to_owned());
        }
        if request.limit == 0 || request.limit > 100_000 {
            return Err(AgentError::rejected(
                "INVALID_COLLECTOR_LIMIT",
                "collector limit must be between 1 and 100000",
            ));
        }
    }
    Ok(capabilities)
}

fn validate_budget(requested: &ResourceBudget, maximum: &ResourceBudget) -> Result<()> {
    let invalid = requested.cpu_percent == 0
        || requested.cpu_percent > maximum.cpu_percent
        || requested.memory_bytes == 0
        || requested.memory_bytes > maximum.memory_bytes
        || requested.io_bytes > maximum.io_bytes
        || requested.duration_ms == 0
        || requested.duration_ms > maximum.duration_ms
        || requested.max_result_bytes == 0
        || requested.max_result_bytes > maximum.max_result_bytes
        || requested.max_file_count == 0
        || requested.max_file_count > maximum.max_file_count
        || requested.max_file_bytes > maximum.max_file_bytes;
    if invalid {
        return Err(AgentError::rejected(
            "BUDGET_DENIED",
            "job budget is invalid or exceeds endpoint policy",
        ));
    }
    Ok(())
}

fn parse_time(value: &str) -> Result<DateTime<Utc>> {
    DateTime::parse_from_rfc3339(value)
        .map(|value| value.with_timezone(&Utc))
        .map_err(|_| AgentError::rejected("INVALID_TIME", "job time is not RFC 3339"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> (tempfile::TempDir, AgentState, Spool) {
        let temp = tempfile::tempdir().unwrap();
        let state = AgentState::initialize(temp.path(), "org-test").unwrap();
        let spool = Spool::open(temp.path()).unwrap();
        (temp, state, spool)
    }

    #[test]
    fn signed_job_is_verified_and_replay_is_idempotent() {
        let (_temp, state, mut spool) = setup();
        let job = create_local_job(
            &state,
            "case-test",
            vec![CollectorRequest::new("system")],
            ResourceBudget::default(),
            Duration::minutes(5),
        )
        .unwrap();
        assert!(matches!(
            admit(&state, &mut spool, &job).unwrap(),
            NonceOutcome::New(_)
        ));
        assert!(matches!(
            admit(&state, &mut spool, &job).unwrap(),
            NonceOutcome::Duplicate(_)
        ));
    }

    #[test]
    fn malformed_signature_and_expiry_fail_before_nonce_consumption() {
        let (_temp, state, mut spool) = setup();
        let mut job = create_local_job(
            &state,
            "case-test",
            vec![CollectorRequest::new("system")],
            ResourceBudget::default(),
            Duration::minutes(5),
        )
        .unwrap();
        job.signature.value_base64 = "broken".to_owned();
        assert!(admit(&state, &mut spool, &job).is_err());
        let expired = create_local_job(
            &state,
            "case-test",
            vec![CollectorRequest::new("system")],
            ResourceBudget::default(),
            Duration::seconds(-1),
        )
        .unwrap();
        assert!(matches!(
            admit(&state, &mut spool, &expired),
            Err(AgentError::Rejected {
                code: "JOB_EXPIRED",
                ..
            })
        ));
    }
}
