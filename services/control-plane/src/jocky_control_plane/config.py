from pathlib import Path
from typing import Literal

from jocky_contracts.common import Mode
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOCKY_", extra="ignore")
    environment: Literal["development", "test"] = "development"
    mode: Mode = Mode.REAL
    transport_mode: Literal["DIRECT"] = "DIRECT"
    compiler_path: Path | None = None
    compiler_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    # Refuse production/relay settings until authentication and TLS are implemented.
