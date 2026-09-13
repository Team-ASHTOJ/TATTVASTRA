use std::collections::VecDeque;
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

use chrono::{DateTime, Utc};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::error::{AgentError, Result};
use crate::model::{
    Availability, CollectorDescriptor, CollectorIssue, CollectorOutput, CollectorRequest, Platform,
    ResourceBudget,
};

#[cfg(target_os = "linux")]
mod linux;
#[cfg(windows)]
mod windows;

const COLLECTORS: &[(&str, &str)] = &[
    ("system", "system.read"),
    ("users", "users.read"),
    ("sessions", "users.read"),
    ("processes", "process.read"),
    ("interfaces", "network.read"),
    ("connections", "network.read"),
    ("routes", "network.read"),
    ("files", "filesystem.metadata"),
    ("file_metadata", "filesystem.metadata"),
    ("file_hash", "filesystem.content"),
    ("services", "persistence.read"),
    ("startup", "persistence.read"),
    ("events", "logs.read"),
    ("software", "system.read"),
    ("drivers", "drivers.read"),
    ("modules", "drivers.read"),
];

pub struct CollectorContext {
    pub budget: ResourceBudget,
    pub allowed_roots: Vec<PathBuf>,
    pub files_examined: u64,
    pub bytes_read: u64,
}

impl CollectorContext {
    pub fn new(budget: ResourceBudget, allowed_roots: &[String]) -> Self {
        let roots = allowed_roots
            .iter()
            .filter_map(|root| Path::new(root).canonicalize().ok())
            .collect();
        Self {
            budget,
            allowed_roots: roots,
            files_examined: 0,
            bytes_read: 0,
        }
    }

    pub fn charge_file(&mut self) -> Result<()> {
        self.files_examined = self.files_examined.saturating_add(1);
        if self.files_examined > self.budget.max_file_count {
            return Err(AgentError::rejected(
                "FILE_COUNT_EXCEEDED",
                "collector exceeded the file-count budget",
            ));
        }
        Ok(())
    }

    pub fn charge_bytes(&mut self, bytes: u64) -> Result<()> {
        self.bytes_read = self.bytes_read.saturating_add(bytes);
        if self.bytes_read > self.budget.max_file_bytes || self.bytes_read > self.budget.io_bytes {
            return Err(AgentError::rejected(
                "FILE_BYTES_EXCEEDED",
                "collector exceeded the byte-read budget",
            ));
        }
        Ok(())
    }

    fn approved(&self, path: &Path) -> Result<PathBuf> {
        let canonical = path.canonicalize().map_err(|error| {
            AgentError::rejected("PATH_UNAVAILABLE", format!("{}: {error}", path.display()))
        })?;
        if self
            .allowed_roots
            .iter()
            .any(|root| canonical.starts_with(root))
        {
            Ok(canonical)
        } else {
            Err(AgentError::rejected(
                "PATH_DENIED",
                format!("{} is outside approved roots", canonical.display()),
            ))
        }
    }
}

pub fn required_capability(name: &str) -> Option<&'static str> {
    COLLECTORS
        .iter()
        .find_map(|(collector, capability)| (*collector == name).then_some(*capability))
}

pub fn catalog() -> Vec<CollectorDescriptor> {
    let platform = Platform::current();
    let mut result = COLLECTORS
        .iter()
        .map(|(name, capability)| {
            let (availability, reason) = platform_availability(name);
            CollectorDescriptor {
                name: (*name).to_owned(),
                capability: (*capability).to_owned(),
                availability,
                reason,
                platform: platform.clone(),
            }
        })
        .collect::<Vec<_>>();
    for (name, executable) in [
        ("yara", "yara"),
        ("volatility3", "vol.py"),
        ("osquery", "osqueryi"),
    ] {
        let available = command_available(executable);
        result.push(CollectorDescriptor {
            name: name.to_owned(),
            capability: format!("adapter.{name}"),
            availability: if available {
                Availability::Partial
            } else {
                Availability::Unavailable
            },
            reason: Some(if available {
                format!("{executable} is present; policy-approved supplied-input execution is not enabled")
            } else {
                format!("{executable} was not found on PATH")
            }),
            platform: platform.clone(),
        });
    }
    result
}

fn platform_availability(name: &str) -> (Availability, Option<String>) {
    if !cfg!(any(target_os = "linux", windows)) {
        return (
            Availability::Unavailable,
            Some("unsupported endpoint platform".to_owned()),
        );
    }
    #[cfg(not(target_os = "linux"))]
    let _ = name;
    #[cfg(target_os = "linux")]
    if let Some(program) = match name {
        "sessions" => Some("who"),
        "services" => Some("systemctl"),
        "events" => Some("journalctl"),
        "software" => Some("dpkg-query"),
        _ => None,
    } {
        if !command_available(program) {
            return (
                Availability::Unavailable,
                Some(format!(
                    "required read-only adapter {program} was not found on PATH"
                )),
            );
        }
    }
    #[cfg(windows)]
    if !command_available("powershell") && !command_available("powershell.exe") {
        return (
            Availability::Unavailable,
            Some("powershell.exe was not found on PATH".to_owned()),
        );
    }
    (Availability::Available, None)
}

pub fn collect(request: &CollectorRequest, context: &mut CollectorContext) -> CollectorOutput {
    let before_files = context.files_examined;
    let before_bytes = context.bytes_read;
    let result = match request.collector.as_str() {
        "files" | "file_metadata" | "file_hash" => collect_files(request, context),
        "yara" | "volatility3" | "osquery" => Ok(CollectorOutput::unavailable(
            &request.collector,
            "ADAPTER_INPUT_REQUIRED",
            "optional adapters require an explicitly supplied, policy-approved input",
        )),
        _ => platform_collect(request, context),
    };
    let mut output = result.unwrap_or_else(|error| error_output(&request.collector, error));
    output.files_examined = context.files_examined.saturating_sub(before_files);
    output.bytes_read = context.bytes_read.saturating_sub(before_bytes);
    output
}

fn platform_collect(
    request: &CollectorRequest,
    context: &mut CollectorContext,
) -> Result<CollectorOutput> {
    #[cfg(target_os = "linux")]
    {
        return linux::collect(request, context);
    }
    #[cfg(windows)]
    {
        return windows::collect(request, context);
    }
    #[allow(unreachable_code)]
    Ok(CollectorOutput::unavailable(
        &request.collector,
        "PLATFORM_UNSUPPORTED",
        "collector platform is unsupported",
    ))
}

fn error_output(collector: &str, error: AgentError) -> CollectorOutput {
    let (availability, code) = match &error {
        AgentError::Rejected { code, .. } if *code == "PATH_DENIED" => {
            (Availability::Denied, *code)
        }
        AgentError::Rejected { code, .. } => (Availability::Partial, *code),
        AgentError::Io(error) if error.kind() == std::io::ErrorKind::PermissionDenied => {
            (Availability::Denied, "PERMISSION_DENIED")
        }
        _ => (Availability::Partial, "COLLECTOR_FAILED"),
    };
    CollectorOutput {
        collector: collector.to_owned(),
        availability,
        records: Vec::new(),
        issues: vec![CollectorIssue {
            code: code.to_owned(),
            message: error.to_string(),
            path: None,
        }],
        files_examined: 0,
        bytes_read: 0,
    }
}

fn collect_files(
    request: &CollectorRequest,
    context: &mut CollectorContext,
) -> Result<CollectorOutput> {
    let requested = request
        .path
        .as_deref()
        .ok_or_else(|| AgentError::rejected("PATH_REQUIRED", "file collectors require a path"))?;
    let root = context.approved(Path::new(requested))?;
    let mut queue = VecDeque::from([root]);
    let mut records = Vec::new();
    let mut issues = Vec::new();
    while let Some(path) = queue.pop_front() {
        if records.len() >= request.limit {
            break;
        }
        context.charge_file()?;
        let metadata = match fs::symlink_metadata(&path) {
            Ok(value) => value,
            Err(error) => {
                issues.push(CollectorIssue {
                    code: if error.kind() == std::io::ErrorKind::PermissionDenied {
                        "PERMISSION_DENIED"
                    } else {
                        "METADATA_UNAVAILABLE"
                    }
                    .to_owned(),
                    message: error.to_string(),
                    path: Some(path.to_string_lossy().into_owned()),
                });
                continue;
            }
        };
        let is_directory = metadata.is_dir();
        let should_hash = (request.hash || request.collector == "file_hash") && metadata.is_file();
        let hash = if should_hash {
            Some(hash_file(&path, context)?)
        } else {
            None
        };
        records.push(json!({
            "path": path.to_string_lossy(),
            "name": path.file_name().map(|value| value.to_string_lossy().into_owned()).unwrap_or_default(),
            "size": metadata.is_file().then_some(metadata.len()),
            "modified_at": metadata.modified().ok().map(time_string),
            "created_at": metadata.created().ok().map(time_string),
            "is_directory": is_directory,
            "is_symlink": metadata.file_type().is_symlink(),
            "sha256": hash,
        }));
        if is_directory && (request.recursive || records.len() == 1) {
            match fs::read_dir(&path) {
                Ok(entries) => {
                    let mut children = entries
                        .filter_map(std::result::Result::ok)
                        .map(|entry| entry.path())
                        .collect::<Vec<_>>();
                    children.sort();
                    if !request.recursive {
                        children.retain(|child| {
                            fs::symlink_metadata(child)
                                .map(|item| !item.is_dir())
                                .unwrap_or(true)
                        });
                    }
                    queue.extend(children);
                }
                Err(error) => issues.push(CollectorIssue {
                    code: "DIRECTORY_UNAVAILABLE".to_owned(),
                    message: error.to_string(),
                    path: Some(path.to_string_lossy().into_owned()),
                }),
            }
        }
    }
    Ok(CollectorOutput {
        collector: request.collector.clone(),
        availability: if issues.is_empty() {
            Availability::Available
        } else {
            Availability::Partial
        },
        records,
        issues,
        files_examined: 0,
        bytes_read: 0,
    })
}

fn hash_file(path: &Path, context: &mut CollectorContext) -> Result<String> {
    let before = fs::metadata(path)?;
    let mut file = File::open(path)?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        context.charge_bytes(read as u64)?;
        digest.update(&buffer[..read]);
    }
    let after = fs::metadata(path)?;
    if before.len() != after.len() || before.modified().ok() != after.modified().ok() {
        return Err(AgentError::rejected(
            "FILE_CHANGED_DURING_READ",
            format!("{} changed while hashing", path.display()),
        ));
    }
    Ok(hex::encode(digest.finalize()))
}

fn time_string(time: SystemTime) -> String {
    DateTime::<Utc>::from(time).to_rfc3339()
}

fn command_available(name: &str) -> bool {
    let Some(path) = std::env::var_os("PATH") else {
        return false;
    };
    let extensions: &[&str] = if cfg!(windows) {
        &["", ".exe", ".cmd", ".bat", ".py"]
    } else {
        &[""]
    };
    std::env::split_paths(&path).any(|directory| {
        extensions
            .iter()
            .any(|extension| directory.join(format!("{name}{extension}")).is_file())
    })
}

pub(crate) fn output(collector: &str, records: Vec<Value>) -> CollectorOutput {
    CollectorOutput {
        collector: collector.to_owned(),
        availability: Availability::Available,
        records,
        issues: Vec::new(),
        files_examined: 0,
        bytes_read: 0,
    }
}

pub(crate) fn run_fixed(program: &str, arguments: &[&str], max_bytes: usize) -> Result<String> {
    let result = std::process::Command::new(program)
        .args(arguments)
        .output()?;
    if !result.status.success() {
        return Err(AgentError::rejected(
            "ADAPTER_UNAVAILABLE",
            String::from_utf8_lossy(&result.stderr).trim().to_owned(),
        ));
    }
    if result.stdout.len() > max_bytes {
        return Err(AgentError::rejected(
            "ADAPTER_OUTPUT_EXCEEDED",
            "fixed system adapter exceeded its output bound",
        ));
    }
    String::from_utf8(result.stdout)
        .map_err(|_| AgentError::rejected("ADAPTER_ENCODING", "adapter output was not UTF-8"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn path_scope_denies_outside_root() {
        let temp = tempfile::tempdir().unwrap();
        let other = tempfile::tempdir().unwrap();
        let mut context = CollectorContext::new(
            ResourceBudget::default(),
            &[temp.path().to_string_lossy().into_owned()],
        );
        let mut request = CollectorRequest::new("file_metadata");
        request.path = Some(other.path().to_string_lossy().into_owned());
        let result = collect(&request, &mut context);
        assert_eq!(result.availability, Availability::Denied);
        assert_eq!(result.issues[0].code, "PATH_DENIED");
    }

    #[test]
    fn empty_directory_is_an_explicit_nonempty_metadata_result() {
        let temp = tempfile::tempdir().unwrap();
        let mut context = CollectorContext::new(
            ResourceBudget::default(),
            &[temp.path().to_string_lossy().into_owned()],
        );
        let mut request = CollectorRequest::new("files");
        request.path = Some(temp.path().to_string_lossy().into_owned());
        let result = collect(&request, &mut context);
        assert_eq!(result.records.len(), 1);
        assert_eq!(result.availability, Availability::Available);
    }

    #[test]
    fn inaccessible_path_is_reported_without_fabricating_records() {
        let temp = tempfile::tempdir().unwrap();
        let missing = temp.path().join("does-not-exist");
        let mut context = CollectorContext::new(
            ResourceBudget::default(),
            &[temp.path().to_string_lossy().into_owned()],
        );
        let mut request = CollectorRequest::new("file_metadata");
        request.path = Some(missing.to_string_lossy().into_owned());
        let result = collect(&request, &mut context);
        assert_eq!(result.availability, Availability::Partial);
        assert!(result.records.is_empty());
        assert_eq!(result.issues[0].code, "PATH_UNAVAILABLE");
    }

    #[test]
    fn file_count_and_byte_budgets_fail_closed() {
        let temp = tempfile::tempdir().unwrap();
        fs::write(temp.path().join("sample.bin"), b"four").unwrap();
        let roots = &[temp.path().to_string_lossy().into_owned()];

        let count_budget = ResourceBudget {
            max_file_count: 1,
            ..ResourceBudget::default()
        };
        let mut context = CollectorContext::new(count_budget, roots);
        let mut request = CollectorRequest::new("files");
        request.path = Some(temp.path().to_string_lossy().into_owned());
        let count_result = collect(&request, &mut context);
        assert_eq!(count_result.availability, Availability::Partial);
        assert_eq!(count_result.issues[0].code, "FILE_COUNT_EXCEEDED");

        let byte_budget = ResourceBudget {
            max_file_bytes: 3,
            ..ResourceBudget::default()
        };
        let mut context = CollectorContext::new(byte_budget, roots);
        let mut request = CollectorRequest::new("file_hash");
        request.path = Some(
            temp.path()
                .join("sample.bin")
                .to_string_lossy()
                .into_owned(),
        );
        let byte_result = collect(&request, &mut context);
        assert_eq!(byte_result.availability, Availability::Partial);
        assert_eq!(byte_result.issues[0].code, "FILE_BYTES_EXCEEDED");
    }
}
