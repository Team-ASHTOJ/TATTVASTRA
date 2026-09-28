from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from jocky_contracts.common import Mode
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOCKY_", extra="ignore")
    environment: Literal["development", "test"] = "development"
    mode: Mode = Mode.REAL
    transport_mode: Literal["DIRECT"] = "DIRECT"
    compiler_path: Path | None = None
    worker_sdk_path: Path | None = None
    database_url: str | None = None
    object_root: Path = Path(".local/objects")
    signing_key_path: Path = Path(".local/control-plane.key")
    tls_ca_path: Path = Path(".local/tls/ca.pem")
    # Served to an operator so a Windows host can run the existing native
    # enrollment flow without copying scripts by hand.
    bootstrap_script_path: Path = Path("scripts/windows/connect-jocky.ps1")
    # The address an external endpoint uses to reach this control plane. The
    # internal names below are loopback and compose-network names, so an
    # external Windows host must never be handed those: on that machine
    # "localhost" is the Windows host itself. Set this to the LAN name or
    # address of the JOCKY machine. Nothing here is hardcoded to a developer
    # address, and the three explicit URLs below still win when set.
    agent_public_host: str | None = None
    agent_api_port: int = Field(default=18443, ge=1, le=65535)
    agent_control_port: int = Field(default=15051, ge=1, le=65535)
    agent_enrollment_port: int = Field(default=15052, ge=1, le=65535)
    windows_api_url: str | None = None
    windows_control_server: str | None = None
    windows_enrollment_server: str | None = None
    tls_ca_key_path: Path = Path(".local/tls/ca.key")
    tls_cert_path: Path = Path(".local/tls/server.pem")
    tls_key_path: Path = Path(".local/tls/server.key")
    grpc_relay_bind: str | None = None
    grpc_relay_enrollment_bind: str | None = None
    grpc_bind: str = "127.0.0.1:50051"
    grpc_enrollment_bind: str = "127.0.0.1:50052"
    local_launcher_url: str | None = None
    local_launcher_urls: list[str] = []
    local_launcher_token: SecretStr | None = None
    event_stream_seconds: float = Field(default=60, gt=0, le=60)
    compiler_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    # This is a local prototype; production deployment and relay remain unsupported.

    @property
    def agent_public_addresses(self) -> tuple[str | None, str | None, str | None]:
        """(api_url, control_server, enrollment_server) for an external endpoint.

        Each address is what the endpoint dials, so it must resolve and be
        reachable on the endpoint's own network. An explicitly configured URL
        always wins; otherwise the address is composed from the public host.
        """
        if not self.agent_public_host:
            return (
                self.windows_api_url,
                self.windows_control_server,
                self.windows_enrollment_server,
            )
        host = self.agent_public_host.strip().strip("/")
        return (
            self.windows_api_url or f"https://{host}:{self.agent_api_port}",
            self.windows_control_server or f"https://{host}:{self.agent_control_port}",
            self.windows_enrollment_server or f"https://{host}:{self.agent_enrollment_port}",
        )

    @property
    def agent_public_names(self) -> list[str]:
        """Hosts the server certificate must cover for those addresses."""
        names = []
        for url in self.agent_public_addresses:
            if not url:
                continue
            host = urlsplit(url).hostname
            if host and host not in names:
                names.append(host)
        return names
