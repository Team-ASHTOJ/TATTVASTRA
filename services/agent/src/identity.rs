use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use base64::Engine;
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand_core::OsRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

use crate::error::{AgentError, Result};
use crate::model::{JobSignature, ResourceBudget, SCHEMA_VERSION};

const IDENTITY_KEY: &str = "identity.key";
const DEV_AUTHORITY_KEY: &str = "dev-authority.key";
const CONFIG: &str = "config.json";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AgentConfig {
    pub schema_version: String,
    pub endpoint_id: String,
    pub organization_id: String,
    pub identity_public_key_base64: String,
    pub trusted_job_authorities: BTreeMap<String, String>,
    pub capabilities: BTreeSet<String>,
    pub allowed_roots: Vec<String>,
    pub max_budget: ResourceBudget,
    pub max_concurrency: usize,
    pub local_development: bool,
    pub remote_transport_configured: bool,
    pub key_storage: String,
}

pub struct AgentState {
    pub root: PathBuf,
    pub config: AgentConfig,
}

impl AgentState {
    pub fn initialize(root: &Path, organization_id: &str) -> Result<Self> {
        if organization_id.is_empty() {
            return Err(AgentError::rejected(
                "INVALID_ORGANIZATION",
                "organization ID cannot be empty",
            ));
        }
        fs::create_dir_all(root)?;
        let config_path = root.join(CONFIG);
        if config_path.exists() {
            return Err(AgentError::rejected(
                "ALREADY_INITIALIZED",
                "agent state already exists",
            ));
        }

        let identity = SigningKey::generate(&mut OsRng);
        let authority = SigningKey::generate(&mut OsRng);
        write_secret(&root.join(IDENTITY_KEY), &identity.to_bytes())?;
        write_secret(&root.join(DEV_AUTHORITY_KEY), &authority.to_bytes())?;

        let public = identity.verifying_key().to_bytes();
        let endpoint_id = format!("endpoint-{}", &hex::encode(Sha256::digest(public))[..24]);
        let authority_id = "local-dev-authority".to_owned();
        let mut trusted_job_authorities = BTreeMap::new();
        trusted_job_authorities.insert(
            authority_id,
            base64::engine::general_purpose::STANDARD.encode(authority.verifying_key().to_bytes()),
        );
        let capabilities = [
            "system.read",
            "users.read",
            "process.read",
            "network.read",
            "filesystem.metadata",
            "filesystem.content",
            "persistence.read",
            "logs.read",
            "drivers.read",
        ]
        .into_iter()
        .map(str::to_owned)
        .collect();
        let allowed_root = std::env::current_dir()?.canonicalize()?;
        let config = AgentConfig {
            schema_version: SCHEMA_VERSION.to_owned(),
            endpoint_id,
            organization_id: organization_id.to_owned(),
            identity_public_key_base64: base64::engine::general_purpose::STANDARD.encode(public),
            trusted_job_authorities,
            capabilities,
            allowed_roots: vec![allowed_root.to_string_lossy().into_owned()],
            max_budget: ResourceBudget::default(),
            max_concurrency: 1,
            local_development: true,
            remote_transport_configured: false,
            key_storage: key_storage_status().to_owned(),
        };
        write_secret(&config_path, &serde_json::to_vec_pretty(&config)?)?;
        Ok(Self {
            root: root.to_path_buf(),
            config,
        })
    }

    pub fn load(root: &Path) -> Result<Self> {
        let config: AgentConfig = serde_json::from_slice(&fs::read(root.join(CONFIG))?)?;
        if config.schema_version != SCHEMA_VERSION {
            return Err(AgentError::rejected(
                "STATE_VERSION_MISMATCH",
                "unsupported agent state schema",
            ));
        }
        let state = Self {
            root: root.to_path_buf(),
            config,
        };
        state.validate_key_material()?;
        Ok(state)
    }

    pub fn sign_identity(&self, bytes: &[u8]) -> Result<JobSignature> {
        let key = read_signing_key(&self.root.join(IDENTITY_KEY))?;
        Ok(signature_record(
            "SIGNED",
            "endpoint-identity",
            &key.sign(bytes),
        ))
    }

    pub fn sign_local_job(&self, bytes: &[u8]) -> Result<JobSignature> {
        if !self.config.local_development {
            return Err(AgentError::rejected(
                "LOCAL_AUTHORITY_DISABLED",
                "local development authority is disabled",
            ));
        }
        let key = read_signing_key(&self.root.join(DEV_AUTHORITY_KEY))?;
        Ok(signature_record(
            "SIGNED",
            "local-dev-authority",
            &key.sign(bytes),
        ))
    }

    pub fn verify_job_signature(&self, key_id: &str, bytes: &[u8], value: &str) -> Result<()> {
        let encoded = self
            .config
            .trusted_job_authorities
            .get(key_id)
            .ok_or_else(|| AgentError::rejected("UNTRUSTED_SIGNER", "job signer is not trusted"))?;
        let public = decode_array::<32>(encoded)?;
        let signature_bytes = base64::engine::general_purpose::STANDARD
            .decode(value)
            .map_err(|_| AgentError::Crypto)?;
        let signature = Signature::from_slice(&signature_bytes).map_err(|_| AgentError::Crypto)?;
        let key = VerifyingKey::from_bytes(&public).map_err(|_| AgentError::Crypto)?;
        key.verify(bytes, &signature)
            .map_err(|_| AgentError::rejected("INVALID_SIGNATURE", "job signature is invalid"))
    }

    fn validate_key_material(&self) -> Result<()> {
        let identity = read_signing_key(&self.root.join(IDENTITY_KEY))?;
        let public = identity.verifying_key().to_bytes();
        let configured = decode_array::<32>(&self.config.identity_public_key_base64)?;
        let endpoint_id = format!("endpoint-{}", &hex::encode(Sha256::digest(public))[..24]);
        if public != configured || endpoint_id != self.config.endpoint_id {
            return Err(AgentError::rejected(
                "IDENTITY_MISMATCH",
                "endpoint private key, public key, and endpoint ID do not agree",
            ));
        }
        if self.config.local_development {
            let authority = read_signing_key(&self.root.join(DEV_AUTHORITY_KEY))?;
            let configured = self
                .config
                .trusted_job_authorities
                .get("local-dev-authority")
                .ok_or_else(|| {
                    AgentError::rejected(
                        "LOCAL_AUTHORITY_MISSING",
                        "local development authority is absent from the trust store",
                    )
                })?;
            if authority.verifying_key().to_bytes() != decode_array::<32>(configured)? {
                return Err(AgentError::rejected(
                    "LOCAL_AUTHORITY_MISMATCH",
                    "local development authority key does not match the trust store",
                ));
            }
        }
        if self.config.max_concurrency != 1 {
            return Err(AgentError::rejected(
                "INVALID_CONCURRENCY_POLICY",
                "this Agent build supports exactly one isolated worker",
            ));
        }
        Ok(())
    }
}

fn signature_record(status: &str, key_id: &str, signature: &Signature) -> JobSignature {
    JobSignature {
        status: status.to_owned(),
        algorithm: "Ed25519".to_owned(),
        key_id: key_id.to_owned(),
        value_base64: base64::engine::general_purpose::STANDARD.encode(signature.to_bytes()),
    }
}

fn read_signing_key(path: &Path) -> Result<SigningKey> {
    let bytes = Zeroizing::new(fs::read(path)?);
    let key: [u8; 32] = bytes
        .as_slice()
        .try_into()
        .map_err(|_| AgentError::Crypto)?;
    Ok(SigningKey::from_bytes(&key))
}

fn decode_array<const N: usize>(text: &str) -> Result<[u8; N]> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(text)
        .map_err(|_| AgentError::Crypto)?;
    bytes.try_into().map_err(|_| AgentError::Crypto)
}

fn write_secret(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

#[cfg(unix)]
const fn key_storage_status() -> &'static str {
    "MODE_0600"
}

#[cfg(windows)]
const fn key_storage_status() -> &'static str {
    "UNSUPPORTED_LOCAL_FILE_ONLY"
}

#[cfg(not(any(unix, windows)))]
const fn key_storage_status() -> &'static str {
    "UNSUPPORTED"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identity_is_stable_across_loads() {
        let temp = tempfile::tempdir().unwrap();
        let first = AgentState::initialize(temp.path(), "org-test").unwrap();
        let endpoint = first.config.endpoint_id.clone();
        drop(first);
        let second = AgentState::load(temp.path()).unwrap();
        assert_eq!(second.config.endpoint_id, endpoint);
        assert!(!second.config.remote_transport_configured);
    }

    #[test]
    fn tampered_identity_configuration_fails_closed() {
        let temp = tempfile::tempdir().unwrap();
        AgentState::initialize(temp.path(), "org-test").unwrap();
        let path = temp.path().join(CONFIG);
        let mut config: AgentConfig = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
        config.endpoint_id = "endpoint-tampered".to_owned();
        fs::write(path, serde_json::to_vec(&config).unwrap()).unwrap();
        assert!(matches!(
            AgentState::load(temp.path()),
            Err(AgentError::Rejected {
                code: "IDENTITY_MISMATCH",
                ..
            })
        ));
    }
}
