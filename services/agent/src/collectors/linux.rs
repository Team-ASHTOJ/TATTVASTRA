use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::net::{Ipv4Addr, Ipv6Addr};
use std::path::Path;

use chrono::{Duration, Utc};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use super::{output, run_fixed, CollectorContext};
use crate::error::{AgentError, Result};
use crate::model::{CollectorOutput, CollectorRequest};

pub(super) fn collect(
    request: &CollectorRequest,
    context: &mut CollectorContext,
) -> Result<CollectorOutput> {
    let records = match request.collector.as_str() {
        "system" => system(context)?,
        "users" => users(context, request.limit)?,
        "sessions" => sessions(request.limit)?,
        "processes" => processes(context, request)?,
        "interfaces" => interfaces(context, request.limit)?,
        "connections" => connections(context, request.limit)?,
        "routes" => routes(context, request.limit)?,
        "services" => services(request.limit)?,
        "startup" => startup(context, request.limit)?,
        "events" => events(request.limit)?,
        "software" => software(request.limit)?,
        "drivers" | "modules" => modules(context, request.limit)?,
        other => {
            return Ok(CollectorOutput::unavailable(
                other,
                "COLLECTOR_UNSUPPORTED",
                "collector has no Linux adapter",
            ));
        }
    };
    Ok(output(&request.collector, records))
}

fn system(context: &mut CollectorContext) -> Result<Vec<Value>> {
    let hostname = read_trimmed(context, Path::new("/etc/hostname"), 4_096).unwrap_or_default();
    let kernel = read_trimmed(context, Path::new("/proc/sys/kernel/osrelease"), 4_096).ok();
    let uptime_seconds = read_trimmed(context, Path::new("/proc/uptime"), 4_096)
        .ok()
        .and_then(|value| value.split_whitespace().next()?.parse::<f64>().ok());
    let memory_total = read_trimmed(context, Path::new("/proc/meminfo"), 128 * 1024)
        .ok()
        .and_then(|value| {
            value.lines().find_map(|line| {
                let kb = line.strip_prefix("MemTotal:")?.trim();
                kb.split_whitespace().next()?.parse::<u64>().ok()
            })
        })
        .map(|kb| kb.saturating_mul(1024));
    let os = read_trimmed(context, Path::new("/etc/os-release"), 64 * 1024)
        .ok()
        .and_then(|value| {
            value.lines().find_map(|line| {
                line.strip_prefix("PRETTY_NAME=")
                    .map(|name| name.trim_matches('"').to_owned())
            })
        })
        .unwrap_or_else(|| "Linux".to_owned());
    let boot_time = uptime_seconds.and_then(|seconds| {
        Duration::try_milliseconds((seconds * 1_000.0) as i64)
            .map(|uptime| (Utc::now() - uptime).to_rfc3339())
    });
    Ok(vec![json!({
        "hostname": hostname,
        "os": os,
        "arch": std::env::consts::ARCH,
        "kernel": kernel,
        "boot_time": boot_time,
        "uptime_seconds": uptime_seconds,
        "memory_total": memory_total,
        "cpu_count": std::thread::available_parallelism().map(usize::from).ok(),
    })])
}

fn users(context: &mut CollectorContext, limit: usize) -> Result<Vec<Value>> {
    let active = run_fixed("who", &[], 1_000_000)
        .unwrap_or_default()
        .lines()
        .filter_map(|line| line.split_whitespace().next().map(str::to_owned))
        .collect::<std::collections::BTreeSet<_>>();
    let passwd = read_trimmed(context, Path::new("/etc/passwd"), 4_000_000)?;
    Ok(passwd
        .lines()
        .take(limit)
        .filter_map(|line| {
            let fields = line.split(':').collect::<Vec<_>>();
            (fields.len() >= 7).then(|| {
                json!({
                    "name": fields[0],
                    "uid": fields[2],
                    "home": fields[5],
                    "shell": fields[6],
                    "active": active.contains(fields[0]),
                })
            })
        })
        .collect())
}

fn sessions(limit: usize) -> Result<Vec<Value>> {
    let text = run_fixed("who", &[], 1_000_000)?;
    Ok(text
        .lines()
        .take(limit)
        .enumerate()
        .map(|(index, line)| {
            let fields = line.split_whitespace().collect::<Vec<_>>();
            json!({
                "id": format!("session-{index}"),
                "user": fields.first().copied().unwrap_or_default(),
                "terminal": fields.get(1).copied(),
                "started_at_raw": fields.get(2..4).map(|value| value.join(" ")),
                "remote": fields.get(4).map(|value| value.trim_matches(['(', ')'])),
            })
        })
        .collect())
}

fn processes(context: &mut CollectorContext, request: &CollectorRequest) -> Result<Vec<Value>> {
    let uid_names = uid_names(context).unwrap_or_default();
    let boot_epoch = boot_epoch(context);
    let clock_ticks = clock_ticks();
    let mut pids = fs::read_dir("/proc")?
        .filter_map(std::result::Result::ok)
        .filter_map(|entry| {
            let text = entry.file_name().to_string_lossy().into_owned();
            text.parse::<u32>().ok().map(|pid| (pid, entry.path()))
        })
        .collect::<Vec<_>>();
    pids.sort_by_key(|item| item.0);
    let mut records = Vec::new();
    for (pid, path) in pids.into_iter().take(request.limit) {
        let status = match read_trimmed(context, &path.join("status"), 256 * 1024) {
            Ok(value) => parse_status(&value),
            Err(_) => continue,
        };
        let name = status
            .get("Name")
            .cloned()
            .unwrap_or_else(|| pid.to_string());
        let executable = fs::read_link(path.join("exe"))
            .ok()
            .map(|value| value.to_string_lossy().into_owned());
        let sha256 = if request.hash {
            executable
                .as_deref()
                .and_then(|value| hash_bounded(Path::new(value), context).ok())
        } else {
            None
        };
        let uid = status
            .get("Uid")
            .and_then(|value| value.split_whitespace().next())
            .map(str::to_owned);
        let start_time = process_start_time(context, &path, boot_epoch, clock_ticks);
        records.push(json!({
            "pid": pid,
            "parent_pid": status.get("PPid").and_then(|value| value.parse::<u32>().ok()),
            "name": name,
            "path": executable,
            "user": uid.as_ref().and_then(|value| uid_names.get(value)),
            "uid": uid,
            "start_time": start_time,
            "cpu_percent": Value::Null,
            "memory_bytes": status.get("VmRSS").and_then(|value| value.split_whitespace().next()).and_then(|value| value.parse::<u64>().ok()).map(|kb| kb.saturating_mul(1024)),
            "sha256": sha256,
            "signed": Value::Null,
            "signature_status": "UNAVAILABLE_ON_LINUX",
        }));
    }
    Ok(records)
}

fn interfaces(context: &mut CollectorContext, limit: usize) -> Result<Vec<Value>> {
    let mut names = fs::read_dir("/sys/class/net")?
        .filter_map(std::result::Result::ok)
        .map(|entry| entry.file_name().to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    names.sort();
    let mut addresses = interface_addresses();
    let mut records = Vec::new();
    for name in names.into_iter().take(limit) {
        let base = Path::new("/sys/class/net").join(&name);
        let mac = read_trimmed(context, &base.join("address"), 4_096).ok();
        let mtu = read_trimmed(context, &base.join("mtu"), 4_096)
            .ok()
            .and_then(|value| value.parse::<u32>().ok());
        let state = read_trimmed(context, &base.join("operstate"), 4_096).ok();
        let up = state.as_deref().and_then(|value| match value {
            "up" => Some(true),
            "down" => Some(false),
            _ => None,
        });
        let assigned = addresses.remove(&name).unwrap_or_default();
        if assigned.is_empty() {
            records.push(json!({
                "name": name,
                "address": Value::Null,
                "prefix_length": Value::Null,
                "family": Value::Null,
                "address_availability": "UNAVAILABLE",
                "mac": mac,
                "mtu": mtu,
                "up": up,
                "state": state,
            }));
        } else {
            for address in assigned {
                records.push(json!({
                    "name": name,
                    "address": address.get("address"),
                    "prefix_length": address.get("prefix_length"),
                    "family": address.get("family"),
                    "address_availability": "AVAILABLE",
                    "mac": mac,
                    "mtu": mtu,
                    "up": up,
                    "state": state,
                }));
            }
        }
    }
    records.truncate(limit);
    Ok(records)
}

fn connections(context: &mut CollectorContext, limit: usize) -> Result<Vec<Value>> {
    let boot_epoch = boot_epoch(context);
    let clock_ticks = clock_ticks();
    let inode_processes = socket_owners(context, limit.saturating_mul(4), boot_epoch, clock_ticks);
    let mut records = Vec::new();
    for (path, protocol, ipv6) in [
        ("/proc/net/tcp", "tcp", false),
        ("/proc/net/tcp6", "tcp", true),
        ("/proc/net/udp", "udp", false),
        ("/proc/net/udp6", "udp", true),
    ] {
        let Ok(text) = read_trimmed(context, Path::new(path), 16_000_000) else {
            continue;
        };
        for line in text.lines().skip(1) {
            if records.len() >= limit {
                return Ok(records);
            }
            let fields = line.split_whitespace().collect::<Vec<_>>();
            if fields.len() < 10 {
                continue;
            }
            let Some((local, local_port)) = parse_socket(fields[1], ipv6) else {
                continue;
            };
            let Some((remote, remote_port)) = parse_socket(fields[2], ipv6) else {
                continue;
            };
            let inode = fields.get(9).copied().unwrap_or_default();
            let process = inode_processes.get(inode);
            records.push(json!({
                "pid": process.map(|value| value.pid),
                "process_start_time": process.and_then(|value| value.start_time.as_deref()),
                "protocol": protocol,
                "local": local,
                "local_port": local_port,
                "remote": remote,
                "remote_port": remote_port,
                "state": socket_state(protocol, fields[3]),
                "inode": inode,
            }));
        }
    }
    Ok(records)
}

fn routes(context: &mut CollectorContext, limit: usize) -> Result<Vec<Value>> {
    let text = read_trimmed(context, Path::new("/proc/net/route"), 4_000_000)?;
    Ok(text
        .lines()
        .skip(1)
        .take(limit)
        .filter_map(|line| {
            let fields = line.split_whitespace().collect::<Vec<_>>();
            if fields.len() < 8 {
                return None;
            }
            Some(json!({
                "destination": decode_ipv4_hex(fields[1]),
                "prefix_length": u32::from_str_radix(fields[7], 16).ok().map(u32::count_ones),
                "gateway": decode_ipv4_hex(fields[2]),
                "interface": fields[0],
                "metric": fields.get(6).and_then(|value| value.parse::<u32>().ok()),
            }))
        })
        .collect())
}

fn services(limit: usize) -> Result<Vec<Value>> {
    let text = run_fixed(
        "systemctl",
        &[
            "list-units",
            "--type=service",
            "--all",
            "--no-legend",
            "--no-pager",
            "--plain",
        ],
        8_000_000,
    )?;
    Ok(text
        .lines()
        .take(limit)
        .filter_map(|line| {
            let fields = line.split_whitespace().collect::<Vec<_>>();
            (fields.len() >= 4).then(|| {
                json!({
                    "name": fields[0],
                    "state": fields[3],
                    "load_state": fields[1],
                    "active_state": fields[2],
                    "path": Value::Null,
                    "pid": Value::Null,
                    "start_type": Value::Null,
                })
            })
        })
        .collect())
}

fn startup(context: &mut CollectorContext, limit: usize) -> Result<Vec<Value>> {
    let mut records = Vec::new();
    for directory in [
        "/etc/systemd/system",
        "/etc/cron.d",
        "/etc/cron.daily",
        "/etc/xdg/autostart",
    ] {
        let Ok(entries) = fs::read_dir(directory) else {
            continue;
        };
        let mut paths = entries
            .filter_map(std::result::Result::ok)
            .map(|entry| entry.path())
            .collect::<Vec<_>>();
        paths.sort();
        for path in paths {
            if records.len() >= limit {
                return Ok(records);
            }
            context.charge_file()?;
            records.push(json!({
                "name": path.file_name().map(|value| value.to_string_lossy().into_owned()).unwrap_or_default(),
                "path": path.to_string_lossy(),
                "user": Value::Null,
                "source": directory,
            }));
        }
    }
    Ok(records)
}

fn events(limit: usize) -> Result<Vec<Value>> {
    let lines = run_fixed(
        "journalctl",
        &[
            "--no-pager",
            "--output=json",
            "-n",
            &limit.min(10_000).to_string(),
        ],
        16_000_000,
    )?;
    Ok(lines
        .lines()
        .take(limit)
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .enumerate()
        .map(|(index, entry)| {
            json!({
                "event_id": format!("journal-{index}"),
                "timestamp": journal_timestamp(&entry),
                "source": entry.get("SYSLOG_IDENTIFIER").or_else(|| entry.get("_COMM")),
                "channel": "journal",
                "message": entry.get("MESSAGE"),
                "severity": entry.get("PRIORITY"),
                "pid": entry.get("_PID"),
            })
        })
        .collect())
}

fn journal_timestamp(entry: &Value) -> Option<String> {
    let micros = entry
        .get("_SOURCE_REALTIME_TIMESTAMP")
        .or_else(|| entry.get("__REALTIME_TIMESTAMP"))?
        .as_str()?
        .parse::<i64>()
        .ok()?;
    let seconds = micros.div_euclid(1_000_000);
    let nanoseconds = micros.rem_euclid(1_000_000) as u32 * 1_000;
    chrono::DateTime::<Utc>::from_timestamp(seconds, nanoseconds).map(|value| value.to_rfc3339())
}

fn software(limit: usize) -> Result<Vec<Value>> {
    let text = run_fixed(
        "dpkg-query",
        &["-W", "-f=${binary:Package}\t${Version}\t${Maintainer}\n"],
        16_000_000,
    )?;
    Ok(text
        .lines()
        .take(limit)
        .map(|line| {
            let mut fields = line.splitn(3, '\t');
            json!({
                "name": fields.next().unwrap_or_default(),
                "version": fields.next().unwrap_or_default(),
                "vendor": fields.next(),
            })
        })
        .collect())
}

fn modules(context: &mut CollectorContext, limit: usize) -> Result<Vec<Value>> {
    let text = read_trimmed(context, Path::new("/proc/modules"), 8_000_000)?;
    Ok(text
        .lines()
        .take(limit)
        .map(|line| {
            let fields = line.split_whitespace().collect::<Vec<_>>();
            let name = fields.first().copied().unwrap_or_default();
            let version_path = Path::new("/sys/module").join(name).join("version");
            json!({
                "name": name,
                "version": read_trimmed(context, &version_path, 4_096).ok(),
                "path": format!("/sys/module/{name}"),
                "size": fields.get(1).and_then(|value| value.parse::<u64>().ok()),
                "sha256": Value::Null,
                "signed": Value::Null,
                "signature_status": "UNAVAILABLE",
            })
        })
        .collect())
}

fn read_trimmed(context: &mut CollectorContext, path: &Path, max: usize) -> Result<String> {
    let bytes = fs::read(path)?;
    if bytes.len() > max {
        return Err(AgentError::rejected(
            "SOURCE_TOO_LARGE",
            format!("{} exceeded its collector bound", path.display()),
        ));
    }
    context.charge_bytes(bytes.len() as u64)?;
    String::from_utf8(bytes)
        .map(|value| value.trim().to_owned())
        .map_err(|_| AgentError::rejected("SOURCE_ENCODING", "system source was not UTF-8"))
}

fn parse_status(text: &str) -> BTreeMap<String, String> {
    text.lines()
        .filter_map(|line| {
            let (key, value) = line.split_once(':')?;
            Some((key.to_owned(), value.trim().to_owned()))
        })
        .collect()
}

fn uid_names(context: &mut CollectorContext) -> Result<BTreeMap<String, String>> {
    Ok(read_trimmed(context, Path::new("/etc/passwd"), 4_000_000)?
        .lines()
        .filter_map(|line| {
            let fields = line.split(':').collect::<Vec<_>>();
            (fields.len() >= 3).then(|| (fields[2].to_owned(), fields[0].to_owned()))
        })
        .collect())
}

fn hash_bounded(path: &Path, context: &mut CollectorContext) -> Result<String> {
    let bytes = fs::read(path)?;
    context.charge_bytes(bytes.len() as u64)?;
    Ok(hex::encode(Sha256::digest(bytes)))
}

#[derive(Clone)]
struct ProcessIdentity {
    pid: u32,
    start_time: Option<String>,
}

fn socket_owners(
    context: &mut CollectorContext,
    max_processes: usize,
    boot_epoch: Option<i64>,
    clock_ticks: Option<u64>,
) -> HashMap<String, ProcessIdentity> {
    let mut owners = HashMap::new();
    let Ok(entries) = fs::read_dir("/proc") else {
        return owners;
    };
    let mut pids = entries
        .filter_map(std::result::Result::ok)
        .filter_map(|entry| {
            entry
                .file_name()
                .to_string_lossy()
                .parse::<u32>()
                .ok()
                .map(|pid| (pid, entry.path()))
        })
        .collect::<Vec<_>>();
    pids.sort_by_key(|item| item.0);
    for (pid, path) in pids.into_iter().take(max_processes.max(1)) {
        let start_time = process_start_time(context, &path, boot_epoch, clock_ticks);
        let Ok(descriptors) = fs::read_dir(path.join("fd")) else {
            continue;
        };
        for descriptor in descriptors.filter_map(std::result::Result::ok) {
            let Ok(target) = fs::read_link(descriptor.path()) else {
                continue;
            };
            let text = target.to_string_lossy();
            if let Some(inode) = text
                .strip_prefix("socket:[")
                .and_then(|value| value.strip_suffix(']'))
            {
                owners
                    .entry(inode.to_owned())
                    .or_insert_with(|| ProcessIdentity {
                        pid,
                        start_time: start_time.clone(),
                    });
            }
        }
    }
    owners
}

fn boot_epoch(context: &mut CollectorContext) -> Option<i64> {
    read_trimmed(context, Path::new("/proc/stat"), 4_000_000)
        .ok()?
        .lines()
        .find_map(|line| line.strip_prefix("btime ")?.parse::<i64>().ok())
}

fn clock_ticks() -> Option<u64> {
    run_fixed("getconf", &["CLK_TCK"], 4_096)
        .ok()?
        .trim()
        .parse::<u64>()
        .ok()
        .filter(|value| *value != 0)
}

fn process_start_time(
    context: &mut CollectorContext,
    process_path: &Path,
    boot_epoch: Option<i64>,
    clock_ticks: Option<u64>,
) -> Option<String> {
    let stat = read_trimmed(context, &process_path.join("stat"), 256 * 1024).ok()?;
    let ticks = stat
        .rsplit_once(')')?
        .1
        .split_whitespace()
        .nth(19)?
        .parse::<u64>()
        .ok()?;
    let seconds = boot_epoch?.checked_add((ticks / clock_ticks?) as i64)?;
    chrono::DateTime::<Utc>::from_timestamp(seconds, 0).map(|value| value.to_rfc3339())
}

fn interface_addresses() -> HashMap<String, Vec<Value>> {
    let Ok(text) = run_fixed("ip", &["-j", "address", "show"], 8_000_000) else {
        return HashMap::new();
    };
    let Ok(Value::Array(interfaces)) = serde_json::from_str::<Value>(&text) else {
        return HashMap::new();
    };
    let mut addresses = HashMap::<String, Vec<Value>>::new();
    for interface in interfaces {
        let Some(name) = interface.get("ifname").and_then(Value::as_str) else {
            continue;
        };
        let Some(items) = interface.get("addr_info").and_then(Value::as_array) else {
            continue;
        };
        for item in items {
            let Some(address) = item.get("local").and_then(Value::as_str) else {
                continue;
            };
            addresses.entry(name.to_owned()).or_default().push(json!({
                "address": address,
                "prefix_length": item.get("prefixlen"),
                "family": item.get("family"),
            }));
        }
    }
    addresses
}

fn parse_socket(value: &str, ipv6: bool) -> Option<(String, u16)> {
    let (address, port) = value.split_once(':')?;
    let port = u16::from_str_radix(port, 16).ok()?;
    if ipv6 {
        let bytes = hex::decode(address).ok()?;
        if bytes.len() != 16 {
            return None;
        }
        let mut normalized = [0_u8; 16];
        for (source, target) in bytes.chunks_exact(4).zip(normalized.chunks_exact_mut(4)) {
            target.copy_from_slice(&[source[3], source[2], source[1], source[0]]);
        }
        Some((Ipv6Addr::from(normalized).to_string(), port))
    } else {
        Some((decode_ipv4_hex(address)?, port))
    }
}

fn decode_ipv4_hex(value: &str) -> Option<String> {
    let number = u32::from_str_radix(value, 16).ok()?;
    Some(Ipv4Addr::from(number.to_le_bytes()).to_string())
}

fn socket_state(protocol: &str, state: &str) -> &'static str {
    if protocol == "udp" {
        return "UNCONN";
    }
    match state {
        "01" => "ESTABLISHED",
        "02" => "SYN_SENT",
        "03" => "SYN_RECV",
        "04" => "FIN_WAIT1",
        "05" => "FIN_WAIT2",
        "06" => "TIME_WAIT",
        "07" => "CLOSE",
        "08" => "CLOSE_WAIT",
        "09" => "LAST_ACK",
        "0A" => "LISTEN",
        "0B" => "CLOSING",
        _ => "UNKNOWN",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn journal_microsecond_timestamp_is_normalized() {
        let entry = json!({"__REALTIME_TIMESTAMP": "1757779200123456"});
        assert_eq!(
            journal_timestamp(&entry).as_deref(),
            Some("2025-09-13T16:00:00.123456+00:00")
        );
    }
}
