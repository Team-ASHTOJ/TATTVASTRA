use serde::Serialize;

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
    pub operational: bool,
    pub collectors_available: Vec<&'static str>,
    pub execution_available: bool,
    pub reason: &'static str,
}

pub fn doctor() -> AgentStatus {
    AgentStatus {
        schema_version: "1.0.0",
        simulation: false,
        version: env!("CARGO_PKG_VERSION"),
        host_os: std::env::consts::OS,
        host_arch: std::env::consts::ARCH,
        supported_endpoint_platform: cfg!(any(target_os = "linux", target_os = "windows")),
        operational: false,
        collectors_available: Vec::new(),
        execution_available: false,
        reason: "Agent scaffold. Enrollment, policy, collectors and execution are unavailable.",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use prost::Message;

    #[test]
    fn scaffold_never_claims_endpoint_execution() {
        let status = doctor();
        assert!(!status.operational);
        assert!(!status.execution_available);
        assert!(status.collectors_available.is_empty());
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
