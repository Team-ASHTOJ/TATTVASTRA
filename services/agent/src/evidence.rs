use std::collections::BTreeMap;

use chrono::Utc;
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::error::{AgentError, Result};
use crate::identity::AgentState;
use crate::model::{
    CollectorOutput, EvidenceManifest, JobSignature, Observation, Platform, SignedJob,
    SCHEMA_VERSION,
};

pub fn normalize(
    job: &SignedJob,
    output: &CollectorOutput,
    observed_at: &str,
) -> Result<Vec<Observation>> {
    output
        .records
        .iter()
        .map(|record| {
            let object = record.as_object().ok_or_else(|| {
                AgentError::rejected("NORMALIZATION_FAILED", "collector record was not an object")
            })?;
            let data = object
                .iter()
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect::<BTreeMap<_, _>>();
            let mut observation = Observation {
                schema_version: SCHEMA_VERSION.to_owned(),
                observation_id: format!("obs-{}", Uuid::new_v4().simple()),
                endpoint_id: job.endpoint_id.clone(),
                job_id: job.job_id.clone(),
                case_id: job.case_id.clone(),
                collector: output.collector.clone(),
                observed_at: observed_at.to_owned(),
                source_time: source_time(&data),
                platform: Platform::current(),
                data,
                integrity_hash: String::new(),
                simulation: false,
                simulation_label: None,
            };
            observation.integrity_hash = integrity_hash(&observation)?;
            Ok(observation)
        })
        .collect()
}

pub fn manifest(
    state: &AgentState,
    job: &SignedJob,
    started_at: &str,
    observations: &[Observation],
) -> Result<EvidenceManifest> {
    let mut manifest = EvidenceManifest {
        schema_version: SCHEMA_VERSION.to_owned(),
        endpoint_id: job.endpoint_id.clone(),
        job_id: job.job_id.clone(),
        case_id: job.case_id.clone(),
        agent_identity: state.config.endpoint_id.clone(),
        started_at: started_at.to_owned(),
        completed_at: Utc::now().to_rfc3339(),
        observation_hashes: observations
            .iter()
            .map(|item| item.integrity_hash.clone())
            .collect(),
        simulation: false,
        simulation_label: None,
        signature: JobSignature {
            status: "UNSIGNED".to_owned(),
            algorithm: "Ed25519".to_owned(),
            key_id: "endpoint-identity".to_owned(),
            value_base64: String::new(),
        },
    };
    let bytes = domain_bytes("JOCKY:manifest:v1\n", &manifest, "signature")?;
    manifest.signature = state.sign_identity(&bytes)?;
    Ok(manifest)
}

pub fn integrity_hash(observation: &Observation) -> Result<String> {
    Ok(hex::encode(Sha256::digest(domain_bytes(
        "",
        observation,
        "integrity_hash",
    )?)))
}

pub fn domain_bytes<T: Serialize>(domain: &str, value: &T, excluded: &str) -> Result<Vec<u8>> {
    let mut document = serde_json::to_value(value)?;
    let object = document.as_object_mut().ok_or_else(|| {
        AgentError::rejected("CANONICALIZATION_FAILED", "document is not an object")
    })?;
    object.remove(excluded);
    let mut bytes = domain.as_bytes().to_vec();
    bytes.extend(serde_jcs::to_vec(&document).map_err(|_| AgentError::Crypto)?);
    Ok(bytes)
}

fn source_time(data: &BTreeMap<String, Value>) -> Option<String> {
    ["source_time", "timestamp", "start_time", "modified_at"]
        .into_iter()
        .find_map(|key| data.get(key)?.as_str().map(str::to_owned))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{
        Availability, CollectorRequest, EnforcementPolicy, ResourceBudget, SignedJob,
    };

    fn job() -> SignedJob {
        SignedJob {
            schema_version: SCHEMA_VERSION.to_owned(),
            simulation: false,
            simulation_label: None,
            job_id: "job-test".to_owned(),
            case_id: "case-test".to_owned(),
            organization_id: "org-test".to_owned(),
            endpoint_id: "endpoint-test".to_owned(),
            required_capabilities: vec!["system.read".to_owned()],
            collectors: vec![CollectorRequest::new("system")],
            budget: ResourceBudget::default(),
            enforcement_policy: EnforcementPolicy::Monitored,
            nonce: "00".repeat(32),
            issued_at: Utc::now().to_rfc3339(),
            expires_at: (Utc::now() + chrono::Duration::minutes(5)).to_rfc3339(),
            signature: JobSignature {
                status: "SIGNED".to_owned(),
                algorithm: "Ed25519".to_owned(),
                key_id: "test".to_owned(),
                value_base64: "test".to_owned(),
            },
        }
    }

    #[test]
    fn real_observation_hash_detects_content_change() {
        let output = CollectorOutput {
            collector: "system".to_owned(),
            availability: Availability::Available,
            records: vec![serde_json::json!({"hostname": "real-host"})],
            issues: Vec::new(),
            files_examined: 0,
            bytes_read: 0,
        };
        let mut observation = normalize(&job(), &output, &Utc::now().to_rfc3339())
            .unwrap()
            .remove(0);
        assert!(!observation.simulation);
        let original = observation.integrity_hash.clone();
        observation
            .data
            .insert("hostname".to_owned(), Value::String("changed".to_owned()));
        assert_ne!(integrity_hash(&observation).unwrap(), original);
    }
}
