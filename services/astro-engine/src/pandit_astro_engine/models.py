"""Typed request/response contracts for the astronomical calculation engine.

Phase 4 scope only (docs/ARCHITECTURE.md "Astrology Engine Architecture"):
astronomical state, not chart/Kundli domain fields. Do not add houses,
nakshatras, rashis-as-placements, dignities, or lords here -- those are
Phase 5.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

# --------------------------------------------------------------------------
# Canonical identifiers (docs/ASTROLOGY_STANDARDS.md keeps these stable and
# machine-readable; presentation-layer aliases belong outside this engine)
# --------------------------------------------------------------------------


class CelestialBody(str, Enum):
    SUN = "sun"
    MOON = "moon"
    MARS = "mars"
    MERCURY = "mercury"
    JUPITER = "jupiter"
    VENUS = "venus"
    SATURN = "saturn"
    RAHU = "rahu"
    KETU = "ketu"


class ZodiacType(str, Enum):
    SIDEREAL = "sidereal"
    TROPICAL = "tropical"


class Ayanamsa(str, Enum):
    LAHIRI = "lahiri"


class NodeConvention(str, Enum):
    """docs/ASTROLOGY_STANDARDS.md 'Node convention (Rahu / Ketu)' -- both
    supported, never silently mixed; MEAN is the Vedic default."""

    MEAN = "mean"
    TRUE = "true"


class EphemerisMode(str, Enum):
    """What the underlying Swiss Ephemeris call actually used -- always
    reported explicitly, never left for the caller to infer (see
    services/astro-engine/README.md 'Ephemeris data')."""

    SWISS_EPHEMERIS_FILES = "swiss_ephemeris_files"
    MOSHIER = "moshier"
    JPL = "jpl"


class DisambiguationPolicy(str, Enum):
    """How to resolve a local time that is ambiguous or nonexistent under
    the given timezone's DST rules. STRICT (default) raises instead of
    silently picking one -- see errors.AmbiguousLocalTimeError /
    NonexistentLocalTimeError."""

    STRICT = "strict"
    EARLIER = "earlier"
    LATER = "later"


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------


class Location(BaseModel):
    """Coordinates only -- this engine consumes coordinates, it never
    geocodes a place name (docs/ARCHITECTURE.md "Location standards" /
    Phase 4 prompt §11)."""

    latitude: float = Field(..., description="Degrees, -90..90, north positive.")
    longitude: float = Field(..., description="Degrees, -180..180, east positive.")
    altitude_meters: float = Field(default=0.0, description="Meters above sea level.")

    @field_validator("latitude")
    @classmethod
    def _validate_latitude(cls, value: float) -> float:
        from pandit_astro_engine.errors import InvalidLatitudeError

        if not -90.0 <= value <= 90.0:
            raise InvalidLatitudeError(value)
        return value

    @field_validator("longitude")
    @classmethod
    def _validate_longitude(cls, value: float) -> float:
        from pandit_astro_engine.errors import InvalidLongitudeError

        if not -180.0 <= value <= 180.0:
            raise InvalidLongitudeError(value)
        return value


class LocalDateTimeInput(BaseModel):
    """Local civil time -- deliberately not a single `datetime`, so the
    timezone identifier travels with it explicitly rather than relying on
    the caller to have attached the right tzinfo already."""

    year: int
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(default=0, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    second: float = Field(default=0.0, ge=0.0, lt=60.0)
    timezone: str = Field(..., description="IANA timezone identifier, e.g. 'Asia/Kolkata'.")
    disambiguation: DisambiguationPolicy = DisambiguationPolicy.STRICT


class CalculationConfig(BaseModel):
    """Everything needed to answer 'what exactly produced this number'
    (docs/ASTROLOGY_STANDARDS.md §Reproducibility)."""

    zodiac: ZodiacType = ZodiacType.SIDEREAL
    ayanamsa: Ayanamsa | None = Ayanamsa.LAHIRI
    node_convention: NodeConvention = NodeConvention.MEAN
    combustion_standard: str = "brihat_parashara_hora_shastra_v1"
    allow_moshier_fallback: bool = Field(
        default=True,
        description=(
            "If no Swiss Ephemeris data files are configured/found, allow the "
            "Moshier analytical fallback (explicitly flagged in output metadata) "
            "rather than raising EphemerisDataUnavailableError."
        ),
    )

    @model_validator(mode="after")
    def _ayanamsa_matches_zodiac(self) -> CalculationConfig:
        from pandit_astro_engine.errors import UnsupportedConfigurationError

        if self.zodiac == ZodiacType.TROPICAL and self.ayanamsa is not None:
            raise UnsupportedConfigurationError(
                "ayanamsa must not be set when zodiac='tropical' (tropical has no "
                "ayanamsa/precession correction by definition) -- got "
                f"ayanamsa={self.ayanamsa!r}."
            )
        if self.zodiac == ZodiacType.SIDEREAL and self.ayanamsa is None:
            raise UnsupportedConfigurationError(
                "ayanamsa must be set when zodiac='sidereal'; it must never be silently defaulted."
            )
        return self


class AstronomicalCalculationRequest(BaseModel):
    local_datetime: LocalDateTimeInput
    location: Location
    config: CalculationConfig = Field(default_factory=CalculationConfig)
    bodies: list[CelestialBody] = Field(
        default_factory=lambda: list(CelestialBody),
        description="Which bodies to calculate; defaults to all nine.",
    )
    include_solar_events: bool = True


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


class DegreeComponents(BaseModel):
    """Degree/minute/second decomposition of an *absolute* ecliptic
    longitude (0-360). This is NOT sign-relative degree (that is a Phase 5
    Rashi-placement concept) -- purely arithmetic on the precise longitude."""

    degrees: int
    minutes: int
    seconds: float

    @staticmethod
    def from_longitude(longitude: float) -> DegreeComponents:
        whole_degrees = int(longitude)
        fractional = longitude - whole_degrees
        minutes_float = fractional * 60
        whole_minutes = int(minutes_float)
        seconds = (minutes_float - whole_minutes) * 60
        return DegreeComponents(degrees=whole_degrees, minutes=whole_minutes, seconds=seconds)


class CombustionStatus(BaseModel):
    """docs/ASTROLOGY_STANDARDS.md 'Combustion standard' -- a derived status,
    not raw ephemeris output. None for Sun/Rahu/Ketu (not evaluated)."""

    is_combust: bool
    angular_separation_degrees: float
    threshold_degrees: float
    standard: str


class PlanetState(BaseModel):
    body: CelestialBody
    longitude: float = Field(..., description="Absolute ecliptic longitude, degrees, [0, 360).")
    latitude: float = Field(..., description="Ecliptic latitude, degrees (not geographic).")
    distance_au: float
    speed_longitude: float = Field(..., description="Degrees/day in longitude; sign preserved.")
    speed_latitude: float
    retrograde: bool
    degree_components: DegreeComponents
    combustion: CombustionStatus | None = None
    node_convention: NodeConvention | None = Field(
        default=None, description="Set only for RAHU/KETU."
    )
    ephemeris_mode: EphemerisMode = Field(
        ...,
        description=(
            "What actually produced *this body's* position. Reported per-body (not just "
            "in the top-level metadata) because e.g. the lunar node is computed analytically "
            "and may report a different mode than the planets in the same calculation -- "
            "never blur that into one aggregate claim."
        ),
    )


class Planets(BaseModel):
    """One field per canonical body. `None` for a body that was not
    requested (`AstronomicalCalculationRequest.bodies` may be a subset) --
    never a missing key, so callers can always check `result.planets.mars`
    directly regardless of what was requested."""

    sun: PlanetState | None = None
    moon: PlanetState | None = None
    mars: PlanetState | None = None
    mercury: PlanetState | None = None
    jupiter: PlanetState | None = None
    venus: PlanetState | None = None
    saturn: PlanetState | None = None
    rahu: PlanetState | None = None
    ketu: PlanetState | None = None


class SolarEventStatus(str, Enum):
    OCCURRED = "occurred"
    CIRCUMPOLAR_NO_EVENT = "circumpolar_no_event"
    NOT_CALCULATED = "not_calculated"


class SolarEvent(BaseModel):
    status: SolarEventStatus
    utc_datetime: datetime | None = None
    local_datetime: datetime | None = None
    julian_day_ut: float | None = None


class SolarEvents(BaseModel):
    sunrise: SolarEvent
    sunset: SolarEvent


class TimeResolution(BaseModel):
    """Distinguishes local civil time / UTC / ephemeris time explicitly
    (Phase 4 prompt §9)."""

    input_local_datetime: str = Field(..., description="ISO-8601, naive, exactly as given.")
    timezone: str
    utc_offset_seconds: int
    utc_datetime: datetime
    julian_day_ut: float = Field(..., description="Julian day, Universal Time (UT1).")
    julian_day_et: float = Field(..., description="Julian day, Ephemeris/Terrestrial Time.")
    dst_active: bool
    was_ambiguous: bool
    was_nonexistent: bool
    disambiguation_applied: DisambiguationPolicy | None = None


class CalculationMetadata(BaseModel):
    engine_version: str
    swisseph_version: str
    ephemeris_mode: EphemerisMode
    ephemeris_path: str | None
    calculation_config: CalculationConfig
    time_resolution: TimeResolution
    location: Location


class CalculationResult(BaseModel):
    planets: Planets
    solar_events: SolarEvents
    metadata: CalculationMetadata
