#Requires -Version 5.1
<#
.SYNOPSIS
    Connect a native Windows host to a JOCKY control plane as a real endpoint.

.DESCRIPTION
    Automates the existing JOCKY agent enrollment flow on Windows:

        1. create (or reuse) a protected state directory
        2. obtain the trusted control-plane CA certificate
        3. read the one-time enrollment token from a file
        4. generate a P-256 transport key and PKCS#10 request with the
           platform crypto provider (no OpenSSL installation required)
        5. run the existing `jocky-agent init`, `enroll` and `connect` commands

    Certificate verification is never relaxed: the CA is written into the agent
    state and the agent performs the real mTLS handshake with the control plane.
    The script embeds no credentials and never prints the enrollment token.

.PARAMETER Server
    Control-plane gRPC endpoint the agent connects to, e.g.
    https://control-plane.example.internal:15051 . Must be https://.

.PARAMETER EnrollmentServer
    Enrollment gRPC endpoint. Defaults to -Server.

.PARAMETER TokenFile
    Path to the file holding the one-time enrollment token. The token never
    appears on the command line.

.PARAMETER CaFile
    Path to the control-plane CA certificate in PEM form.

.PARAMETER CaUrl
    HTTPS URL of the control-plane CA certificate. Used only when -CaFile is
    absent; the download uses normal certificate validation.

.PARAMETER StateDir
    Agent state directory. Defaults to %ProgramData%\JOCKY.

.PARAMETER OrganizationId
    Local organization label bound into the endpoint identity.

.PARAMETER AgentPath
    jocky-agent.exe to run. Defaults to the copy next to this script, then the
    state directory, then PATH.

.PARAMETER WorkerPath
    jocky-worker.exe used for LLVM memory execution. Defaults to the copy next
    to the agent. A missing worker does not block enrollment or heartbeat; jobs
    that need compiler-artifact execution are refused by the agent until it is
    installed.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\connect-jocky.ps1 `
        -Server https://10.0.0.5:15051 `
        -CaFile .\control-plane-ca.pem `
        -TokenFile .\enrollment.token
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Server,
    [string] $EnrollmentServer,
    [Parameter(Mandatory = $true)][string] $TokenFile,
    [string] $CaFile,
    [string] $CaUrl,
    [string] $StateDir = (Join-Path $env:ProgramData 'JOCKY'),
    [string] $OrganizationId = 'local-development',
    [string] $AgentPath,
    [string] $WorkerPath,
    [switch] $EnrollOnly
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Write-Step {
    param([Parameter(Mandatory = $true)][string] $Message)
    Write-Host "==> $Message"
}

function Stop-Bootstrap {
    param([Parameter(Mandatory = $true)][string] $Message)
    Write-Host ''
    Write-Host "JOCKY enrollment failed: $Message" -ForegroundColor Red
    Write-Host 'No endpoint was reported online. Resolve the cause and run this script again.'
    exit 1
}

function Protect-Path {
    # Remove inherited access and grant only SYSTEM and Administrators. The
    # transport private key, evidence identity key and spool all live here.
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [switch] $Container
    )
    $acl = Get-Acl -Path $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) {
        [void]$acl.RemoveAccessRule($rule)
    }
    $inheritance = if ($Container) { 'ContainerInherit, ObjectInherit' } else { 'None' }
    foreach ($identity in @('NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators')) {
        $rule = New-Object -TypeName System.Security.AccessControl.FileSystemAccessRule `
            -ArgumentList @($identity, 'FullControl', $inheritance, 'None', 'Allow')
        [void]$acl.AddAccessRule($rule)
    }
    Set-Acl -Path $Path -AclObject $acl
}

function Write-PemFile {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][byte[]] $Bytes
    )
    $body = [System.Convert]::ToBase64String($Bytes)
    $lines = for ($offset = 0; $offset -lt $body.Length; $offset += 64) {
        $body.Substring($offset, [Math]::Min(64, $body.Length - $offset))
    }
    $text = "-----BEGIN $Label-----`n" + ($lines -join "`n") + "`n-----END $Label-----`n"
    [System.IO.File]::WriteAllText($Path, $text, [System.Text.UTF8Encoding]::new($false))
}

function New-TransportMaterial {
    # Equivalent to the OpenSSL request the Linux enrollment path builds: an
    # ECDSA P-256 key and a SHA-256 PKCS#10 request for CN=jocky-agent.
    param(
        [Parameter(Mandatory = $true)][string] $KeyPath,
        [Parameter(Mandatory = $true)][string] $CsrPath
    )
    $creation = [System.Security.Cryptography.CngKeyCreationParameters]::new()
    $creation.KeyCreationOptions = [System.Security.Cryptography.CngKeyCreationOptions]::None
    $creation.Provider = [System.Security.Cryptography.CngProvider]::MicrosoftSoftwareKeyStorageProvider
    $creation.ExportPolicy = (
        [System.Security.Cryptography.CngExportPolicies]::AllowExport -bor
        [System.Security.Cryptography.CngExportPolicies]::AllowPlaintextExport)
    $cng = [System.Security.Cryptography.CngKey]::Create(
        [System.Security.Cryptography.CngAlgorithm]::ECDsaP256, $null, $creation)
    try {
        $ecdsa = [System.Security.Cryptography.ECDsaCng]::new($cng)
        try {
            $request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
                'CN=jocky-agent', $ecdsa, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
            $csr = $request.CreateSigningRequest()
        }
        finally { $ecdsa.Dispose() }
        $key = $cng.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob)
    }
    finally { $cng.Dispose() }
    Write-PemFile -Path $KeyPath -Label 'PRIVATE KEY' -Bytes $key
    Write-PemFile -Path $CsrPath -Label 'CERTIFICATE REQUEST' -Bytes $csr
}

function Resolve-AgentPath {
    param([string] $Explicit)
    if ($Explicit) { return $Explicit }
    foreach ($candidate in @(
            (Join-Path $PSScriptRoot 'jocky-agent.exe'),
            (Join-Path $StateDir 'jocky-agent.exe'))) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    $found = Get-Command 'jocky-agent' -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    return $null
}

function Invoke-Agent {
    param([Parameter(Mandatory = $true)][string[]] $Arguments)
    & $agent '--state-dir' $StateDir @Arguments
    if ($LASTEXITCODE -ne 0) {
        Stop-Bootstrap "jocky-agent $($Arguments[0]) exited with code $LASTEXITCODE. See the JSON error above."
    }
}

if ($Server -notmatch '^https://') {
    Stop-Bootstrap '-Server must be an https:// URL; JOCKY does not use plaintext transport.'
}
$principal = [System.Security.Principal.WindowsPrincipal]::new(
    [System.Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Stop-Bootstrap 'run this script from an elevated PowerShell session; machine-wide enrollment requires it.'
}
if ([string]::IsNullOrWhiteSpace($EnrollmentServer)) { $EnrollmentServer = $Server }
elseif ($EnrollmentServer -notmatch '^https://') {
    Stop-Bootstrap '-EnrollmentServer must be an https:// URL.'
}
if (-not (Test-Path -LiteralPath $TokenFile -PathType Leaf)) {
    Stop-Bootstrap "enrollment token file not found: $TokenFile"
}
$token = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($token)) {
    Stop-Bootstrap "enrollment token file is empty: $TokenFile"
}
Remove-Variable token

$agent = Resolve-AgentPath -Explicit $AgentPath
if (-not $agent -or -not (Test-Path -LiteralPath $agent -PathType Leaf)) {
    Stop-Bootstrap 'jocky-agent.exe was not found. Pass -AgentPath or place it next to this script.'
}
if (-not $WorkerPath) {
    $WorkerPath = Join-Path (Split-Path -Parent $agent) 'jocky-worker.exe'
}

Write-Step "Preparing state directory $StateDir"
if (-not (Test-Path -LiteralPath $StateDir)) {
    New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
}
Protect-Path -Path $StateDir -Container

$staging = Join-Path $StateDir 'bootstrap'
$configPath = Join-Path $StateDir 'config.json'
$bindingPath = Join-Path $StateDir 'remote.json'

try {
    if (Test-Path -LiteralPath $bindingPath) {
        Write-Step 'Endpoint is already enrolled; reusing the existing identity and state'
    }

    if (-not (Test-Path -LiteralPath $configPath)) {
        Write-Step 'Initializing the local endpoint identity and encrypted spool'
        Invoke-Agent -Arguments @('init', '--organization-id', $OrganizationId)
    }
    else {
        Write-Step 'Reusing the existing endpoint identity'
    }

    if (-not (Test-Path -LiteralPath $bindingPath)) {
        Write-Step 'Resolving the trusted control-plane CA certificate'
        $caPath = $null
        if (-not [string]::IsNullOrWhiteSpace($CaFile)) {
            if (-not (Test-Path -LiteralPath $CaFile -PathType Leaf)) {
                Stop-Bootstrap "CA certificate not found: $CaFile"
            }
            $caPath = (Resolve-Path -LiteralPath $CaFile).Path
        }
        elseif (-not [string]::IsNullOrWhiteSpace($CaUrl)) {
            if ($CaUrl -notmatch '^https://') {
                Stop-Bootstrap '-CaUrl must be an https:// URL.'
            }
            $caPath = Join-Path $staging 'control-plane-ca.pem'
            New-Item -ItemType Directory -Path $staging -Force | Out-Null
            Protect-Path -Path $staging -Container
            Invoke-WebRequest -Uri $CaUrl -OutFile $caPath -UseBasicParsing
        }
        else {
            Stop-Bootstrap 'Supply the control-plane CA with -CaFile or -CaUrl.'
        }
        $caText = Get-Content -LiteralPath $caPath -Raw
        if ($caText -notmatch '-----BEGIN CERTIFICATE-----') {
            Stop-Bootstrap "the supplied CA is not a PEM certificate: $caPath"
        }

        Write-Step 'Generating the P-256 transport key and certificate request'
        New-Item -ItemType Directory -Path $staging -Force | Out-Null
        Protect-Path -Path $staging -Container
        $keyPath = Join-Path $staging 'transport.key'
        $csrPath = Join-Path $staging 'transport.csr'
        New-TransportMaterial -KeyPath $keyPath -CsrPath $csrPath
        Protect-Path -Path $keyPath
        Protect-Path -Path $csrPath

        Write-Step 'Enrolling over mTLS with the control plane'
        Invoke-Agent -Arguments @(
            'enroll',
            '--enrollment-server', $EnrollmentServer,
            '--server', $Server,
            '--ca', $caPath,
            '--token-file', (Resolve-Path -LiteralPath $TokenFile).Path,
            '--worker', $WorkerPath,
            '--transport-key', $keyPath,
            '--csr', $csrPath)
    }

    if (Test-Path -LiteralPath $WorkerPath -PathType Leaf) {
        Write-Step "LLVM execution worker: $WorkerPath"
    }
    else {
        Write-Step "LLVM execution worker is not installed at $WorkerPath"
        Write-Host '    The endpoint will enroll, heartbeat and appear ONLINE.'
        Write-Host '    Compiler-artifact jobs are refused until the worker is installed.'
    }

    if ($EnrollOnly) {
        Write-Step 'Enrollment complete; the JOCKY bootstrap service will supervise the agent connection'
        return
    }

    Write-Step 'Connecting; the control plane marks this endpoint ONLINE only after an authenticated heartbeat'
    Write-Host '    Leave this window open. Press Ctrl+C to stop the agent.'
    Invoke-Agent -Arguments @('connect')
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    }
}
