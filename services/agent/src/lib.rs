use std::path::Path;

use serde::Serialize;

pub mod collectors;
pub mod error;
pub mod evidence;
pub mod identity;
pub mod model;
pub mod policy;
pub mod risk;
pub mod runner;
pub mod spool;

pub mod wire {
    tonic::include_proto!("jocky.v1");
}

#[derive(Debug, Serialize)]
pub struct AgentStatus {
    pub schema_version: &'static str,
    pub simulation: bool,
    pub version: &'static str,
    pub host_os: &'static str,
    pub host_arch: &'static str,
    pub supported_endpoint_platform: bool,
    pub initialized: bool,
    pub endpoint_id: Option<String>,
    pub organization_id: Option<String>,
    pub local_standalone_operational: bool,
    pub remote_transport_configured: bool,
    pub remote_transport_available: bool,
    pub collectors: Vec<model::CollectorDescriptor>,
    pub execution_worker_available: bool,
    pub llvm_real_host_integration: &'static str,
    pub enforcement: model::EnforcementReport,
    pub key_storage: String,
    pub reason: String,
}

pub fn doctor(state_dir: &Path) -> AgentStatus {
    let supported = cfg!(any(target_os = "linux", windows));
    let loaded = identity::AgentState::load(state_dir).ok();
    let initialized = loaded.is_some();
    AgentStatus {
        schema_version: model::SCHEMA_VERSION,
        simulation: false,
        version: env!("CARGO_PKG_VERSION"),
        host_os: std::env::consts::OS,
        host_arch: std::env::consts::ARCH,
        supported_endpoint_platform: supported,
        initialized,
        endpoint_id: loaded.as_ref().map(|state| state.config.endpoint_id.clone()),
        organization_id: loaded
            .as_ref()
            .map(|state| state.config.organization_id.clone()),
        local_standalone_operational: supported && initialized,
        remote_transport_configured: loaded
            .as_ref()
            .is_some_and(|state| state.config.remote_transport_configured),
        remote_transport_available: false,
        collectors: collectors::catalog(),
        execution_worker_available: supported && initialized,
        llvm_real_host_integration: "UNAVAILABLE: current ORC path binds a simulated C++ fixture; REAL jobs use the isolated Rust collector worker",
        enforcement: model::EnforcementReport::current(),
        key_storage: loaded
            .as_ref()
            .map_or_else(|| "UNINITIALIZED".to_owned(), |state| state.config.key_storage.clone()),
        reason: if !supported {
            "This host is not a supported endpoint platform.".to_owned()
        } else if !initialized {
            "Initialize local state before collection or job execution.".to_owned()
        } else {
            "Local standalone REAL collection is available; no server connectivity is configured or claimed."
                .to_owned()
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use prost::Message;

    #[test]
    fn uninitialized_doctor_does_not_claim_remote_connectivity() {
        let temp = tempfile::tempdir().unwrap();
        let status = doctor(temp.path());
        assert!(!status.remote_transport_available);
        assert!(!status.remote_transport_configured);
        assert!(!status.local_standalone_operational);
    }

    #[test]
    fn transport_preserves_simulation_and_signed_bytes() {
        let frame = wire::AgentFrame {
            schema_version: "1.0.0".into(),
            endpoint_id: "fixture-endpoint".into(),
            sequence: 4,
            simulation: Some(true),
            body: Some(wire::agent_frame::Body::Observation(
                wire::CanonicalDocument {
                    json_utf8: br#"{"simulation":true}"#.to_vec(),
                },
            )),
        };
        let decoded = wire::AgentFrame::decode(frame.encode_to_vec().as_slice()).unwrap();
        assert_eq!(decoded, frame);
    }
}
