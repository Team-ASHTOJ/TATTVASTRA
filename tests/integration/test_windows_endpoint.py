"""Static acceptance for the native Windows endpoint connection path.

These checks are deliberately static: the repository has no Windows host in
CI, so they assert that the shipped bootstrap drives the *existing* enrollment
flow, keeps secrets in files, and never weakens certificate verification. The
Windows CI job additionally parses the script with the real PowerShell parser.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts/windows/connect-jocky.ps1"
WORKFLOW = ROOT / ".github/workflows/ci.yml"

# Constructs that would disable or weaken TLS verification. JOCKY enrolls with
# the real control-plane CA, so none of these may appear in the bootstrap.
TLS_WEAKENING = (
    "SkipCertificateCheck",
    "ServerCertificateValidationCallback",
    "TrustAllCerts",
    "RemoteSigned",
    "AllowUntrusted",
    "CertificateValidationCallback",
    "SecurityProtocolType]::Ssl3",
    "SecurityProtocolType]::Tls",
)


def bootstrap() -> str:
    assert BOOTSTRAP.is_file(), f"missing Windows bootstrap: {BOOTSTRAP}"
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert text.strip(), "the Windows bootstrap is empty"
    return text


def test_bootstrap_automates_the_existing_enrollment_flow() -> None:
    text = bootstrap()
    for command in ("'init'", "'enroll'", "'connect'"):
        assert command in text, f"bootstrap does not run jocky-agent {command}"
    for option in (
        "--enrollment-server",
        "--server",
        "--ca",
        "--token-file",
        "--worker",
        "--transport-key",
        "--csr",
    ):
        assert option in text, f"bootstrap does not pass {option}"


def test_bootstrap_keeps_the_agent_state_directory() -> None:
    text = bootstrap()
    assert "$env:ProgramData" in text
    assert "'JOCKY'" in text
    assert "--state-dir" in text
    # One state directory is created, protected and reused for every command.
    assert text.count("$StateDir = ") == 1


def test_bootstrap_reads_the_token_from_a_file_and_never_prints_it() -> None:
    text = bootstrap()
    assert "TokenFile" in text
    assert "-Raw" in text, "the token file must be read whole"
    write_commands = [line for line in text.splitlines() if line.strip().startswith("Write-Host")]
    assert not any("$token" in line for line in write_commands), (
        "the enrollment token must never be written to the console"
    )


def test_bootstrap_never_weakens_certificate_verification() -> None:
    text = bootstrap()
    for forbidden in TLS_WEAKENING:
        assert forbidden not in text, f"bootstrap weakens TLS verification: {forbidden}"
    # The CA must be validated as a PEM certificate before it is trusted.
    assert "-----BEGIN CERTIFICATE-----" in text
    assert "^https://" in text


def test_bootstrap_embeds_no_credentials() -> None:
    text = bootstrap()
    assert "Authorization" not in text
    assert "password" not in text.lower()
    # A long base64/hex blob would indicate an embedded key or token.
    assert not re.search(r"[A-Za-z0-9+/]{200,}={0,2}", text)


def test_bootstrap_generates_transport_material_without_openssl() -> None:
    text = bootstrap()
    # The default agent path shells out to OpenSSL, which a stock Windows host
    # does not have; the bootstrap supplies equivalent P-256 material instead.
    assert "ECDsaP256" in text
    assert "CreateSigningRequest" in text
    assert "Pkcs8PrivateBlob" in text
    invocations = [line.strip().lower() for line in text.splitlines() if line.strip()]
    assert not any(
        line.startswith(("openssl", "& openssl", "openssl.exe")) for line in invocations
    ), "the bootstrap must not execute an OpenSSL binary"


def test_windows_ci_validates_and_publishes_the_bootstrap() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/windows/connect-jocky.ps1" in workflow
    assert "jocky-agent.exe" in workflow
    assert "Parser]::ParseFile" in workflow, "CI must parse the bootstrap script"


def test_windows_bundle_ships_one_action_setup() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    installer = ROOT / "scripts/windows/Install-JOCKY.cmd"
    settings = ROOT / "scripts/windows/install-jocky-bootstrap.ps1"
    assert installer.is_file(), "the endpoint bundle needs a one-action entry point"
    assert "jocky-windows-endpoint" in workflow, "CI must publish one endpoint bundle"
    for name in (
        "Install-JOCKY.cmd",
        "install-jocky-bootstrap.ps1",
        "connect-jocky.ps1",
        "jocky-agent.exe",
        "jocky-bootstrap.exe",
    ):
        assert name in workflow, f"the Windows bundle does not ship {name}"
    launcher = installer.read_text(encoding="utf-8")
    # The operator extracts the bundle, drops the downloaded configuration
    # beside it and runs one file: no manual init/enroll/connect sequence.
    assert "jocky-bootstrap.json" in launcher
    assert "RunAs" in launcher, "the launcher must elevate itself"
    for manual in ("jocky-agent.exe init", "jocky-agent.exe enroll", "jocky-agent.exe connect"):
        assert manual not in launcher
    setup = settings.read_text(encoding="utf-8")
    assert "WindowsBuiltInRole]::Administrator" in setup, "setup must require elevation"
    assert "sc.exe create" in setup, "setup must register the supervisor service"
    for forbidden in TLS_WEAKENING:
        assert forbidden not in launcher, f"the launcher weakens TLS: {forbidden}"
        assert forbidden not in setup, f"setup weakens TLS: {forbidden}"


def test_the_bootstrap_is_served_by_the_authenticated_enrollment_api() -> None:
    api = (ROOT / "services/control-plane/src/jocky_control_plane/api.py").read_text(
        encoding="utf-8"
    )
    assert '"/endpoints/enrollments/{identifier}/bootstrap"' in api
    assert "settings.bootstrap_script_path" in api
    settings = (ROOT / "services/control-plane/src/jocky_control_plane/config.py").read_text(
        encoding="utf-8"
    )
    assert "scripts/windows/connect-jocky.ps1" in settings
    # The control-plane image must carry the script it serves.
    dockerfile = (ROOT / "infra/docker/control-plane.Dockerfile").read_text(encoding="utf-8")
    assert "COPY scripts/windows/ scripts/windows/" in dockerfile


def test_console_offers_a_windows_connect_path_from_real_state() -> None:
    console = (ROOT / "apps/dashboard/src/components/operator-console.tsx").read_text(
        encoding="utf-8"
    )
    assert "Start Windows Endpoint" in console
    assert "windows-endpoint/${action}" in console
    assert "Download PowerShell bootstrap" in console
    assert "Download enrollment token" in console
    assert "WAITING_FOR_HEARTBEAT" in console
    assert "Advanced Setup" in console
    # The supervisor report is separate; ONLINE comes from the endpoint status API.
    assert 'windowsEndpoint.data?.state === "ONLINE"' in console
    enrollment = console[
        console.index("function Enrollment") : console.index("function EndpointDetail")
    ]
    assert "setTimeout" not in enrollment
