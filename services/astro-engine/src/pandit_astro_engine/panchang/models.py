"""Request and result contracts for the daily Panchang (Phase 10;
`docs/ASTROLOGY_STANDARDS.md` v1.23.0, PC-01 to PC-24). Facts and
provenance only; no auspiciousness verdict."""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from pandit_astro_engine.models import CelestialBody, EphemerisMode, Location
from pandit_astro_engine.panchang.constants import (
    KaranaName,
    MonthName,
    Paksha,
    TithiName,
    Weekday,
    YogaName,
)
from pandit_astro_engine.panchang.profiles import (
    EvidenceLabel,
    RegionalConvention,
    SauraFrame,
    SourceReference,
    SunriseConvention,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PanchangStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class PanchangReason(str, Enum):
    SUNRISE_NOT_OCCURRING = "sunrise_not_occurring"
    SUNSET_NOT_OCCURRING = "sunset_not_occurring"
    YEAR_START_ADHIKA_CHAITRA = "year_start_adhika_chaitra"


class EventStatus(str, Enum):
    OCCURRED = "occurred"
    NO_EVENT_IN_DAY = "no_event_in_day"
    CIRCUMPOLAR_NO_EVENT = "circumpolar_no_event"


class ElementKind(str, Enum):
    TITHI = "tithi"
    NAKSHATRA = "nakshatra"
    YOGA = "yoga"
    KARANA = "karana"


class Instant(_Model):
    julian_day_ut: float
    utc: dt.datetime
    local: dt.datetime


class RiseSet(_Model):
    status: EventStatus
    instant: Instant | None = None


class PanchangRequest(_Model):
    """`timezone` has no default: the Panchang is location- and
    zone-dependent (standards §Panchang, PC-01)."""

    date: dt.date
    location: Location
    timezone: str
    sunrise_convention: SunriseConvention = SunriseConvention.CRC_1955_CENTRE_REFRACTION_30
    regional_convention: RegionalConvention = RegionalConvention.PAN_INDIAN_DRIK_CRC_1955
    allow_moshier_fallback: bool = True


class ElementSpan(_Model):
    kind: ElementKind
    index: int = Field(description="1-based: tithi 1-30, nakshatra 1-27, yoga 1-27, karana 1-60")
    name: str
    start: Instant
    end: Instant
    current_at_sunrise: bool
    current_at_next_sunrise: bool
    #: Begins after this sunrise and ends before the next one (an expunged
    #: element in Sewell and Dikshit's terms, Art. 32).
    kshaya: bool


class TithiInfo(_Model):
    index: int
    name: TithiName
    paksha: Paksha
    number_in_paksha: int


class Vara(_Model):
    weekday: Weekday
    lord: CelestialBody


class LunarMonth(_Model):
    """One saura frame's month facts for the Hindu day (PC-13 to PC-17)."""

    saura_frame: SauraFrame
    amanta_month: MonthName
    amanta_adhika: bool
    purnimanta_month: MonthName
    purnimanta_adhika: bool
    paksha: Paksha
    suppressed_month_before: MonthName | None = Field(
        default=None, description="a kshaya name skipped just before this month"
    )
    month_start_new_moon: Instant
    month_end_new_moon: Instant
    saka_year_expired: int | None = None
    vikrama_year_chaitradi_expired: int | None = None
    year_reason: PanchangReason | None = None


class DayPartKind(str, Enum):
    RAHU_KALAM = "rahu_kalam"
    YAMAGANDA = "yamaganda"
    GULIKA_KALAM = "gulika_kalam"


class DayPart(_Model):
    kind: DayPartKind
    period: str = Field(description="day or night")
    part: int = Field(description="1-8")
    start: Instant
    end: Instant
    evidence_label: EvidenceLabel


class Hora(_Model):
    number: int = Field(description="1 = the hora beginning at sunrise")
    lord: CelestialBody
    start: Instant
    end: Instant
    truncated_by_next_sunrise: bool = False


class Interval(_Model):
    start: Instant
    end: Instant
    starts_before_day: bool
    ends_after_day: bool


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...]


class NotImplementedItem(_Model):
    item: str
    reason: str


class DailyPanchang(_Model):
    system: str
    standards_version: str
    engine_version: str
    profile_id: str
    regional_convention: RegionalConvention
    sunrise_convention: SunriseConvention
    hora_profile_id: str
    day_part_profile_id: str
    date: dt.date
    location: Location
    timezone: str
    ayanamsa: str
    status: PanchangStatus
    reason: PanchangReason | None = None
    ephemeris_mode: EphemerisMode | None = None
    sunrise: RiseSet
    sunset: RiseSet
    next_sunrise: RiseSet
    moonrise: RiseSet
    moonset: RiseSet
    vara: Vara | None = None
    tithi_at_sunrise: TithiInfo | None = None
    tithis: tuple[ElementSpan, ...] = ()
    nakshatras: tuple[ElementSpan, ...] = ()
    yogas: tuple[ElementSpan, ...] = ()
    karanas: tuple[ElementSpan, ...] = ()
    lunar_months: tuple[LunarMonth, ...] = ()
    day_parts: tuple[DayPart, ...] = ()
    horas: tuple[Hora, ...] = ()
    nakshatra_panchaka: tuple[Interval, ...] = ()
    bhadra: tuple[Interval, ...] = ()
    not_implemented: tuple[NotImplementedItem, ...] = ()
    provenance: tuple[ProvenanceEntry, ...] = ()
    warnings: tuple[str, ...] = ()


__all__ = [
    "DailyPanchang",
    "DayPart",
    "DayPartKind",
    "ElementKind",
    "ElementSpan",
    "EventStatus",
    "Hora",
    "Instant",
    "Interval",
    "KaranaName",
    "LunarMonth",
    "NotImplementedItem",
    "PanchangReason",
    "PanchangRequest",
    "PanchangStatus",
    "ProvenanceEntry",
    "RiseSet",
    "TithiInfo",
    "Vara",
    "YogaName",
]
