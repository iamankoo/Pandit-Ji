from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """rule-engine configuration. Rule-set version/location config is domain
    logic and belongs to Phase 6, not this Phase 3 foundation."""

    model_config = SettingsConfigDict(env_prefix="RULE_ENGINE_", extra="ignore")
