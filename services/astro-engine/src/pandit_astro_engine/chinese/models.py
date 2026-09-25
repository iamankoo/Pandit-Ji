"""Request and result contracts for the Chinese Four Pillars module
(Phase 9 WP-H; `docs/ASTROLOGY_STANDARDS.md` v1.18.0, CN-01 to CN-14).
Calendar facts and provenance only; no interpretation."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from pandit_astro_engine.chinese.constants import (
    Branch,
    ChineseTimePrecision,
    DayBoundary,
    Element,
    PillarReason,
    PillarStatus,
    Polarity,
    Stem,
    TimeBasis,
)
from pandit_astro_engine.chinese.profiles import PROFILE_ID, EvidenceLabel, SourceReference
from pandit_astro_engine.models import EphemerisMode, LocalDateTimeInput, Location, TimeResolution


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChineseChartRequest(_Model):
    """`time_basis` and `day_boundary` have no default (CN-08, CN-09)."""

    local_datetime: LocalDateTimeInput
    location: Location
    time_precision: ChineseTimePrecision
    time_basis: TimeBasis
    day_boundary: DayBoundary
    allow_moshier_fallback: bool = True


class Pillar(_Model):
    status: PillarStatus
    reason: PillarReason | None = None
    sexagenary_index: int | None = Field(default=None, description="0 = 甲子 ... 59 = 癸亥")
    stem: Stem | None = None
    branch: Branch | None = None
    stem_character: str | None = None
    branch_character: str | None = None
    stem_element: Element | None = None
    stem_polarity: Polarity | None = None
    branch_element: Element | None = None
    branch_polarity: Polarity | None = None
    branch_animal: str | None = None


class SolarTermBracket(_Model):
    """The jie terms before and after the birth instant (UTC)."""

    previous_longitude: float
    previous_utc: dt.datetime
    next_longitude: float
    next_utc: dt.datetime


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class ChineseChartFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    profile_id: str = PROFILE_ID
    time_precision: ChineseTimePrecision
    time_basis: TimeBasis
    day_boundary: DayBoundary
    time_resolution: TimeResolution
    location: Location
    ephemeris_mode: EphemerisMode
    sun_apparent_longitude: float
    near_solar_term: bool
    solar_term_bracket: SolarTermBracket
    lichun_year: int
    basis_local_datetime: dt.datetime | None = Field(
        default=None, description="Local date-time in the chosen time basis (naive)."
    )
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar
    not_evaluated: tuple[str, ...] = (
        "luck_cycles_require_sex_not_collected",
        "hidden_stems",
        "ten_gods",
        "na_yin",
        "interpretation",
    )
    provenance: tuple[ProvenanceEntry, ...]
    warnings: tuple[str, ...] = ()
