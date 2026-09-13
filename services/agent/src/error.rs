use thiserror::Error;

#[derive(Debug, Error)]
pub enum AgentError {
    #[error("{code}: {message}")]
    Rejected { code: &'static str, message: String },
    #[error("I/O failure: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON failure: {0}")]
    Json(#[from] serde_json::Error),
    #[error("state database failure: {0}")]
    Sql(#[from] rusqlite::Error),
    #[error("cryptographic operation failed")]
    Crypto,
}

impl AgentError {
    pub fn rejected(code: &'static str, message: impl Into<String>) -> Self {
        Self::Rejected {
            code,
            message: message.into(),
        }
    }
}

pub type Result<T> = std::result::Result<T, AgentError>;
