from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """verification configuration. Verification-check-specific config is
    added in Phase 16 -- not this foundation."""

    model_config = SettingsConfigDict(env_prefix="VERIFICATION_", extra="ignore")
