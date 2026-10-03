//! Bounded, read-only YARA scanning of files beneath an approved root.
use std::collections::VecDeque;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use serde_json::json;
use sha2::{Digest, Sha256};

use super::{command_available, hash_file, output, CollectorContext};
use crate::error::{AgentError, Result};
use crate::model::{Availability, CollectorDescriptor, CollectorOutput, CollectorRequest, Platform};

const MAX_RULESET_BYTES: u64 = 1024 * 1024;
const MAX_CONSOLE_BYTES: u64 = 64 * 1024;

pub(super) fn descriptor(platform: Platform) -> CollectorDescriptor {
    let evidence_configured = std::env::var("JOCKY_YARA_EVIDENCE_ROOT")
        .ok()
        .and_then(|path| Path::new(&path).canonicalize().ok())
        .is_some_and(|path| path.is_dir());
    descriptor_for(platform, command_available("yara"), rules_directory().is_ok(), evidence_configured)
}

fn descriptor_for(platform: Platform, binary: bool, rules_configured: bool, evidence_configured: bool) -> CollectorDescriptor {
    let (availability, reason) = if !matches!(platform.os.as_str(), "linux" | "windows") {
        (Availability::Unavailable, Some("unsupported endpoint platform".to_owned()))
    } else if !binary {
        (Availability::Unavailable, Some("yara was not found on PATH".to_owned()))
    } else if !rules_configured {
        (Availability::Partial, Some("no approved ruleset configured".to_owned()))
    } else if !evidence_configured {
        (Availability::Partial, Some("no approved evidence root configured".to_owned()))
    } else {
        (Availability::Available, None)
    };
    CollectorDescriptor {
        name: "yara".to_owned(),
        capability: "adapter.yara".to_owned(),
        availability,
        reason,
        platform,
    }
}

fn rules_directory() -> Result<PathBuf> {
    let configured = std::env::var("JOCKY_YARA_RULESETS_DIR").map_err(|_| {
        AgentError::rejected("RULESET_NOT_APPROVED", "approved YARA ruleset directory is not configured")
    })?;
    let root = Path::new(&configured).canonicalize()?;
    if !root.is_dir() {
        return Err(AgentError::rejected("RULESET_NOT_APPROVED", "approved YARA ruleset directory is invalid"));
    }
    Ok(root)
}

fn approved_ruleset(name: &str) -> Result<(PathBuf, String)> {
    approved_ruleset_in(&rules_directory()?, name)
}

fn approved_ruleset_in(root: &Path, name: &str) -> Result<(PathBuf, String)> {
    if name.is_empty() || name.len() > 64 || name == "." || name == ".." ||
        !name.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-')) {
        return Err(AgentError::rejected("RULESET_INVALID", "ruleset must be a bounded logical identifier"));
    }
    let path = root.join(format!("{name}.yar"));
    let canonical = path.canonicalize().map_err(|_| {
        AgentError::rejected("RULESET_NOT_APPROVED", "ruleset is not approved")
    })?;
    if !canonical.starts_with(root) || !canonical.is_file() {
        return Err(AgentError::rejected("RULESET_NOT_APPROVED", "ruleset is outside the approved directory"));
    }
    let metadata = fs::metadata(&canonical)?;
    if metadata.len() > MAX_RULESET_BYTES {
        return Err(AgentError::rejected("RULESET_INVALID", "ruleset exceeds the static size limit"));
    }
    let hash = hex::encode(Sha256::digest(fs::read(&canonical)?));
    Ok((canonical, hash))
}

fn run_yara(rules: &Path, target: &Path) -> Result<Vec<String>> {
    let mut child = Command::new("yara")
        .arg(rules)
        .arg(target)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    let stdout = child.stdout.take().ok_or_else(|| AgentError::rejected("YARA_FAILED", "YARA stdout unavailable"))?;
    let stderr = child.stderr.take().ok_or_else(|| AgentError::rejected("YARA_FAILED", "YARA stderr unavailable"))?;
    let out_reader = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        stdout.take(MAX_CONSOLE_BYTES + 1).read_to_end(&mut bytes).map(|_| bytes)
    });
    let err_reader = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        stderr.take(MAX_CONSOLE_BYTES + 1).read_to_end(&mut bytes).map(|_| bytes)
    });
    let started = Instant::now();
    let status = loop {
        if let Some(status) = child.try_wait()? { break status; }
        if started.elapsed() > Duration::from_secs(5) {
            let _ = child.kill();
            let _ = child.wait();
            return Err(AgentError::rejected("YARA_TIMEOUT_OR_OUTPUT_LIMIT", "YARA exceeded its time or console-output bound"));
        }
        std::thread::sleep(Duration::from_millis(10));
    };
    let stdout = out_reader.join().map_err(|_| AgentError::rejected("YARA_FAILED", "YARA output reader failed"))??;
    let stderr = err_reader.join().map_err(|_| AgentError::rejected("YARA_FAILED", "YARA error reader failed"))??;
    if stdout.len() as u64 > MAX_CONSOLE_BYTES || stderr.len() as u64 > MAX_CONSOLE_BYTES {
        return Err(AgentError::rejected("YARA_OUTPUT_EXCEEDED", "YARA console output exceeded its bound"));
    }
    if !status.success() {
        return Err(AgentError::rejected("YARA_RULE_FAILED", format!("YARA rejected approved ruleset or target: {}", String::from_utf8_lossy(&stderr).trim())));
    }
    let text = String::from_utf8(stdout).map_err(|_| AgentError::rejected("YARA_OUTPUT_INVALID", "YARA output is not UTF-8"))?;
    parse_yara_output(&text, target)
}

fn parse_yara_output(text: &str, target: &Path) -> Result<Vec<String>> {
    let suffix = format!(" {}", target.display());
    text.lines().map(|line| {
        let rule = line.strip_suffix(&suffix).ok_or_else(|| AgentError::rejected("YARA_OUTPUT_INVALID", "YARA output did not match the scanned file"))?;
        if rule.is_empty() || !rule.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_') {
            return Err(AgentError::rejected("YARA_OUTPUT_INVALID", "YARA emitted an invalid rule identifier"));
        }
        Ok(rule.to_owned())
    }).collect()
}

pub(super) fn collect(request: &CollectorRequest, context: &mut CollectorContext) -> Result<CollectorOutput> {
    if !cfg!(any(target_os = "linux", windows)) {
        return Ok(CollectorOutput::unavailable("yara", "PLATFORM_UNSUPPORTED", "YARA collector requires a supported endpoint platform"));
    }
    if !command_available("yara") {
        return Ok(CollectorOutput::unavailable("yara", "YARA_UNAVAILABLE", "yara was not found on PATH"));
    }
    let name = request.ruleset.as_deref().ok_or_else(|| AgentError::rejected("RULESET_NOT_APPROVED", "an approved ruleset is required"))?;
    let (rules, ruleset_sha256) = approved_ruleset(name)?;
    let evidence_root = std::env::var("JOCKY_YARA_EVIDENCE_ROOT").map_err(|_| {
        AgentError::rejected("PATH_DENIED", "approved YARA evidence root is not configured")
    })?;
    let evidence_root = Path::new(&evidence_root).canonicalize()?;
    let requested = request.path.as_deref().ok_or_else(|| AgentError::rejected("PATH_REQUIRED", "YARA requires an approved path"))?;
    let requested = Path::new(requested).canonicalize()?;
    if !requested.starts_with(&evidence_root) {
        return Err(AgentError::rejected("PATH_DENIED", "YARA target is outside its dedicated evidence root"));
    }
    scan(request, context, name, &rules, &ruleset_sha256)
}

fn scan(request: &CollectorRequest, context: &mut CollectorContext, name: &str, rules: &Path, ruleset_sha256: &str) -> Result<CollectorOutput> {
    let requested = request.path.as_deref().ok_or_else(|| AgentError::rejected("PATH_REQUIRED", "YARA requires an approved path"))?;
    let root = context.approved(Path::new(requested))?;
    if request.limit == 0 || request.limit > 100_000 {
        return Err(AgentError::rejected("LIMIT_INVALID", "YARA limit must be between 1 and 100000"));
    }
    let mut queue = VecDeque::from([root]);
    let mut visited = 0usize;
    let visit_limit = request.limit.saturating_mul(4).min(100_000);
    let initial_files = context.files_examined;
    let mut scan_bytes = 0u64;
    let mut records = Vec::new();
    while let Some(path) = queue.pop_front() {
        visited += 1;
        if visited > visit_limit {
            return Err(AgentError::rejected("FILE_COUNT_EXCEEDED", "YARA directory traversal exceeded its bound"));
        }
        let metadata = fs::symlink_metadata(&path)?;
        if metadata.file_type().is_symlink() {
            // Never follow directory or file symlinks while scanning.
            continue;
        }
        if metadata.is_dir() {
            let mut children = Vec::new();
            for entry in fs::read_dir(&path)? {
                if visited + queue.len() + children.len() >= visit_limit {
                    return Err(AgentError::rejected("FILE_COUNT_EXCEEDED", "YARA directory traversal exceeded its bound"));
                }
                children.push(entry?.path());
            }
            children.sort();
            if !request.recursive && visited != 1 { continue; }
            queue.extend(children);
            continue;
        }
        if !metadata.is_file() { continue; }
        if context.files_examined - initial_files >= request.limit as u64 {
            return Err(AgentError::rejected("FILE_COUNT_EXCEEDED", "YARA request file limit exceeded"));
        }
        let approved = context.approved(&path)?;
        context.charge_file()?;
        context.charge_bytes(metadata.len())?;
        scan_bytes = scan_bytes.saturating_add(metadata.len());
        for rule in run_yara(rules, &approved)? {
            if records.len() >= request.limit {
                return Err(AgentError::rejected("MATCH_LIMIT_EXCEEDED", "YARA match count exceeded its request limit"));
            }
            let file_sha256 = hash_file(&approved, context)?;
            records.push(json!({
                "matched": true, "rule": rule, "path": approved.to_string_lossy(),
                "ruleset": name, "ruleset_sha256": ruleset_sha256,
                "file_sha256": file_sha256, "size": metadata.len(),
            }));
        }
    }
    for record in &mut records {
        record["files_scanned"] = json!(context.files_examined - initial_files);
    }
    let matches = records.len();
    let mut result = output("yara", records);
    result.metadata = Some(json!({
        "ruleset": name,
        "ruleset_sha256": ruleset_sha256,
        "files_scanned": context.files_examined - initial_files,
        "matches": matches,
        "bytes_considered": scan_bytes,
    }));
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::ResourceBudget;

    fn fixture_root() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../fixtures/yara").canonicalize().unwrap()
    }

    #[test]
    fn catalog_distinguishes_missing_binary_and_missing_rules() {
        let linux = Platform { os: "linux".to_owned(), arch: "x86_64".to_owned() };
        assert_eq!(descriptor_for(linux.clone(), false, true, true).availability, Availability::Unavailable);
        assert_eq!(descriptor_for(linux.clone(), true, false, true).availability, Availability::Partial);
        assert_eq!(descriptor_for(linux.clone(), true, true, false).availability, Availability::Partial);
        assert_eq!(descriptor_for(linux, true, true, true).availability, Availability::Available);
    }

    #[test]
    fn only_static_logical_rulesets_resolve() {
        let root = fixture_root().join("rules");
        let (_, hash) = approved_ruleset_in(&root, "approved-demo").unwrap();
        assert_eq!(hash.len(), 64);
        for name in ["../outside", "/absolute", "..", "unknown", "x/y"] {
            assert!(approved_ruleset_in(&root, name).is_err());
        }
    }

    #[cfg(unix)]
    #[test]
    fn ruleset_symlink_escape_is_denied() {
        let temp = tempfile::tempdir().unwrap();
        let outside = tempfile::tempdir().unwrap();
        fs::write(outside.path().join("escape.yar"), b"rule safe { condition: true }").unwrap();
        std::os::unix::fs::symlink(outside.path().join("escape.yar"), temp.path().join("escape.yar")).unwrap();
        let error = approved_ruleset_in(temp.path(), "escape").unwrap_err();
        assert!(matches!(error, AgentError::Rejected { code: "RULESET_NOT_APPROVED", .. }));
    }

    #[test]
    fn malformed_output_is_rejected() {
        let path = Path::new("/approved/match.txt");
        assert!(parse_yara_output("rule /other/file\n", path).is_err());
        assert!(parse_yara_output("", path).unwrap().is_empty());
    }

    #[test]
    fn malformed_rule_reports_explicit_issue_when_yara_is_installed() {
        if !command_available("yara") { return; }
        let temp = tempfile::tempdir().unwrap();
        let bad = temp.path().join("bad.yar");
        fs::write(&bad, b"rule invalid {").unwrap();
        let target = fixture_root().join("evidence/clean.txt");
        let error = run_yara(&bad, &target).unwrap_err();
        assert!(matches!(error, AgentError::Rejected { code: "YARA_RULE_FAILED", .. }));
    }

    #[test]
    fn approved_root_is_enforced_before_scan() {
        let root = fixture_root();
        let rules = root.join("rules/approved-demo.yar");
        let evidence = root.join("evidence");
        let mut context = CollectorContext::new(ResourceBudget::default(), &[evidence.to_string_lossy().into_owned()]);
        let mut request = CollectorRequest::new("yara");
        request.path = Some(root.join("rules").to_string_lossy().into_owned());
        request.limit = 128;
        let error = scan(&request, &mut context, "approved-demo", &rules, "x").unwrap_err();
        assert!(matches!(error, AgentError::Rejected { code: "PATH_DENIED", .. }));
        request.path = Some(evidence.join("../rules").to_string_lossy().into_owned());
        let error = scan(&request, &mut context, "approved-demo", &rules, "x").unwrap_err();
        assert!(matches!(error, AgentError::Rejected { code: "PATH_DENIED", .. }));
    }

    #[test]
    fn real_yara_matches_only_the_benign_marker_when_installed() {
        if !command_available("yara") { return; }
        let root = fixture_root();
        let rules = root.join("rules/approved-demo.yar");
        let evidence = root.join("evidence");
        let mut request = CollectorRequest::new("yara");
        request.path = Some(evidence.to_string_lossy().into_owned());
        request.recursive = true;
        request.limit = 128;
        let mut context = CollectorContext::new(ResourceBudget::default(), &[evidence.to_string_lossy().into_owned()]);
        let result = scan(&request, &mut context, "approved-demo", &rules, "rule-hash").unwrap();
        assert_eq!(result.records.len(), 1);
        assert_eq!(result.metadata.as_ref().unwrap()["files_scanned"], 2);
        assert_eq!(result.metadata.as_ref().unwrap()["matches"], 1);
        assert_eq!(result.records[0]["rule"], "approved_demo_marker");
        assert!(result.records[0]["path"].as_str().unwrap().ends_with("match.txt"));
        assert_eq!(context.files_examined, 2);

        request.path = Some(evidence.join("clean.txt").to_string_lossy().into_owned());
        let mut context = CollectorContext::new(ResourceBudget::default(), &[evidence.to_string_lossy().into_owned()]);
        let clean = scan(&request, &mut context, "approved-demo", &rules, "rule-hash").unwrap();
        assert_eq!(clean.availability, Availability::Available);
        assert!(clean.records.is_empty());
        assert_eq!(clean.metadata.as_ref().unwrap()["matches"], 0);
    }

    #[test]
    fn byte_and_file_limits_reject_before_unbounded_scanning() {
        let root = fixture_root();
        let rules = root.join("rules/approved-demo.yar");
        let evidence = root.join("evidence");
        let mut request = CollectorRequest::new("yara");
        request.path = Some(evidence.join("match.txt").to_string_lossy().into_owned());
        request.limit = 128;
        let budget = ResourceBudget { max_file_bytes: 1, ..ResourceBudget::default() };
        let mut context = CollectorContext::new(budget, &[evidence.to_string_lossy().into_owned()]);
        let error = scan(&request, &mut context, "approved-demo", &rules, "x").unwrap_err();
        assert!(matches!(error, AgentError::Rejected { code: "FILE_BYTES_EXCEEDED", .. }));
        let budget = ResourceBudget { max_file_count: 0, ..ResourceBudget::default() };
        let mut context = CollectorContext::new(budget, &[evidence.to_string_lossy().into_owned()]);
        let error = scan(&request, &mut context, "approved-demo", &rules, "x").unwrap_err();
        assert!(matches!(error, AgentError::Rejected { code: "FILE_COUNT_EXCEEDED", .. }));
    }
}
