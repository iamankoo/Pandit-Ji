"""Typed contracts for the Vimshottari Dasha engine (Phase 7).

Facts only: this module carries temporal facts and their provenance. It has no
interpretation vocabulary (no career, marriage, Maraka ...); later phases
consume these facts.
"""

from __future__ import annotations

import datetime as dt
import math
from enum import Enum
from fractions import Fraction

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.dashas.constants import (
    BOUNDARY_CONVENTION,
    DASHA_STANDARDS_VERSION,
    SYSTEM_ID,
    TIME_BASE,
    DashaLevel,
)
from pandit_astro_engine.dashas.profiles import (
    DEFAULT_BALANCE_PROFILE_ID,
    DEFAULT_YEAR_LENGTH_PROFILE_ID,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import Nakshatra


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DashaStatus(str, Enum):
    SUCCESS = "success"
    APPROXIMATE = "approximate"
    NOT_EVALUABLE = "not_evaluable"
    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_PROFILE = "unsupported_profile"
    CONFIGURATION_ERROR = "configuration_error"
    INTERNAL_ERROR = "internal_error"


class DashaReason(str, Enum):
    """Machine-readable reason codes. Every non-success status carries one."""

    # NOT_EVALUABLE
    BIRTH_TIME_UNKNOWN = "birth_time_unknown"
    UNCERTAINTY_INTERVAL_MISSING = "uncertainty_interval_missing"
    STARTING_LORD_AMBIGUOUS = "starting_lord_ambiguous"
    # INVALID_INPUT
    MOON_LONGITUDE_MISSING = "moon_longitude_missing"
    NON_FINITE_LONGITUDE = "non_finite_longitude"
    NAIVE_DATETIME = "naive_datetime"
    INVALID_TIMEZONE = "invalid_timezone"
    INVALID_LOCAL_DATETIME = "invalid_local_datetime"
    AMBIGUOUS_LOCAL_TIME = "ambiguous_local_time"
    NONEXISTENT_LOCAL_TIME = "nonexistent_local_time"
    INVALID_UNCERTAINTY = "invalid_uncertainty"
    REVERSED_INTERVAL = "reversed_interval"
    MOON_RANGE_INCONSISTENT = "moon_range_inconsistent"
    UNSUPPORTED_HIERARCHY_DEPTH = "unsupported_hierarchy_depth"
    INVALID_HORIZON = "invalid_horizon"
    UNKNOWN_LORD = "unknown_lord"
    TIMELINE_OUT_OF_RANGE = "timeline_out_of_range"
    # UNSUPPORTED_PROFILE
    UNKNOWN_BALANCE_PROFILE = "unknown_balance_profile"
    UNKNOWN_YEAR_LENGTH_PROFILE = "unknown_year_length_profile"
    PROFILE_INACTIVE = "profile_inactive"
    # CONFIGURATION_ERROR
    SIDEREAL_ZODIAC_REQUIRED = "sidereal_zodiac_required"
    EPHEMERIS_UNAVAILABLE = "ephemeris_unavailable"
    INCOMPATIBLE_CONFIGURATION = "incompatible_configuration"
    # INTERNAL_ERROR
    INTERNAL_ERROR = "internal_error"


class BirthTimeStatus(str, Enum):
    """Precision of the birth time (docs/ASTROLOGY_STANDARDS.md
    "Birth-time uncertainty"). Never silently upgraded."""

    EXACT = "exact"
    APPROXIMATE = "approximate"
    NOT_EVALUABLE = "not_evaluable"


class RangePosition(str, Enum):
    BEFORE_TIMELINE = "before_timeline"
    WITHIN_TIMELINE = "within_timeline"
    AT_OR_AFTER_TIMELINE_END = "at_or_after_timeline_end"


# --------------------------------------------------------------------------
# Rational numbers: exact, JSON-safe
# --------------------------------------------------------------------------


class Rational(_Model):
    numerator: int
    denominator: int = Field(gt=0)

    @classmethod
    def of(cls, value: Fraction) -> Rational:
        return cls(numerator=value.numerator, denominator=value.denominator)

    def to_fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def approx(self) -> float:
        return self.numerator / self.denominator


# --------------------------------------------------------------------------
# Configuration and request
# --------------------------------------------------------------------------


class DashaConfiguration(_Model):
    """Profile choices are plain strings so that an unknown ID becomes an
    `UNSUPPORTED_PROFILE` result rather than a construction-time exception."""

    balance_profile_id: str = DEFAULT_BALANCE_PROFILE_ID
    year_length_profile_id: str = DEFAULT_YEAR_LENGTH_PROFILE_ID
    depth: int = Field(default=3, description="1 = Mahadasha, 2 = + Antardasha, 3 = + Pratyantar.")
    horizon_years: int = Field(
        default=120, description="Cover at least this many profile-years after birth."
    )


class BirthTimeInput(_Model):
    status: BirthTimeStatus = BirthTimeStatus.EXACT
    uncertainty_seconds: float | None = Field(
        default=None, description="Symmetric half-width of the birth-time interval, seconds."
    )


class MoonUncertaintyRange(_Model):
    """Moon sidereal longitudes at the earliest and latest instants of the
    birth-time interval. Supplied by the caller (the service computes them)."""

    moon_longitude_at_earliest: float
    moon_longitude_at_latest: float


class DashaRequest(_Model):
    """Pure-arithmetic request: a Moon sidereal longitude and a UTC birth
    instant. `moon_longitude_degrees` may be None so that a missing Moon is a
    structured `INVALID_INPUT` result, not an exception."""

    moon_longitude_degrees: float | None
    birth_utc: dt.datetime
    config: DashaConfiguration = Field(default_factory=DashaConfiguration)
    birth_time: BirthTimeInput = Field(default_factory=BirthTimeInput)
    uncertainty_range: MoonUncertaintyRange | None = None


class BirthTimeRecord(_Model):
    """Time-conversion facts, kept so the original local input is never lost."""

    input_local_datetime: str
    timezone: str
    utc_offset_seconds: int
    dst_active: bool
    was_ambiguous: bool
    was_nonexistent: bool
    disambiguation_applied: str | None
    utc_datetime: dt.datetime
    julian_day_ut: float


class ValidationResult(_Model):
    valid: bool
    status: DashaStatus = DashaStatus.SUCCESS
    reason_code: DashaReason | None = None
    detail: str | None = None


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class PrecisionAssessment(_Model):
    birth_time_status: BirthTimeStatus
    uncertainty_seconds: float | None = None
    starting_lord_stable: bool | None = None
    nakshatra_boundary_within_interval: bool | None = None
    pada_boundary_within_interval: bool | None = None
    moon_longitude_low: float | None = None
    moon_longitude_high: float | None = None
    balance_fraction_min: Rational | None = None
    balance_fraction_max: Rational | None = None
    first_mahadasha_end_earliest_utc: dt.datetime | None = None
    first_mahadasha_end_latest_utc: dt.datetime | None = None
    envelope_method: str | None = Field(
        default=None,
        description=(
            "How the first-Mahadasha end range was evaluated. It is an envelope from the two "
            "interval endpoints and the nominal instant, not a proven bound."
        ),
    )


class StartingState(_Model):
    raw_moon_longitude: float
    normalized_longitude: float
    nakshatra: Nakshatra
    pada: int = Field(ge=1, le=4)
    lord: CelestialBody
    near_boundary: bool
    elapsed_fraction: Rational
    remaining_fraction: Rational
    lord_full_years: int
    remaining_duration_microseconds_exact: Rational
    remaining_duration_microseconds: int = Field(
        description="Exact remaining duration floored to whole microseconds."
    )


class PeriodProfileIds(_Model):
    balance_profile_id: str
    year_length_profile_id: str
    subperiod_profile_id: str


class PeriodNode(_Model):
    period_id: str
    level: DashaLevel
    lord: CelestialBody
    parent_id: str | None
    sequence_index: int = Field(ge=0, description="Position within the parent (0-based).")
    path: tuple[str, ...] = Field(description="Lord IDs from the Mahadasha down to this period.")
    start_utc: dt.datetime
    end_utc: dt.datetime
    nominal_start_utc: dt.datetime = Field(
        description="Start before truncation at birth; equals start_utc unless truncated."
    )
    truncated_at_birth: bool
    duration_microseconds: int = Field(ge=0)
    profile_ids: PeriodProfileIds
    standards_version: str
    engine_version: str
    calculation_status: DashaStatus
    provenance_ids: tuple[str, ...]

    @model_validator(mode="after")
    def _ordered(self) -> PeriodNode:
        if self.end_utc < self.start_utc:
            raise ValueError("period end precedes its start")
        if self.nominal_start_utc > self.start_utc:
            raise ValueError("nominal start after start")
        return self


class DashaFacts(_Model):
    """The complete Vimshottari result. For any non-success status `periods`
    is empty and `reason_code` says why; nothing is guessed."""

    system_id: str = SYSTEM_ID
    status: DashaStatus
    reason_code: DashaReason | None = None
    detail: str | None = None
    standards_version: str = DASHA_STANDARDS_VERSION
    engine_version: str
    boundary_convention: str = BOUNDARY_CONVENTION
    time_base: str = TIME_BASE
    profile_ids: PeriodProfileIds
    precision: PrecisionAssessment
    birth_utc: dt.datetime | None = None
    birth_record: BirthTimeRecord | None = None
    starting: StartingState | None = None
    depth: int | None = None
    horizon_years: int | None = None
    timeline_start_utc: dt.datetime | None = None
    timeline_end_utc: dt.datetime | None = None
    periods: tuple[PeriodNode, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[ProvenanceEntry, ...] = ()

    @model_validator(mode="after")
    def _status_contract(self) -> DashaFacts:
        ok = self.status in (DashaStatus.SUCCESS, DashaStatus.APPROXIMATE)
        if ok and self.reason_code is not None:
            raise ValueError("a successful result must not carry a failure reason code")
        if not ok and self.reason_code is None:
            raise ValueError("every failure must carry a machine-readable reason code")
        if not ok and self.periods:
            raise ValueError("a failed result must not carry periods")
        return self


class LevelPosition(_Model):
    period_id: str
    level: DashaLevel
    lord: CelestialBody
    start_utc: dt.datetime
    end_utc: dt.datetime
    elapsed_microseconds: int
    remaining_microseconds: int


class PeriodResolution(_Model):
    """Which Mahadasha / Antardasha / Pratyantar own an instant. The later
    period owns a shared boundary (half-open intervals)."""

    status: DashaStatus
    reason_code: DashaReason | None = None
    range_position: RangePosition | None = None
    at_utc: dt.datetime | None = None
    levels: tuple[LevelPosition, ...] = ()
    path: tuple[str, ...] = ()


class Transition(_Model):
    level: DashaLevel
    at_utc: dt.datetime
    from_period_id: str
    to_period_id: str
    from_lord: CelestialBody
    to_lord: CelestialBody


class PeriodQueryResult(_Model):
    status: DashaStatus
    reason_code: DashaReason | None = None
    periods: tuple[PeriodNode, ...] = ()


def finite(value: float) -> bool:
    return math.isfinite(value)
