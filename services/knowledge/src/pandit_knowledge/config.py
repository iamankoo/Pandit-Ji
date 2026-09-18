from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """knowledge configuration. Embedding-model and pgvector-index
    configuration is added in Phase 12 -- not this foundation."""

    model_config = SettingsConfigDict(env_prefix="KNOWLEDGE_", extra="ignore")
