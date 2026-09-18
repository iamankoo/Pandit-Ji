"""The astronomical calculation service facade (Phase 4 prompt §23).

    AstronomicalCalculationRequest -> AstronomicalCalculationService -> CalculationResult

Pure/stateless from the caller's perspective (Phase 4 prompt §41): no
database, no cache, no queue, no auth -- callable directly from tests or
any future service. HTTP exposure (if any) belongs in `server/`, which
depends on this, never the reverse.
"""

from __future__ import annotations

from pandit_astro_engine import ephemeris, planets, solar_events, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.config import Settings
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationMetadata,
    CalculationResult,
    CelestialBody,
    Planets,
    PlanetState,
    SolarEvent,
    SolarEvents,
    SolarEventStatus,
)

_UNSET = object()


class AstronomicalCalculationService:
    """Stateless facade. Reads `Settings().ephemeris_path` from the
    environment at construction time unless `ephemeris_path` is explicitly
    passed (mainly for tests, including explicitly passing `None` to force
    the Moshier fallback regardless of the environment)."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved_path = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved_path)

    def calculate(self, request: AstronomicalCalculationRequest) -> CalculationResult:
        utc_datetime, time_resolution = timezones.resolve_local_datetime(request.local_datetime)

        jd_et, jd_ut = ephemeris.utc_to_julian_day(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            utc_datetime.hour,
            utc_datetime.minute,
            utc_datetime.second + utc_datetime.microsecond / 1_000_000,
        )
        time_resolution = time_resolution.model_copy(
            update={"julian_day_ut": jd_ut, "julian_day_et": jd_et}
        )

        planet_states, ephemeris_mode = planets.calculate_all_bodies(
            jd_ut, request.config, request.bodies
        )

        solar_events_result = (
            solar_events.calculate_solar_events(jd_ut, request.location)
            if request.include_solar_events
            else SolarEvents(
                sunrise=SolarEvent(status=SolarEventStatus.NOT_CALCULATED),
                sunset=SolarEvent(status=SolarEventStatus.NOT_CALCULATED),
            )
        )

        planets_model = _build_planets_model(planet_states)

        metadata = CalculationMetadata(
            engine_version=__version__,
            swisseph_version=ephemeris.swisseph_version(),
            ephemeris_mode=ephemeris_mode,
            ephemeris_path=ephemeris.configured_ephemeris_path(),
            calculation_config=request.config,
            time_resolution=time_resolution,
            location=request.location,
        )

        return CalculationResult(
            planets=planets_model,
            solar_events=solar_events_result,
            metadata=metadata,
        )


def _build_planets_model(planet_states: dict[CelestialBody, PlanetState]) -> Planets:
    return Planets(
        sun=planet_states.get(CelestialBody.SUN),
        moon=planet_states.get(CelestialBody.MOON),
        mars=planet_states.get(CelestialBody.MARS),
        mercury=planet_states.get(CelestialBody.MERCURY),
        jupiter=planet_states.get(CelestialBody.JUPITER),
        venus=planet_states.get(CelestialBody.VENUS),
        saturn=planet_states.get(CelestialBody.SATURN),
        rahu=planet_states.get(CelestialBody.RAHU),
        ketu=planet_states.get(CelestialBody.KETU),
    )
