"""Request and result contracts for Muhurta (Phase 10;
`docs/ASTROLOGY_STANDARDS.md` v1.23.0, MU-01 to MU-14). Factor-level
facts tagged by purpose and source; no overall "auspicious" verdict."""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.muhurta.rules import Classification, FactorKind, Purpose
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.panchang.models import Instant
from pandit_astro_engine.panchang.profiles import EvidenceLabel, SourceReference, SunriseConvention
from pandit_astro_engine.rashi import Rashi


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactorStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class JanmaInput(_Model):
    """One participant's birth nakshatra and birth Moon sign. Participants
    are unlabelled: no role, gender or relationship is recorded (MU-09)."""

    janma_nakshatra: Nakshatra
    janma_rasi: Rashi


class MuhurtaEvaluateRequest(_Model):
    purpose: Purpose
    local_datetime: LocalDateTimeInput
    location: Location
    participants: tuple[JanmaInput, ...] = ()
    sunrise_convention: SunriseConvention = SunriseConvention.CRC_1955_CENTRE_REFRACTION_30
    allow_moshier_fallback: bool = True


class MuhurtaSearchRequest(_Model):
    purpose: Purpose
    start_date: dt.date
    days: int = Field(ge=1, le=31)
    location: Location
    timezone: str
    participants: tuple[JanmaInput, ...] = ()
    sunrise_convention: SunriseConvention = SunriseConvention.CRC_1955_CENTRE_REFRACTION_30
    allow_moshier_fallback: bool = True


class FactorResult(_Model):
    rule_id: str
    kind: FactorKind
    status: FactorStatus
    participant: int | None = Field(default=None, description="index into participants")
    value: str | None = None
    classification: Classification | None = None
    reason: str | None = None
    evidence_label: EvidenceLabel
    reference: SourceReference


class MomentFacts(_Model):
    tithi: str
    paksha: str
    nakshatra: Nakshatra
    yoga: str
    karana: str
    weekday: str
    lagna_sign: Rashi
    lagna_navamsa: Rashi
    moon_sign: Rashi
    sun_sign: Rashi
    planet_signs: tuple[tuple[str, Rashi], ...]
    jupiter_combust: bool
    venus_combust: bool
    is_daytime: bool
    forenoon: bool


class Summary(_Model):
    favourable: int
    middling: int
    unfavourable: int
    not_listed: int
    not_evaluable: int
    unfavourable_rule_ids: tuple[str, ...]
    not_evaluable_rule_ids: tuple[str, ...]
    no_unfavourable_factor: bool = Field(
        description="no evaluated factor is unfavourable; not-evaluable factors are listed"
    )


class MuhurtaEvaluation(_Model):
    system: str
    standards_version: str
    rules_version: str
    engine_version: str
    purpose: Purpose
    sunrise_convention: SunriseConvention
    ayanamsa: str
    instant: Instant
    status: FactorStatus
    reason: str | None = None
    facts: MomentFacts | None = None
    factors: tuple[FactorResult, ...] = ()
    summary: Summary | None = None
    notes: tuple[str, ...] = ()


class MuhurtaWindow(_Model):
    start: Instant
    end: Instant
    facts_at_midpoint: MomentFacts
    summary: Summary


class MuhurtaSearchResult(_Model):
    system: str
    standards_version: str
    rules_version: str
    engine_version: str
    purpose: Purpose
    sunrise_convention: SunriseConvention
    ayanamsa: str
    start_date: dt.date
    days: int
    timezone: str
    location: Location
    segments_examined: int
    days_not_evaluable: tuple[dt.date, ...]
    windows: tuple[MuhurtaWindow, ...]
    rules: tuple[str, ...]
    notes: tuple[str, ...] = ()
