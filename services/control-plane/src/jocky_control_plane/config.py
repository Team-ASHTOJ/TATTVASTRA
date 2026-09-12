from typing import Literal

from jocky_contracts.common import Mode
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOCKY_", extra="ignore")
    environment: Literal["development", "test"] = "development"
    mode: Mode = Mode.REAL
    transport_mode: Literal["DIRECT"] = "DIRECT"
    # Refuse production/relay settings until authentication and TLS are implemented.
