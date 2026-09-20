use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Nonce};
use rand_core::{OsRng, RngCore};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use zeroize::Zeroizing;

use crate::error::{AgentError, Result};

const SPOOL_KEY: &str = "spool.key";

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct SpoolRecord {
    pub record_id: String,
    pub kind: String,
    pub payload: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NonceOutcome {
    New(String),
    Duplicate(String),
}

pub struct Spool {
    root: PathBuf,
    connection: Connection,
    key: Zeroizing<Vec<u8>>,
}

impl Spool {
    pub fn open(root: &Path) -> Result<Self> {
        fs::create_dir_all(root)?;
        let key_path = root.join(SPOOL_KEY);
        let database_path = root.join("agent.db");
        if !key_path.exists() {
            if database_path.exists() {
                return Err(AgentError::rejected(
                    "MISSING_SPOOL_KEY",
                    "existing spool database cannot be opened without its original key",
                ));
            }
            let mut key = [0_u8; 32];
            OsRng.fill_bytes(&mut key);
            write_secret(&key_path, &key)?;
        }
        let key = Zeroizing::new(fs::read(&key_path)?);
        if key.len() != 32 {
            return Err(AgentError::rejected(
                "INVALID_SPOOL_KEY",
                "spool key must be 32 bytes",
            ));
        }
        let connection = Connection::open(database_path)?;
        connection.execute_batch(
            "PRAGMA journal_mode=WAL;
             CREATE TABLE IF NOT EXISTS nonce_ledger (
               nonce TEXT PRIMARY KEY,
               job_id TEXT NOT NULL,
               receipt_id TEXT NOT NULL,
               expires_at TEXT NOT NULL
             );
             CREATE TABLE IF NOT EXISTS spool (
               record_id TEXT PRIMARY KEY,
               kind TEXT NOT NULL,
               nonce BLOB NOT NULL,
               ciphertext BLOB NOT NULL,
               created_at TEXT NOT NULL
             );
             CREATE TABLE IF NOT EXISTS metrics (
               name TEXT PRIMARY KEY,
               value INTEGER NOT NULL
             );
             CREATE TABLE IF NOT EXISTS remote_sequence (id INTEGER PRIMARY KEY CHECK(id=1), value INTEGER NOT NULL);
             INSERT OR IGNORE INTO remote_sequence VALUES (1, 0);
             CREATE TABLE IF NOT EXISTS remote_jobs (job_id TEXT PRIMARY KEY, envelope_hash TEXT NOT NULL, nonce TEXT UNIQUE NOT NULL, done INTEGER NOT NULL DEFAULT 0);",
        )?;
        Ok(Self {
            root: root.to_path_buf(),
            connection,
            key,
        })
    }

    pub fn consume_nonce(
        &mut self,
        nonce: &str,
        job_id: &str,
        expires_at: &str,
    ) -> Result<NonceOutcome> {
        let transaction = self.connection.transaction()?;
        let existing: Option<(String, String)> = transaction
            .query_row(
                "SELECT job_id, receipt_id FROM nonce_ledger WHERE nonce = ?1",
                [nonce],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .optional()?;
        if let Some((existing_job, receipt)) = existing {
            if existing_job != job_id {
                return Err(AgentError::rejected(
                    "NONCE_REUSE",
                    "nonce was already consumed by another job",
                ));
            }
            transaction.commit()?;
            return Ok(NonceOutcome::Duplicate(receipt));
        }
        let receipt = format!("receipt-{}", Uuid::new_v4().simple());
        transaction.execute(
            "INSERT INTO nonce_ledger(nonce, job_id, receipt_id, expires_at) VALUES (?1, ?2, ?3, ?4)",
            params![nonce, job_id, receipt, expires_at],
        )?;
        transaction.commit()?;
        Ok(NonceOutcome::New(receipt))
    }

    pub fn enqueue(&self, kind: &str, payload: &[u8]) -> Result<String> {
        let record_id = format!("spool-{}", Uuid::new_v4().simple());
        let aad = format!("JOCKY:spool:v1:{record_id}:{kind}");
        let mut nonce = [0_u8; 12];
        OsRng.fill_bytes(&mut nonce);
        let cipher = Aes256Gcm::new_from_slice(&self.key).map_err(|_| AgentError::Crypto)?;
        let ciphertext = cipher
            .encrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: payload,
                    aad: aad.as_bytes(),
                },
            )
            .map_err(|_| AgentError::Crypto)?;
        self.connection.execute(
            "INSERT INTO spool(record_id, kind, nonce, ciphertext, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                record_id,
                kind,
                nonce.as_slice(),
                ciphertext,
                chrono::Utc::now().to_rfc3339()
            ],
        )?;
        self.increment("spooled_records", 1)?;
        Ok(record_id)
    }

    pub fn pending(&self) -> Result<Vec<SpoolRecord>> {
        let cipher = Aes256Gcm::new_from_slice(&self.key).map_err(|_| AgentError::Crypto)?;
        let mut statement = self.connection.prepare(
            "SELECT record_id, kind, nonce, ciphertext FROM spool ORDER BY created_at, record_id",
        )?;
        let rows = statement.query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, Vec<u8>>(2)?,
                row.get::<_, Vec<u8>>(3)?,
            ))
        })?;
        let mut records = Vec::new();
        for row in rows {
            let (record_id, kind, nonce, ciphertext) = row?;
            if nonce.len() != 12 {
                return Err(AgentError::Crypto);
            }
            let aad = format!("JOCKY:spool:v1:{record_id}:{kind}");
            let payload = cipher
                .decrypt(
                    Nonce::from_slice(&nonce),
                    Payload {
                        msg: &ciphertext,
                        aad: aad.as_bytes(),
                    },
                )
                .map_err(|_| AgentError::Crypto)?;
            records.push(SpoolRecord {
                record_id,
                kind,
                payload,
            });
        }
        Ok(records)
    }

    pub fn acknowledge(&self, record_id: &str) -> Result<bool> {
        let removed = self
            .connection
            .execute("DELETE FROM spool WHERE record_id = ?1", [record_id])?;
        if removed != 0 {
            self.increment("acknowledged_records", 1)?;
        }
        Ok(removed != 0)
    }

    pub fn pending_count(&self) -> Result<usize> {
        Ok(self
            .connection
            .query_row("SELECT COUNT(*) FROM spool", [], |row| row.get::<_, u64>(0))?
            as usize)
    }

    pub fn increment(&self, name: &str, amount: u64) -> Result<()> {
        self.connection.execute(
            "INSERT INTO metrics(name, value) VALUES (?1, ?2)
             ON CONFLICT(name) DO UPDATE SET value = value + excluded.value",
            params![name, amount],
        )?;
        Ok(())
    }

    pub fn metrics(&self) -> Result<Vec<(String, u64)>> {
        let mut statement = self
            .connection
            .prepare("SELECT name, value FROM metrics ORDER BY name")?;
        let rows = statement.query_map([], |row| Ok((row.get(0)?, row.get(1)?)))?;
        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(AgentError::from)
    }

    pub fn database_path(&self) -> PathBuf {
        self.root.join("agent.db")
    }

    /// Allocate sequence numbers and persist encrypted protobuf bytes atomically.
    /// A crash cannot leave a gap or change an already transmitted frame.
    pub fn queue_remote(
        &mut self,
        frames: &mut [crate::wire::AgentFrame],
        completed_job: Option<&str>,
    ) -> Result<()> {
        use prost::Message;
        let transaction = self.connection.transaction()?;
        let mut sequence: u64 =
            transaction.query_row("SELECT value FROM remote_sequence WHERE id=1", [], |r| {
                r.get(0)
            })?;
        let cipher = Aes256Gcm::new_from_slice(&self.key).map_err(|_| AgentError::Crypto)?;
        for frame in frames {
            sequence += 1;
            frame.sequence = sequence;
            let id = format!("remote-{sequence:020}");
            let mut nonce = [0_u8; 12];
            OsRng.fill_bytes(&mut nonce);
            let ciphertext = cipher
                .encrypt(
                    Nonce::from_slice(&nonce),
                    Payload {
                        msg: &frame.encode_to_vec(),
                        aad: format!("JOCKY:spool:v1:{id}:remote").as_bytes(),
                    },
                )
                .map_err(|_| AgentError::Crypto)?;
            transaction.execute(
                "INSERT INTO spool VALUES (?1,'remote',?2,?3,?4)",
                params![
                    id,
                    nonce.as_slice(),
                    ciphertext,
                    chrono::Utc::now().to_rfc3339()
                ],
            )?;
        }
        transaction.execute("UPDATE remote_sequence SET value=?1 WHERE id=1", [sequence])?;
        if let Some(job) = completed_job {
            transaction.execute("UPDATE remote_jobs SET done=1 WHERE job_id=?1", [job])?;
        }
        transaction.commit()?;
        Ok(())
    }

    pub fn claim_remote_job(&self, job: &str, hash: &str, nonce: &str) -> Result<bool> {
        let existing: Option<String> = self
            .connection
            .query_row(
                "SELECT envelope_hash FROM remote_jobs WHERE job_id=?1",
                [job],
                |r| r.get(0),
            )
            .optional()?;
        if let Some(existing) = existing {
            if existing != hash {
                return Err(AgentError::rejected(
                    "JOB_CONFLICT",
                    "Job ID reused with different signed content",
                ));
            }
            return Ok(false);
        }
        self.connection.execute(
            "INSERT INTO remote_jobs(job_id,envelope_hash,nonce) VALUES (?1,?2,?3)",
            params![job, hash, nonce],
        )?;
        Ok(true)
    }

    pub fn interrupted_remote_jobs(&self) -> Result<Vec<String>> {
        let mut statement = self
            .connection
            .prepare("SELECT job_id FROM remote_jobs WHERE done=0 ORDER BY job_id")?;
        let jobs = statement
            .query_map([], |r| r.get(0))?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        Ok(jobs)
    }

    pub fn remote_job_done(&self, job: &str) -> Result<bool> {
        Ok(self
            .connection
            .query_row(
                "SELECT done FROM remote_jobs WHERE job_id=?1",
                [job],
                |row| row.get::<_, i64>(0),
            )
            .optional()?
            .is_some_and(|done| done != 0))
    }
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

#[cfg(test)]
mod tests {
    use super::*;
    use prost::Message;

    #[test]
    fn encrypted_spool_survives_reopen_and_acknowledges() {
        let temp = tempfile::tempdir().unwrap();
        let spool = Spool::open(temp.path()).unwrap();
        let id = spool
            .enqueue("observation", br#"{"secret":"value"}"#)
            .unwrap();
        let database = fs::read(spool.database_path()).unwrap();
        assert!(!database.windows(6).any(|window| window == b"secret"));
        drop(spool);
        let spool = Spool::open(temp.path()).unwrap();
        let records = spool.pending().unwrap();
        assert_eq!(records[0].record_id, id);
        assert!(spool.acknowledge(&id).unwrap());
        assert_eq!(spool.pending_count().unwrap(), 0);
    }

    #[test]
    fn nonce_is_durable_and_idempotent_for_same_job() {
        let temp = tempfile::tempdir().unwrap();
        let mut spool = Spool::open(temp.path()).unwrap();
        let first = spool.consume_nonce("a", "job-a", "later").unwrap();
        let second = spool.consume_nonce("a", "job-a", "later").unwrap();
        assert!(matches!(first, NonceOutcome::New(_)));
        assert!(matches!(second, NonceOutcome::Duplicate(_)));
        drop(spool);
        let mut reopened = Spool::open(temp.path()).unwrap();
        assert!(matches!(
            reopened.consume_nonce("a", "job-a", "later").unwrap(),
            NonceOutcome::Duplicate(_)
        ));
    }

    #[test]
    fn missing_key_never_silently_rekeys_an_existing_database() {
        let temp = tempfile::tempdir().unwrap();
        let spool = Spool::open(temp.path()).unwrap();
        spool.enqueue("observation", b"evidence").unwrap();
        drop(spool);
        fs::remove_file(temp.path().join(SPOOL_KEY)).unwrap();
        assert!(matches!(
            Spool::open(temp.path()),
            Err(AgentError::Rejected {
                code: "MISSING_SPOOL_KEY",
                ..
            })
        ));
    }

    #[test]
    fn remote_frame_replays_without_reclaiming_or_rerunning_job() {
        let temp = tempfile::tempdir().unwrap();
        let mut spool = Spool::open(temp.path()).unwrap();
        let job = "job-remote-replay";
        assert!(spool
            .claim_remote_job(job, "envelope-hash", "nonce")
            .unwrap());
        assert!(!spool
            .claim_remote_job(job, "envelope-hash", "nonce")
            .unwrap());
        let mut frames = [crate::wire::AgentFrame {
            schema_version: "1.0.0".into(),
            endpoint_id: "endpoint".into(),
            sequence: 0,
            simulation: Some(false),
            body: Some(crate::wire::agent_frame::Body::JobProgress(
                crate::wire::CanonicalDocument {
                    json_utf8: br#"{"schema_version":"1.0.0","job_id":"job-remote-replay","state":"SUCCESS"}"#.to_vec(),
                },
            )),
        }];
        spool.queue_remote(&mut frames, Some(job)).unwrap();
        let original = spool.pending().unwrap().pop().unwrap();
        drop(spool);

        let reopened = Spool::open(temp.path()).unwrap();
        assert!(!reopened
            .claim_remote_job(job, "envelope-hash", "nonce")
            .unwrap());
        let replay = reopened.pending().unwrap().pop().unwrap();
        assert_eq!(replay.record_id, original.record_id);
        assert_eq!(replay.payload, original.payload);
        assert_eq!(
            crate::wire::AgentFrame::decode(replay.payload.as_slice())
                .unwrap()
                .sequence,
            1
        );
        assert!(reopened.acknowledge(&replay.record_id).unwrap());
        assert_eq!(reopened.pending_count().unwrap(), 0);
    }
}
