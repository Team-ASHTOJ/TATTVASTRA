#Requires -Version 5.1
<#
.SYNOPSIS
    One-time installation of the bounded JOCKY Windows endpoint supervisor.

.DESCRIPTION
    Copies only the signed JOCKY runtime files, protects the bootstrap
    configuration for SYSTEM and Administrators, and registers an automatic
    Windows service. Normal endpoint starts are then controlled from JOCKY.
#>
[CmdletBinding()]
param(
    # Defaults to the bootstrap configuration downloaded from JOCKY and placed
    # beside this script, which is what Install-JOCKY.cmd relies on.
    [string] $Configuration,
    [string] $SourceDirectory = $PSScriptRoot,
    [string] $InstallDirectory = (Join-Path $env:ProgramFiles 'JOCKY'),
    [string] $StateDirectory = (Join-Path $env:ProgramData 'JOCKY')
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$serviceName = 'JockyBootstrap'

if (-not $Configuration) { $Configuration = Join-Path $SourceDirectory 'jocky-bootstrap.json' }
$principal = [System.Security.Principal.WindowsPrincipal]::new(
    [System.Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this one-time installer from an elevated PowerShell session.'
}

function Protect-JockyPath {
    param([Parameter(Mandatory = $true)][string] $Path, [switch] $Container)
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRule($rule) }
    $inheritance = if ($Container) { 'ContainerInherit, ObjectInherit' } else { 'None' }
    foreach ($identity in @('NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators')) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $identity, 'FullControl', $inheritance, 'None', 'Allow')
        [void]$acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

if (-not (Test-Path -LiteralPath $Configuration -PathType Leaf)) {
    throw "Bootstrap configuration not found: $Configuration"
}
$parsed = Get-Content -LiteralPath $Configuration -Raw | ConvertFrom-Json
foreach ($property in @(
        'schema_version', 'api_url', 'control_server', 'enrollment_server',
        'organization_id', 'bootstrap_id', 'bootstrap_secret', 'ca_pem')) {
    if (-not $parsed.PSObject.Properties.Name.Contains($property)) {
        throw "Bootstrap configuration is missing $property"
    }
}
foreach ($url in @($parsed.api_url, $parsed.control_server, $parsed.enrollment_server)) {
    if ($url -notmatch '^https://') { throw 'Every JOCKY service URL must use HTTPS.' }
}

New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null
Protect-JockyPath -Path $InstallDirectory -Container
Protect-JockyPath -Path $StateDirectory -Container

foreach ($name in @('jocky-bootstrap.exe', 'jocky-agent.exe', 'connect-jocky.ps1')) {
    $source = Join-Path $SourceDirectory $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing $source" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $InstallDirectory $name) -Force
}
$worker = Join-Path $SourceDirectory 'jocky-worker.exe'
if (Test-Path -LiteralPath $worker -PathType Leaf) {
    Copy-Item -LiteralPath $worker -Destination (Join-Path $InstallDirectory 'jocky-worker.exe') -Force
}

$configPath = Join-Path $StateDirectory 'bootstrap.json'
Copy-Item -LiteralPath $Configuration -Destination $configPath -Force
Protect-JockyPath -Path $configPath

# The CA travels inside the bootstrap configuration. Installing it beside the
# state keeps it available for troubleshooting without ever weakening the
# verification the supervisor performs.
$caPath = Join-Path $StateDirectory 'control-plane-ca.pem'
Set-Content -LiteralPath $caPath -Value $parsed.ca_pem -Encoding ascii -NoNewline
Protect-JockyPath -Path $caPath

$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existing) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    & sc.exe delete $serviceName | Out-Null
    Start-Sleep -Seconds 1
}
$binary = Join-Path $InstallDirectory 'jocky-bootstrap.exe'
$command = '"{0}" --config "{1}"' -f $binary, $configPath
& sc.exe create $serviceName binPath= $command start= auto obj= LocalSystem `
    DisplayName= 'JOCKY Endpoint Bootstrap' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to register $serviceName" }
& sc.exe description $serviceName `
    'Supervises only the native JOCKY agent enrollment and connection lifecycle.' | Out-Null
Start-Service -Name $serviceName
$state = (Get-Service -Name $serviceName).Status
Write-Host ''
Write-Host "JOCKY Windows endpoint supervisor installed on $env:COMPUTERNAME and $state." -ForegroundColor Green
Write-Host "  control plane : $($parsed.api_url)"
Write-Host "  agent channel : $($parsed.control_server)"
Write-Host "  state         : $StateDirectory (existing identity preserved)"
Write-Host ''
Write-Host 'Next: open JOCKY -> Endpoints -> Connect Endpoint -> Windows, confirm WINDOWS-01 is READY, then Start Windows Endpoint.'
