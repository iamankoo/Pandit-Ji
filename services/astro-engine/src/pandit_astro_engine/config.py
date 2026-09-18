from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """astro-engine configuration.

    `ephemeris_path` is the only Phase 4 addition: where to find Swiss
    Ephemeris `.se1` data files (never committed to this repository --
    see README.md "Ephemeris data"). Per-request calculation configuration
    (ayanamsa, zodiac, node convention, ...) is `models.CalculationConfig`,
    not process-level settings, since it varies per calculation.
    """

    model_config = SettingsConfigDict(env_prefix="ASTRO_ENGINE_", extra="ignore")

    ephemeris_path: str | None = Field(
        default=None,
        description=(
            "Filesystem path to Swiss Ephemeris .se1 data files. If unset, the "
            "engine uses Swiss Ephemeris's built-in Moshier analytical fallback, "
            "explicitly flagged in every result's metadata.ephemeris_mode."
        ),
    )
