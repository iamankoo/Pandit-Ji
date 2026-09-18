"""Typed Kundli (birth chart) output contracts -- Phase 5 (Birth Chart /
Kundli Engine).

Chart/domain concepts only: builds on top of Phase 4's `CalculationResult`
(astronomical facts) rather than re-declaring planetary longitude/speed/
retrograde/combustion fields, per the "facts flow one direction" invariant
-- this module adds derived chart structure, it never recomputes or
shadows Phase 4 astronomical facts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from pandit_astro_engine.dignity import DignityStatus
from pandit_astro_engine.models import CalculationResult, CelestialBody, EphemerisMode
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.rashi import Rashi


class RashiPlacement(BaseModel):
    rashi: Rashi
    degree_in_sign: float = Field(..., description="0.0 (inclusive) .. 30.0 (exclusive).")


class NakshatraPlacement(BaseModel):
    nakshatra: Nakshatra
    pada: int = Field(..., ge=1, le=4)
    lord: CelestialBody
    near_boundary: bool = Field(
        ...,
        description=(
            "True when the longitude falls within floating-point epsilon of a "
            "Nakshatra/Pada boundary -- flagged for review per "
            "docs/ASTROLOGY_STANDARDS.md 'Nakshatra standards', never silently "
            "rounded to one side."
        ),
    )


class HouseInfo(BaseModel):
    house: int = Field(..., ge=1, le=12)
    rashi: Rashi
    lord: CelestialBody


class KundliPlanet(BaseModel):
    """A planet's D1 (Rashi chart) placement plus every Phase 5 derived
    attribute that is evaluated once, at D1, rather than per-varga
    (Nakshatra/Pada, dignity, aspects)."""

    body: CelestialBody
    longitude: float
    rashi: Rashi
    degree_in_sign: float
    house: int = Field(
        ..., ge=1, le=12, description="Whole-sign house, relative to the D1 Ascendant."
    )
    nakshatra: NakshatraPlacement
    dignity: DignityStatus | None = Field(
        None, description="None for Rahu/Ketu (not evaluated under this standard)."
    )
    retrograde: bool
    combust: bool | None = Field(
        None, description="None where combustion is not evaluated (Sun/Rahu/Ketu)."
    )
    aspected_houses: list[int] = Field(
        ..., description="Houses (1-12) this planet aspects, D1-relative."
    )
    ephemeris_mode: EphemerisMode


class DivisionalPlanetPlacement(BaseModel):
    """A planet's placement within one divisional (varga) chart -- deliberately
    minimal: Nakshatra/dignity/aspects are D1 concepts (see `KundliPlanet`),
    not recomputed per-varga."""

    body: CelestialBody
    rashi: Rashi
    house: int = Field(
        ..., ge=1, le=12, description="Whole-sign house, relative to this chart's own Ascendant."
    )
    house_lord: CelestialBody


class DivisionalChart(BaseModel):
    varga: int = Field(
        ..., description="1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, or 60."
    )
    label: str = Field(..., description='e.g. "D1", "D9", or "Chandra Lagna" for the Moon chart.')
    ascendant_rashi: Rashi
    houses: list[HouseInfo] = Field(..., min_length=12, max_length=12)
    planets: list[DivisionalPlanetPlacement]


class KundliMetadata(BaseModel):
    engine_version: str
    standards_version: str = Field(
        ..., description="docs/ASTROLOGY_STANDARDS.md version this Kundli was built against."
    )
    house_system: str = "vedic_whole_sign"
    varga_scheme: str = "classical_parashari_v1"
    aspect_standard: str = "vedic_graha_drishti_v1"
    dignity_standard: str = "classical_exaltation_debilitation_v1"


class Kundli(BaseModel):
    """The complete machine-readable Kundli (`Phases.md` Phase 5
    deliverable). `astronomical` is Phase 4's own `CalculationResult`,
    embedded rather than re-derived -- every chart fact here traces back to
    that single set of ephemeris-backed longitudes."""

    astronomical: CalculationResult
    lagna_longitude: float = Field(
        ..., description="Sidereal Ascendant, absolute degrees [0, 360)."
    )
    lagna: RashiPlacement
    houses: list[HouseInfo] = Field(
        ..., min_length=12, max_length=12, description="D1 whole-sign houses."
    )
    planets: list[KundliPlanet]
    charts: dict[int, DivisionalChart] = Field(
        ..., description="Keyed by varga number (1, 2, 3, ... 60); includes D1 for uniform access."
    )
    chandra_chart: DivisionalChart | None = Field(
        None, description="Moon-as-Lagna whole-sign chart; None only if Moon was not requested."
    )
    metadata: KundliMetadata
