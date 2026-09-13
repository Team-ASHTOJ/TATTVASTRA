use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::error::{AgentError, Result};

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DriverIdentity {
    pub name: String,
    pub path: Option<String>,
    pub version: Option<String>,
    pub sha256: Option<String>,
    pub signer: Option<String>,
    pub signature_status: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RiskMatch {
    pub source: String,
    pub source_version: String,
    pub source_hash: String,
    pub risk: String,
    pub cve: Option<String>,
    pub blocklist_match: Option<bool>,
}

pub trait DriverRiskAdapter {
    fn lookup(&self, driver: &DriverIdentity) -> Result<Option<RiskMatch>>;
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RiskFile {
    schema_version: String,
    source: String,
    source_version: String,
    source_hash: String,
    entries: BTreeMap<String, RiskEntry>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RiskEntry {
    risk: String,
    cve: Option<String>,
    blocklist_match: Option<bool>,
}

pub struct JsonRiskAdapter {
    file: RiskFile,
}

impl JsonRiskAdapter {
    pub fn load(path: &Path) -> Result<Self> {
        let bytes = fs::read(path)?;
        if bytes.len() > 16_000_000 {
            return Err(AgentError::rejected(
                "RISK_DATA_TOO_LARGE",
                "risk metadata exceeded 16 MB",
            ));
        }
        let file: RiskFile = serde_json::from_slice(&bytes)?;
        if file.schema_version != "1.0.0"
            || file.source.is_empty()
            || file.source_version.is_empty()
            || file.source_hash.len() != 64
        {
            return Err(AgentError::rejected(
                "RISK_DATA_INVALID",
                "risk metadata identity is incomplete",
            ));
        }
        Ok(Self { file })
    }
}

impl DriverRiskAdapter for JsonRiskAdapter {
    fn lookup(&self, driver: &DriverIdentity) -> Result<Option<RiskMatch>> {
        let key = driver
            .sha256
            .as_ref()
            .map(|value| value.to_ascii_lowercase())
            .unwrap_or_else(|| driver.name.to_ascii_lowercase());
        Ok(self.file.entries.get(&key).map(|entry| RiskMatch {
            source: self.file.source.clone(),
            source_version: self.file.source_version.clone(),
            source_hash: self.file.source_hash.clone(),
            risk: entry.risk.clone(),
            cve: entry.cve.clone(),
            blocklist_match: entry.blocklist_match,
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn absent_risk_metadata_is_unknown_not_safe() {
        struct Empty;
        impl DriverRiskAdapter for Empty {
            fn lookup(&self, _driver: &DriverIdentity) -> Result<Option<RiskMatch>> {
                Ok(None)
            }
        }
        let result = Empty
            .lookup(&DriverIdentity {
                name: "example".to_owned(),
                path: None,
                version: None,
                sha256: None,
                signer: None,
                signature_status: None,
            })
            .unwrap();
        assert!(result.is_none());
    }
}
