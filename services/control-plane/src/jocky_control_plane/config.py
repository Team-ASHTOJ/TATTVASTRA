from pathlib import Path
from typing import Literal

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
