"""Typed contracts for the Transit / Gochar engine (Phase 8).

Facts only: this module carries transit facts and their provenance. It has no
interpretation vocabulary (no good, bad, career, marriage, remedy ...); later
phases consume these facts. A "favourable set" is membership in a source's list
of houses, never a verdict.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.kundli_models import Kundli
from pandit_astro_engine.models import CalculationConfig, CelestialBody, EphemerisMode
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.transits.constants import (
    ALL_BODIES,
    BOUNDARY_CONVENTION,
    SYSTEM_ID,
    TIME_BASE,
    TRANSIT_STANDARDS_VERSION,
)
from pandit_astro_engine.transits.profiles import (
    REF_MOON_SIGN_ID,
    SADE_SATI_ID,
    VEDHA_PHALADEEPIKA_ID,
    EvidenceLabel,
    SourceReference,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TransitStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"
    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_PROFILE = "unsupported_profile"
    CONFIGURATION_ERROR = "configuration_error"
    INTERNAL_ERROR = "internal_error"


class TransitReason(str, Enum):
    """Machine-readable reason codes. Every non-success status carries one."""

    # NOT_EVALUABLE
    MOON_LONGITUDE_MISSING = "moon_longitude_missing"
    NATAL_MOON_SIGN_AMBIGUOUS = "natal_moon_sign_ambiguous"
    NATAL_RANGE_MISSING = "natal_range_missing"
    NATAL_TIME_UNKNOWN = "natal_time_unknown"
    NATAL_PLANETS_UNAVAILABLE = "natal_planets_unavailable"
    LAGNA_UNAVAILABLE = "lagna_unavailable"
    READING_AMBIGUOUS = "reading_ambiguous"
    NODE_PARTICIPATION_UNSPECIFIED = "node_participation_unspecified"
    NODE_READING_SINGLE_SOURCE = "node_reading_single_source"
    NOT_SPECIFIED_BY_SOURCE = "not_specified_by_source"
    WINDOW_TOO_LARGE = "window_too_large"
    EVENT_LIMIT_EXCEEDED = "event_limit_exceeded"
    EPHEMERIS_ERROR = "ephemeris_error"
    # INVALID_INPUT
    INVALID_WINDOW = "invalid_window"
    INVALID_INSTANT = "invalid_instant"
    NO_QUERY = "no_query"
    NON_FINITE_LONGITUDE = "non_finite_longitude"
    NATAL_RANGE_INCONSISTENT = "natal_range_inconsistent"
    NO_BODIES = "no_bodies"
    # UNSUPPORTED_PROFILE
    UNSUPPORTED_PROFILE = "unsupported_profile"
    # CONFIGURATION_ERROR
    SIDEREAL_ZODIAC_REQUIRED = "sidereal_zodiac_required"
    EPHEMERIS_UNAVAILABLE = "ephemeris_unavailable"
    # INTERNAL_ERROR
    INTERNAL_ERROR = "internal_error"


class EventKind(str, Enum):
    SIGN_INGRESS = "sign_ingress"
    NAKSHATRA_INGRESS = "nakshatra_ingress"
    STATION_RETROGRADE = "station_retrograde"
    STATION_DIRECT = "station_direct"


DEFAULT_EVENT_KINDS: tuple[EventKind, ...] = (
    EventKind.SIGN_INGRESS,
    EventKind.STATION_RETROGRADE,
    EventKind.STATION_DIRECT,
)


class FavourableStatus(str, Enum):
    """Membership in a source's favourable set: a structural fact, not a verdict."""

    IN_FAVOURABLE_SET = "in_favourable_set"
    NOT_IN_FAVOURABLE_SET = "not_in_favourable_set"
    NOT_EVALUABLE = "not_evaluable"


class ContactKind(str, Enum):
    CONJUNCTION = "conjunction"
    ASPECT = "aspect"


class SectionStatus(str, Enum):
    AVAILABLE = "available"
    NOT_EVALUABLE = "not_evaluable"
    NOT_REQUESTED = "not_requested"


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------


class NatalReference(_Model):
    """The natal facts a transit is related to. Precision is never upgraded:
    an approximate natal time needs an explicit Moon longitude range."""

    precision: BirthTimeStatus = BirthTimeStatus.EXACT
    moon_longitude: float | None = Field(
        default=None, description="Sidereal longitude of the natal Moon, degrees."
    )
    moon_longitude_low: float | None = Field(
        default=None, description="Lower end of the Moon's range for an approximate natal time."
    )
    moon_longitude_high: float | None = Field(
        default=None, description="Upper end of the Moon's range (range runs forward mod 360)."
    )
    lagna_longitude: float | None = None
    natal_planets: dict[CelestialBody, float] = Field(
        default_factory=dict,
        description="Sidereal longitudes of the natal planets (exact natal time only).",
    )

    @classmethod
    def from_kundli(cls, kundli: Kundli) -> NatalReference:
        """An exact natal reference from a Phase 5 Kundli (sidereal D1)."""
        planets = {p.body: p.longitude for p in kundli.planets}
        return cls(
            precision=BirthTimeStatus.EXACT,
            moon_longitude=planets.get(CelestialBody.MOON),
            lagna_longitude=kundli.lagna_longitude,
            natal_planets=planets,
        )

    def all_longitudes(self) -> list[float]:
        """Every supplied natal longitude, for input validation."""
        values = [
            self.moon_longitude,
            self.moon_longitude_low,
            self.moon_longitude_high,
            self.lagna_longitude,
            *self.natal_planets.values(),
        ]
        return [v for v in values if v is not None]


class TransitConfiguration(_Model):
    """Profile choices are plain strings so an unknown ID becomes an
    `UNSUPPORTED_PROFILE` result rather than a construction-time exception."""

    calculation: CalculationConfig = Field(default_factory=CalculationConfig)
    reference_profile_id: str = REF_MOON_SIGN_ID
    vedha_profile_id: str = VEDHA_PHALADEEPIKA_ID
    sade_sati_profile_id: str = SADE_SATI_ID
    bodies: tuple[CelestialBody, ...] = ALL_BODIES
    event_kinds: tuple[EventKind, ...] = DEFAULT_EVENT_KINDS
    include_lagna_fact: bool = False
    include_vedha: bool = True
    include_contacts: bool = True
    include_sade_sati: bool = False


class TransitRequest(_Model):
    natal: NatalReference
    config: TransitConfiguration = Field(default_factory=TransitConfiguration)
    at_utc: dt.datetime | None = Field(default=None, description="Snapshot instant (aware).")
    window_start_utc: dt.datetime | None = None
    window_end_utc: dt.datetime | None = None


# --------------------------------------------------------------------------
# Output: instant snapshot
# --------------------------------------------------------------------------


class BodyState(_Model):
    body: CelestialBody
    longitude: float
    sign: Rashi
    degree_in_sign: float
    nakshatra: Nakshatra
    pada: int = Field(ge=1, le=4)
    speed_longitude: float
    retrograde: bool
    ephemeris_mode: EphemerisMode
    house_from_moon: int | None = Field(default=None, ge=1, le=12)
    house_from_lagna: int | None = Field(default=None, ge=1, le=12)


class FavourableReadingResult(_Model):
    reading_id: str
    label: EvidenceLabel
    in_favourable_set: bool
    single_source: bool = False
    verification_level: str


class FavourableEvaluation(_Model):
    body: CelestialBody
    house_from_moon: int = Field(ge=1, le=12)
    status: FavourableStatus
    reason_code: TransitReason | None = None
    readings: tuple[FavourableReadingResult, ...]
    attesting_reading_ids: tuple[str, ...] = Field(
        default=(), description="Readings that agree with `status` (empty if not evaluable)."
    )


class VedhaFact(_Model):
    body: CelestialBody
    house_from_moon: int = Field(ge=1, le=12)
    profile_id: str
    status: SectionStatus
    reason_code: TransitReason | None = None
    vedha_house: int | None = Field(default=None, ge=1, le=12)
    vedha_sign: Rashi | None = None
    vedha_present: bool | None = None
    occupants: tuple[CelestialBody, ...] = ()
    exempt_occupants: tuple[CelestialBody, ...] = ()
    node_occupants: tuple[CelestialBody, ...] = ()
    warnings: tuple[str, ...] = ()


class TransitContact(_Model):
    transit_body: CelestialBody
    natal_body: CelestialBody
    kind: ContactKind
    aspect_house_offset: int | None = Field(default=None, ge=2, le=12)
    transit_sign: Rashi
    natal_sign: Rashi


class SadeSatiState(_Model):
    profile_id: str
    in_band: bool
    phase: int | None = Field(default=None, ge=1, le=3)


class TransitSnapshot(_Model):
    at_utc: dt.datetime
    julian_day_ut: float
    states: tuple[BodyState, ...]
    moon_relative_status: SectionStatus
    moon_relative_reason: TransitReason | None = None
    favourable: tuple[FavourableEvaluation, ...] = ()
    vedha: tuple[VedhaFact, ...] = ()
    contacts_status: SectionStatus = SectionStatus.NOT_REQUESTED
    contacts_reason: TransitReason | None = None
    contacts: tuple[TransitContact, ...] = ()
    lagna_status: SectionStatus = SectionStatus.NOT_REQUESTED
    lagna_reason: TransitReason | None = None
    sade_sati: SadeSatiState | None = None


# --------------------------------------------------------------------------
# Output: window and events
# --------------------------------------------------------------------------


class TransitEvent(_Model):
    event_id: str
    kind: EventKind
    body: CelestialBody
    instant_utc: dt.datetime
    julian_day_ut: float
    from_value: str | None = None
    to_value: str | None = None
    longitude: float
    speed_longitude: float
    retrograde: bool
    backward_motion: bool | None = Field(
        default=None, description="For ingress events: True if the sign or Nakshatra index fell."
    )
    contacts_after: tuple[TransitContact, ...] = ()
    evidence_label: EvidenceLabel = EvidenceLabel.ENGINEERING_CONVENTION
    ephemeris_mode: EphemerisMode


class TransitWindow(_Model):
    start_utc: dt.datetime
    end_utc: dt.datetime
    start_snapshot: TransitSnapshot
    events: tuple[TransitEvent, ...]
    event_count: int


# --------------------------------------------------------------------------
# Output: Sade Sati (modern tradition)
# --------------------------------------------------------------------------


class SadeSatiSegment(_Model):
    segment_id: str
    sign: Rashi
    phase: int = Field(ge=1, le=3)
    phase_name: str
    start_utc: dt.datetime | None = Field(
        default=None, description="None if the segment began before the window (clipped)."
    )
    end_utc: dt.datetime | None = Field(
        default=None, description="None if the segment continues past the window (clipped)."
    )
    clipped_at_window_start: bool
    clipped_at_window_end: bool
    entered_by_backward_motion: bool | None = None
    ended_by_backward_motion: bool | None = None


class SadeSatiEpisode(_Model):
    episode_id: str
    segment_ids: tuple[str, ...]
    start_utc: dt.datetime | None = None
    end_utc: dt.datetime | None = None
    clipped_at_window_start: bool
    clipped_at_window_end: bool
    entered_by_backward_motion: bool | None = None
    ended_by_backward_motion: bool | None = None
    retrograde_reentry_of_previous_episode: bool


class SadeSatiFacts(_Model):
    profile_id: str = SADE_SATI_ID
    evidence_label: EvidenceLabel = EvidenceLabel.MODERN_TRADITION
    classical_status: str
    status: SectionStatus
    reason_code: TransitReason | None = None
    natal_moon_sign: Rashi | None = None
    band_signs: tuple[Rashi, ...] = ()
    window_start_utc: dt.datetime | None = None
    window_end_utc: dt.datetime | None = None
    segments: tuple[SadeSatiSegment, ...] = ()
    episodes: tuple[SadeSatiEpisode, ...] = ()


# --------------------------------------------------------------------------
# Output: contract
# --------------------------------------------------------------------------


class TransitProfileIds(_Model):
    reference_profile_id: str
    favourable_reading_ids: tuple[str, ...]
    vedha_profile_id: str | None
    contact_profile_id: str | None
    events_profile_id: str | None
    boundary_profile_id: str
    sade_sati_profile_id: str | None = None
    lagna_profile_id: str | None = None


class NatalSummary(_Model):
    precision: BirthTimeStatus
    moon_sign: Rashi | None = None
    moon_sign_status: SectionStatus
    moon_sign_reason: TransitReason | None = None
    lagna_sign: Rashi | None = None
    natal_planet_count: int = 0


class AccuracyDisclosure(_Model):
    """What the numbers are and are not. Numerical resolution is not accuracy."""

    instants_are_exact: bool = False
    ephemeris_modes: tuple[EphemerisMode, ...]
    zodiac: str
    ayanamsa: str | None
    node_convention: str
    search_tolerance_seconds: float
    time_scale_note: str
    ayanamsa_sensitivity_note: str
    engineering_evidence: str
    evidence_label: EvidenceLabel = EvidenceLabel.ENGINEERING_EVIDENCE


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class TransitFacts(_Model):
    """The complete transit result. For any non-success status every fact
    section is absent and `reason_code` says why; nothing is guessed."""

    system_id: str = SYSTEM_ID
    status: TransitStatus
    reason_code: TransitReason | None = None
    detail: str | None = None
    standards_version: str = TRANSIT_STANDARDS_VERSION
    engine_version: str
    swisseph_version: str | None = None
    boundary_convention: str = BOUNDARY_CONVENTION
    time_base: str = TIME_BASE
    configuration: TransitConfiguration
    profile_ids: TransitProfileIds
    natal: NatalSummary | None = None
    accuracy: AccuracyDisclosure | None = None
    snapshot: TransitSnapshot | None = None
    window: TransitWindow | None = None
    sade_sati: SadeSatiFacts | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[ProvenanceEntry, ...] = ()

    @model_validator(mode="after")
    def _status_contract(self) -> TransitFacts:
        ok = self.status == TransitStatus.SUCCESS
        if ok and self.reason_code is not None:
            raise ValueError("a successful result must not carry a failure reason code")
        if not ok and self.reason_code is None:
            raise ValueError("every failure must carry a machine-readable reason code")
        if not ok and (self.snapshot or self.window or self.sade_sati):
            raise ValueError("a failed result must not carry facts")
        return self
