from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """agent configuration. LLMProvider/AI Reasoner endpoint configuration
    is added when Phase 14/15 wire up real inference -- not this foundation."""

    model_config = SettingsConfigDict(env_prefix="AGENT_", extra="ignore")
