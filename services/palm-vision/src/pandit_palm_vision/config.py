from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """palm-vision configuration. Pipeline parameters live in versioned configuration objects
    (`QualityConfig`, `ToleranceRecord`), not in environment variables."""

    model_config = SettingsConfigDict(env_prefix="PALM_VISION_", extra="ignore")
