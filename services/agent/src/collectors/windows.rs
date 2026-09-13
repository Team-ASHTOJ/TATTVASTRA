use serde_json::Value;

use super::{output, run_fixed, CollectorContext};
use crate::error::Result;
use crate::model::{CollectorOutput, CollectorRequest};

pub(super) fn collect(
    request: &CollectorRequest,
    _context: &mut CollectorContext,
) -> Result<CollectorOutput> {
    let script = match request.collector.as_str() {
        "system" => SYSTEM,
        "users" => USERS,
        "sessions" => SESSIONS,
        "processes" => PROCESSES,
        "interfaces" => INTERFACES,
        "connections" => CONNECTIONS,
        "routes" => ROUTES,
        "services" => SERVICES,
        "startup" => STARTUP,
        "events" => EVENTS,
        "software" => SOFTWARE,
        "drivers" | "modules" => DRIVERS,
        other => {
            return Ok(CollectorOutput::unavailable(
                other,
                "COLLECTOR_UNSUPPORTED",
                "collector has no Windows adapter",
            ));
        }
    };
    let command = format!("{script}{SUFFIX}");
    let text = run_fixed(
        "powershell.exe",
        &[
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            &command,
        ],
        32_000_000,
    )?;
    let value: Value = serde_json::from_str(&text)?;
    let mut records = match value {
        Value::Array(records) => records,
        Value::Null => Vec::new(),
        record => vec![record],
    };
    records.truncate(request.limit);
    Ok(output(&request.collector, records))
}

const SUFFIX: &str = " | ConvertTo-Json -Depth 5 -Compress";

const SYSTEM: &str = concat!(
    "$os=Get-CimInstance Win32_OperatingSystem; $cs=Get-CimInstance Win32_ComputerSystem; ",
    "[pscustomobject]@{hostname=$env:COMPUTERNAME;os=$os.Caption;arch=$env:PROCESSOR_ARCHITECTURE;",
    "kernel=$os.Version;boot_time=$os.LastBootUpTime.ToUniversalTime().ToString('o');",
    "uptime_seconds=[int]((Get-Date)-$os.LastBootUpTime).TotalSeconds;",
    "memory_total=[uint64]$cs.TotalPhysicalMemory;cpu_count=[int]$cs.NumberOfLogicalProcessors}"
);

const USERS: &str = concat!(
    "Get-LocalUser | Sort-Object Name | Select-Object @{n='name';e={$_.Name}},",
    "@{n='uid';e={$_.SID.Value}},@{n='home';e={$null}},@{n='active';e={$_.Enabled}}"
);

const SESSIONS: &str = concat!(
    "Get-CimInstance Win32_LogonSession | Sort-Object LogonId | Select-Object ",
    "@{n='id';e={[string]$_.LogonId}},@{n='user';e={$null}},",
    "@{n='started_at';e={if($_.StartTime){$_.StartTime.ToUniversalTime().ToString('o')}else{$null}}},",
    "@{n='remote';e={$null}}"
);

const PROCESSES: &str = concat!(
    "Get-CimInstance Win32_Process | Sort-Object ProcessId | Select-Object ",
    "@{n='pid';e={[uint32]$_.ProcessId}},@{n='parent_pid';e={[uint32]$_.ParentProcessId}},",
    "@{n='name';e={$_.Name}},@{n='path';e={$_.ExecutablePath}},@{n='user';e={$null}},",
    "@{n='start_time';e={if($_.CreationDate){$_.CreationDate.ToUniversalTime().ToString('o')}else{$null}}},",
    "@{n='cpu_percent';e={$null}},@{n='memory_bytes';e={[uint64]$_.WorkingSetSize}},",
    "@{n='sha256';e={$null}},@{n='signed';e={$null}},@{n='signature_status';e={'NOT_REQUESTED'}}"
);

const INTERFACES: &str = concat!(
    "Get-NetIPConfiguration | Sort-Object InterfaceIndex | ForEach-Object { ",
    "$c=$_; if($c.IPv4Address){$c.IPv4Address|ForEach-Object{[pscustomobject]@{name=$c.InterfaceAlias;",
    "address=$_.IPAddress;mac=$c.NetAdapter.LinkLayerAddress;mtu=$null;up=($c.NetAdapter.Status -eq 'Up')}}}",
    "elseif($c.IPv6Address){$c.IPv6Address|Select-Object -First 1|ForEach-Object{[pscustomobject]@{",
    "name=$c.InterfaceAlias;address=$_.IPAddress;mac=$c.NetAdapter.LinkLayerAddress;mtu=$null;",
    "up=($c.NetAdapter.Status -eq 'Up')}}}}"
);

const CONNECTIONS: &str = concat!(
    "$tcp=Get-NetTCPConnection | Select-Object @{n='pid';e={[uint32]$_.OwningProcess}},",
    "@{n='process_start_time';e={$null}},@{n='protocol';e={'tcp'}},@{n='local';e={$_.LocalAddress}},",
    "@{n='local_port';e={[int]$_.LocalPort}},@{n='remote';e={$_.RemoteAddress}},",
    "@{n='remote_port';e={[int]$_.RemotePort}},@{n='state';e={[string]$_.State}};",
    "$udp=Get-NetUDPEndpoint | Select-Object @{n='pid';e={[uint32]$_.OwningProcess}},",
    "@{n='process_start_time';e={$null}},@{n='protocol';e={'udp'}},@{n='local';e={$_.LocalAddress}},",
    "@{n='local_port';e={[int]$_.LocalPort}},@{n='remote';e={$null}},",
    "@{n='remote_port';e={$null}},@{n='state';e={'UNCONN'}}; @($tcp)+@($udp)"
);

const ROUTES: &str = concat!(
    "Get-NetRoute | Sort-Object InterfaceIndex,DestinationPrefix | ForEach-Object {",
    "$p=$_.DestinationPrefix -split '/';[pscustomobject]@{destination=$p[0];",
    "prefix_length=[int]$p[1];gateway=$_.NextHop;interface=[string]$_.InterfaceAlias;",
    "metric=[int]$_.RouteMetric}}"
);

const SERVICES: &str = concat!(
    "Get-CimInstance Win32_Service | Sort-Object Name | Select-Object @{n='name';e={$_.Name}},",
    "@{n='state';e={$_.State}},@{n='path';e={$_.PathName}},@{n='pid';e={[uint32]$_.ProcessId}},",
    "@{n='start_type';e={$_.StartMode}}"
);

const STARTUP: &str = concat!(
    "Get-CimInstance Win32_StartupCommand | Sort-Object Name | Select-Object ",
    "@{n='name';e={$_.Name}},@{n='path';e={$_.Command}},@{n='user';e={$_.User}},",
    "@{n='source';e={$_.Location}}"
);

const EVENTS: &str = concat!(
    "Get-WinEvent -LogName System -MaxEvents 1000 -ErrorAction Stop | Select-Object ",
    "@{n='event_id';e={('{0}-{1}' -f $_.ProviderName,$_.RecordId)}},",
    "@{n='timestamp';e={$_.TimeCreated.ToUniversalTime().ToString('o')}},",
    "@{n='source';e={$_.ProviderName}},@{n='channel';e={$_.LogName}},",
    "@{n='message';e={$_.Message}},@{n='severity';e={[string]$_.LevelDisplayName}},",
    "@{n='pid';e={$_.ProcessId}}"
);

const SOFTWARE: &str = concat!(
    "$paths='HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',",
    "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*';",
    "Get-ItemProperty $paths -ErrorAction SilentlyContinue | Where-Object DisplayName | ",
    "Sort-Object DisplayName,DisplayVersion -Unique | Select-Object @{n='name';e={$_.DisplayName}},",
    "@{n='version';e={$_.DisplayVersion}},@{n='vendor';e={$_.Publisher}}"
);

const DRIVERS: &str = concat!(
    "Get-CimInstance Win32_SystemDriver | Sort-Object Name | Select-Object @{n='name';e={$_.Name}},",
    "@{n='vendor';e={$null}},@{n='version';e={$null}},@{n='path';e={$_.PathName}},",
    "@{n='state';e={$_.State}},@{n='signed';e={$null}},",
    "@{n='signature_status';e={'NOT_REQUESTED'}},@{n='sha256';e={$null}}"
);
