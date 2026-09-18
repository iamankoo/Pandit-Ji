from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """astro-engine configuration.

    Phase 3 foundation only -- calculation-specific configuration
    (`CalculationConfig`: ayanamsa, house system, zodiac, ephemeris
    version) is domain logic and belongs to Phase 4, not infra config.
    """

    model_config = SettingsConfigDict(env_prefix="ASTRO_ENGINE_", extra="ignore")
