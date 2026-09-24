"""Request and result contracts for the Western module (Phase 9 WP-D;
`docs/ASTROLOGY_STANDARDS.md` v1.14.0, WD-01 to WD-20).

Facts and provenance only: positions, signs, Placidus cusps and house
placement, and aspects with orbs and motion. No interpretation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.models import (
    EphemerisMode,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    TimeResolution,
)
from pandit_astro_engine.western.constants import AspectType, TropicalSign, WesternBody
from pandit_astro_engine.western.profiles import (
    ASPECT_SET_PROFILES,
    BODY_PROFILES,
    DEFAULT_ASPECT_SET_PROFILE_ID,
    DEFAULT_BODY_PROFILE_ID,
    DEFAULT_HOUSE_PROFILE_ID,
    DEFAULT_ORB_PROFILE_ID,
    HOUSE_PROFILES,
    MOTION_INSTANTANEOUS_ID,
    MOTION_PROFILES,
    ORB_PROFILES,
    ZODIAC_TROPICAL_ID,
    EvidenceLabel,
    SourceReference,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WesternTimePrecision(str, Enum):
    """EXACT: the birth time is known. UNKNOWN: only the date is known; the
    supplied clock time is a placeholder, so nothing time-sensitive
    (houses, angles, house placement, aspects) is evaluated (WD-15)."""

    EXACT = "exact"
    UNKNOWN = "unknown"


class WesternStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class WesternReason(str, Enum):
    BIRTH_TIME_UNKNOWN = "birth_time_unknown"
    PLACIDUS_POLAR_CIRCLE = "placidus_polar_circle"
    PLACIDUS_NOT_COMPUTABLE = "placidus_not_computable"
    ORB_NOT_DEFINED_FOR_BODY = "orb_not_defined_for_body"
    RELATIVE_MOTION_ZERO = "relative_motion_zero"


class MotionState(str, Enum):
    APPLYING = "applying"
    SEPARATING = "separating"
    EXACT = "exact"
    NOT_EVALUABLE = "not_evaluable"


class WesternChartRequest(_Model):
    """One natal instant and place. Profile fields default to the documented
    engineering defaults (WD-17); whatever is used is recorded in the result.
    `node_convention` has no default and is required exactly when the body
    profile includes the nodes."""

    local_datetime: LocalDateTimeInput
    location: Location
    time_precision: WesternTimePrecision
    body_profile_id: str = DEFAULT_BODY_PROFILE_ID
    house_profile_id: str = DEFAULT_HOUSE_PROFILE_ID
    aspect_set_profile_id: str = DEFAULT_ASPECT_SET_PROFILE_ID
    orb_profile_id: str = DEFAULT_ORB_PROFILE_ID
    motion_profile_id: str = MOTION_INSTANTANEOUS_ID
    node_convention: NodeConvention | None = None
    allow_moshier_fallback: bool = True

    @model_validator(mode="after")
    def _check_profiles(self) -> WesternChartRequest:
        registries: tuple[tuple[str, str, dict[str, object]], ...] = (
            ("body_profile_id", self.body_profile_id, dict(BODY_PROFILES)),
            ("house_profile_id", self.house_profile_id, dict(HOUSE_PROFILES)),
            ("aspect_set_profile_id", self.aspect_set_profile_id, dict(ASPECT_SET_PROFILES)),
            ("orb_profile_id", self.orb_profile_id, dict(ORB_PROFILES)),
            ("motion_profile_id", self.motion_profile_id, dict(MOTION_PROFILES)),
        )
        for field, value, registry in registries:
            if value not in registry:
                raise ValueError(f"unknown {field} {value!r}; supported: {sorted(registry)}")
        needs_nodes = BODY_PROFILES[self.body_profile_id].requires_node_convention
        if needs_nodes and self.node_convention is None:
            raise ValueError(
                f"{self.body_profile_id} includes the lunar nodes; node_convention must be "
                "given explicitly (mean or true) and is never defaulted"
            )
        if not needs_nodes and self.node_convention is not None:
            raise ValueError(f"node_convention was given but {self.body_profile_id} has no nodes")
        return self


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class ProfileIds(_Model):
    zodiac_profile_id: str = ZODIAC_TROPICAL_ID
    body_profile_id: str
    house_profile_id: str
    aspect_set_profile_id: str
    orb_profile_id: str
    motion_profile_id: str
    node_convention: NodeConvention | None


class WesternBodyPosition(_Model):
    body: WesternBody
    longitude: float = Field(..., description="Tropical ecliptic longitude of date, [0, 360).")
    latitude: float
    speed_longitude: float = Field(..., description="Degrees per day; sign preserved.")
    retrograde: bool
    sign: TropicalSign
    degree_in_sign: float
    house: int | None = Field(default=None, description="Placidus house 1-12, if evaluable.")
    ephemeris_mode: EphemerisMode


class WesternHouses(_Model):
    status: WesternStatus
    reason: WesternReason | None = None
    detail: str | None = None
    cusps: tuple[float, ...] | None = Field(
        default=None, description="Cusps of houses 1-12 in order, tropical degrees."
    )
    ascendant: float | None = None
    midheaven: float | None = None
    ascendant_sign: TropicalSign | None = None
    midheaven_sign: TropicalSign | None = None
    polar_limit_degrees: float | None = Field(
        default=None, description="90 minus the true obliquity of date (WD-07)."
    )


class WesternAspect(_Model):
    body_a: WesternBody
    body_b: WesternBody
    aspect: AspectType
    exact_angle: float
    separation: float = Field(..., description="Shorter arc between the bodies, [0, 180].")
    deviation: float = Field(..., description="|separation - exact_angle|.")
    orb_allowed: float
    motion_state: MotionState
    motion_reason: WesternReason | None = None


class NotEvaluablePair(_Model):
    body_a: WesternBody
    body_b: WesternBody
    reason: WesternReason


class WesternAspects(_Model):
    status: WesternStatus
    reason: WesternReason | None = None
    aspects: tuple[WesternAspect, ...] = ()
    not_evaluable_pairs: tuple[NotEvaluablePair, ...] = ()


class WesternChartFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    swisseph_version: str
    ephemeris_path: str | None
    profiles: ProfileIds
    time_precision: WesternTimePrecision
    time_resolution: TimeResolution
    location: Location
    bodies: tuple[WesternBodyPosition, ...]
    houses: WesternHouses
    aspects: WesternAspects
    provenance: tuple[ProvenanceEntry, ...]
    warnings: tuple[str, ...] = ()
