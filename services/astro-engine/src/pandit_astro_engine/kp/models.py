"""Request and result contracts for the KP module (Phase 9 WP-E;
`docs/ASTROLOGY_STANDARDS.md` v1.15.0, KP-01 to KP-16).

Facts and provenance only: KP positions, cusps, star/sub/sub-sub lords,
house significators and Ruling Planets. No interpretation, no judgment of a
horary question.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.kp.constants import (
    KP_TABLE_SIZE,
    DayLordConvention,
    KpReason,
    KpStatus,
    KpTimePrecision,
)
from pandit_astro_engine.kp.profiles import (
    AYANAMSA_PROFILES,
    DEFAULT_AYANAMSA_PROFILE_ID,
    HOUSES_PLACIDUS_SIDEREAL_ID,
    SUBDIVISION_ID,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.kp.ruling_planets import RetrogradeStarFlag, RulingRole
from pandit_astro_engine.models import (
    CelestialBody,
    EphemerisMode,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    TimeResolution,
)
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.rashi import Rashi


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_ayanamsa(profile_id: str) -> None:
    if profile_id not in AYANAMSA_PROFILES:
        raise ValueError(
            f"unknown ayanamsa_profile_id {profile_id!r}; supported: {sorted(AYANAMSA_PROFILES)}"
        )


class KpChartRequest(_Model):
    """A KP natal chart. `node_convention` has no default (the KP Readers do
    not fix mean or true nodes)."""

    local_datetime: LocalDateTimeInput
    location: Location
    time_precision: KpTimePrecision
    node_convention: NodeConvention
    ayanamsa_profile_id: str = DEFAULT_AYANAMSA_PROFILE_ID
    allow_moshier_fallback: bool = True

    @model_validator(mode="after")
    def _check(self) -> KpChartRequest:
        _check_ayanamsa(self.ayanamsa_profile_id)
        return self


class KpRulingPlanetsRequest(_Model):
    """Ruling Planets of a moment of judgment. `day_lord_convention` has no
    default (KP-10)."""

    local_datetime: LocalDateTimeInput
    location: Location
    node_convention: NodeConvention
    day_lord_convention: DayLordConvention
    ayanamsa_profile_id: str = DEFAULT_AYANAMSA_PROFILE_ID
    allow_moshier_fallback: bool = True

    @model_validator(mode="after")
    def _check(self) -> KpRulingPlanetsRequest:
        _check_ayanamsa(self.ayanamsa_profile_id)
        return self


class KpHoraryRequest(_Model):
    """A KP horary chart for the querent's number 1-249 at the moment and
    place of judgment."""

    horary_number: int = Field(..., ge=1, le=KP_TABLE_SIZE)
    local_datetime: LocalDateTimeInput
    location: Location
    node_convention: NodeConvention
    day_lord_convention: DayLordConvention
    ayanamsa_profile_id: str = DEFAULT_AYANAMSA_PROFILE_ID
    allow_moshier_fallback: bool = True

    @model_validator(mode="after")
    def _check(self) -> KpHoraryRequest:
        _check_ayanamsa(self.ayanamsa_profile_id)
        return self


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class KpProfileIds(_Model):
    ayanamsa_profile_id: str
    house_profile_id: str = HOUSES_PLACIDUS_SIDEREAL_ID
    subdivision_profile_id: str = SUBDIVISION_ID
    significator_profile_id: str | None = None
    ruling_planets_profile_id: str | None = None
    horary_profile_id: str | None = None
    node_convention: NodeConvention
    day_lord_convention: DayLordConvention | None = None


class KpLordship(_Model):
    """Sign, star, sub and sub-sub lords of one longitude. Boundaries are in
    degrees; `near_boundary` flags a longitude within 1e-6 degrees of its
    sub-sub boundary."""

    sign: Rashi
    sign_lord: CelestialBody
    nakshatra: Nakshatra
    star_lord: CelestialBody
    sub_lord: CelestialBody
    sub_sub_lord: CelestialBody
    sub_start: float
    sub_end: float
    near_boundary: bool


class KpPlanet(_Model):
    body: CelestialBody
    longitude: float = Field(..., description="Sidereal longitude, KP ayanamsa, [0, 360).")
    speed_longitude: float
    retrograde: bool
    node_convention: NodeConvention | None = None
    ephemeris_mode: EphemerisMode
    lordship: KpLordship | None = Field(
        default=None, description="None when the birth time is unknown (KP-12)."
    )
    house: int | None = None


class KpCusp(_Model):
    house: int
    longitude: float
    lordship: KpLordship


class KpCusps(_Model):
    status: KpStatus
    reason: KpReason | None = None
    detail: str | None = None
    cusps: tuple[KpCusp, ...] = ()
    polar_limit_degrees: float | None = None


class KpHouseSignificators(_Model):
    house: int
    level_a_in_star_of_occupants: tuple[CelestialBody, ...]
    level_b_occupants: tuple[CelestialBody, ...]
    level_c_in_star_of_lord: tuple[CelestialBody, ...]
    level_d_lord: tuple[CelestialBody, ...]


class KpPlanetSignification(_Model):
    body: CelestialBody
    houses: tuple[int, ...]


class KpSignificators(_Model):
    status: KpStatus
    reason: KpReason | None = None
    houses: tuple[KpHouseSignificators, ...] = ()
    planets: tuple[KpPlanetSignification, ...] = ()
    not_evaluated: tuple[str, ...] = (
        "level_e_conjunction",
        "level_f_aspect",
        "node_agency",
    )


class KpRulingPlanet(_Model):
    body: CelestialBody
    role: RulingRole
    represents: CelestialBody | None = None
    star_lord_of_body: CelestialBody
    retrograde_star_flag: RetrogradeStarFlag


class KpRulingPlanets(_Model):
    status: KpStatus
    reason: KpReason | None = None
    weekday_sunday_zero: int | None = None
    ascendant_longitude: float | None = None
    members: tuple[KpRulingPlanet, ...] = ()


class KpChartFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    swisseph_version: str
    ephemeris_path: str | None
    profiles: KpProfileIds
    time_precision: KpTimePrecision
    time_resolution: TimeResolution
    location: Location
    ayanamsa_degrees: float
    planets: tuple[KpPlanet, ...]
    cusps: KpCusps
    significators: KpSignificators
    provenance: tuple[ProvenanceEntry, ...]
    warnings: tuple[str, ...] = ()


class KpRulingPlanetsFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    profiles: KpProfileIds
    time_resolution: TimeResolution
    location: Location
    ruling_planets: KpRulingPlanets
    provenance: tuple[ProvenanceEntry, ...]
    warnings: tuple[str, ...] = ()


class KpHoraryEntry(_Model):
    number: int
    sign: Rashi
    sign_lord: CelestialBody
    nakshatra: Nakshatra
    star_lord: CelestialBody
    sub_lord: CelestialBody
    start: float
    end: float


class KpHoraryFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    swisseph_version: str
    ephemeris_path: str | None
    profiles: KpProfileIds
    time_resolution: TimeResolution
    location: Location
    ayanamsa_degrees: float
    entry: KpHoraryEntry
    planets: tuple[KpPlanet, ...]
    cusps: KpCusps
    significators: KpSignificators
    ruling_planets: KpRulingPlanets
    provenance: tuple[ProvenanceEntry, ...]
    warnings: tuple[str, ...] = ()
