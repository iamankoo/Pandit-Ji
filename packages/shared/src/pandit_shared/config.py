"""Base typed settings every service/server extends.

Only the environment variables that are genuinely cross-cutting at Phase 3
live here (`APP_ENV`, `LOG_LEVEL`). Component-specific settings (e.g.
`server/`'s `DATABASE_URL`) are defined in that component's own config
module and inherit this base.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class BaseServiceSettings(BaseSettings):
    """Common settings every Pandit Ji Python component reads from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: AppEnv = AppEnv.DEVELOPMENT
    log_level: str = "INFO"
