"""Request and result contracts for Shadbala (Phase 9 WP-F;
`docs/ASTROLOGY_STANDARDS.md` v1.16.0, SB-01 to SB-20).

Component-level results only. A total is reported only when every part is
evaluated, which BPHS Ch. 27 as read does not allow today (SB-17): the
Shadbala Pinda, Sthana and Kala totals say which parts are missing, and the
partial sum of the evaluated components is labelled as such, never as a
Shadbala.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from pandit_astro_engine.models import (
    CelestialBody,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    TimeResolution,
)
from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.shadbala.profiles import (
    PROFILE_ID,
    RAMAN_PROFILE_ID,
    Component,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.shadbala.raman import DrekkanaReading, MoonPakshaReading


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ShadbalaTimePrecision(str, Enum):
    EXACT = "exact"
    UNKNOWN = "unknown"


class ComponentStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"
    NOT_APPLICABLE = "not_applicable"


class ShadbalaReason(str, Enum):
    BIRTH_TIME_UNKNOWN = "birth_time_unknown"
    D1_MOOLATRIKONA_SIGN_VERSUS_DEGREE = "d1_moolatrikona_sign_versus_degree"
    SUNRISE_UNAVAILABLE = "sunrise_unavailable"
    MOON_PHASE_BOUNDARY = "moon_phase_boundary"
    MERCURY_MIXED_ASSOCIATION = "mercury_mixed_association"
    YEAR_MONTH_LORD_METHOD_UNVERIFIED = "year_month_lord_method_unverified"
    HORA_METHOD_NOT_LOCKED = "hora_method_not_locked"
    AYANA_METHOD_CONFLICT = "ayana_method_conflict"
    PLANETARY_WAR_UNDEFINED = "planetary_war_undefined"
    CHESHTA_METHOD_CONFLICT = "cheshta_method_conflict"
    DRIK_FORMULA_AMBIGUOUS = "drik_formula_ambiguous"
    COMPONENT_NOT_EVALUABLE = "component_not_evaluable"
    # Raman profile (v1.21.0)
    PLANETARY_WAR_UNRESOLVED = "planetary_war_unresolved"
    DRIK_NATURE_UNDETERMINED = "drik_nature_undetermined"
    CHESHTA_TABLES_OUT_OF_RANGE = "cheshta_tables_out_of_range"
    # Method policy (v1.22.0)
    METHODOLOGY_READING_NOT_SELECTED = "methodology_reading_not_selected"


class ShadbalaRequest(_Model):
    """One birth instant and place, under the Vedic default profile
    (sidereal, Lahiri, whole-sign houses). `node_convention` affects only
    whether Mercury is joined by a node (Paksha Bala); the Vedic default is
    the mean node."""

    local_datetime: LocalDateTimeInput
    location: Location
    time_precision: ShadbalaTimePrecision
    node_convention: NodeConvention = NodeConvention.MEAN
    allow_moshier_fallback: bool = True


class ComponentResult(_Model):
    component: Component
    status: ComponentStatus
    virupas: float | None = None
    reason: ShadbalaReason | None = None
    detail: str | None = None
    evidence_label: EvidenceLabel


class SaptavargaPlacement(_Model):
    varga: int
    sign: Rashi
    category: str | None = Field(
        default=None, description="moolatrikona, own, great_friend, friend, equal, enemy, ..."
    )
    virupas: float | None = None


class PlanetShadbala(_Model):
    body: CelestialBody
    components: tuple[ComponentResult, ...]
    saptavarga: tuple[SaptavargaPlacement, ...] = ()
    evaluated_subtotal_virupas: float = Field(
        ...,
        description=(
            "Sum of the evaluated leaf components only. Not a Shadbala Pinda: see "
            "not_evaluated_components."
        ),
    )
    evaluated_components: tuple[Component, ...]
    not_evaluated_components: tuple[Component, ...]

    def component(self, component: Component) -> ComponentResult:
        return next(c for c in self.components if c.component is component)


class DayNight(_Model):
    status: ComponentStatus
    is_day: bool | None = None
    period_start_julian_day_ut: float | None = None
    period_end_julian_day_ut: float | None = None
    third: int | None = Field(default=None, description="1, 2 or 3")
    vara_weekday_sunday_zero: int | None = None


class ComponentProvenance(_Model):
    component: Component
    evidence_label: EvidenceLabel
    statement: str
    reference: SourceReference


class ShadbalaFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    profile_id: str = PROFILE_ID
    time_precision: ShadbalaTimePrecision
    time_resolution: TimeResolution
    location: Location
    ayanamsa: str
    node_convention: NodeConvention
    lagna_longitude: float | None
    midheaven_longitude: float | None
    apparent_solar_hours: float | None
    unnata_ghatis: float | None
    day_night: DayNight
    planets: tuple[PlanetShadbala, ...]
    provenance: tuple[ComponentProvenance, ...]
    warnings: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# Modern profile SHADBALA_RAMAN_GRAHA_BHAVA_BALAS (standards v1.21.0)
# --------------------------------------------------------------------------


class RamanShadbalaRequest(_Model):
    """A request for the Raman profile. `drekkana_reading` and
    `moon_paksha_reading` settle two contradictions inside Raman's book and
    have no default (SR-06, SR-09)."""

    local_datetime: LocalDateTimeInput
    location: Location
    time_precision: ShadbalaTimePrecision
    drekkana_reading: DrekkanaReading
    moon_paksha_reading: MoonPakshaReading
    node_convention: NodeConvention = NodeConvention.MEAN
    allow_moshier_fallback: bool = True


class RamanCheshtaDetail(_Model):
    body: CelestialBody
    mean_longitude: float
    sighrocca: float
    true_longitude_raman_frame: float
    reduced_kendra: float


class RamanDrishtiCell(_Model):
    aspected: CelestialBody
    aspecting: CelestialBody
    signed_value: float


class RamanWar(_Model):
    planets: tuple[CelestialBody, CelestialBody]
    separation_degrees: float
    winner: CelestialBody | None = None
    yuddha_virupas: float | None = None
    reason: ShadbalaReason | None = None


class RamanDetails(_Model):
    hindu_date: dt.date | None = None
    condensed_ahargana: int | None = None
    abda_lord: CelestialBody | None = None
    masa_lord: CelestialBody | None = None
    vara_lord: CelestialBody | None = None
    hora_lord: CelestialBody | None = None
    hours_since_sunrise: float | None = None
    krantis: tuple[tuple[CelestialBody, float], ...] = ()
    cheshta_interval_days: float | None = None
    cheshta: tuple[RamanCheshtaDetail, ...] = ()
    drishti: tuple[RamanDrishtiCell, ...] = ()
    wars: tuple[RamanWar, ...] = ()


class RamanShadbalaFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    profile_id: str = RAMAN_PROFILE_ID
    drekkana_reading: DrekkanaReading
    moon_paksha_reading: MoonPakshaReading
    time_precision: ShadbalaTimePrecision
    time_resolution: TimeResolution
    location: Location
    ayanamsa: str
    cheshta_frame_ayanamsa: str
    node_convention: NodeConvention
    lagna_longitude: float | None
    midheaven_longitude: float | None
    apparent_solar_hours: float | None
    unnata_ghatis: float | None
    day_night: DayNight
    planets: tuple[PlanetShadbala, ...]
    totals_in_rupas: tuple[tuple[CelestialBody, float | None], ...]
    details: RamanDetails
    provenance: tuple[ComponentProvenance, ...]
    warnings: tuple[str, ...] = ()
