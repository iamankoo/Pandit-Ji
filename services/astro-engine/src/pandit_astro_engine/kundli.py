"""The Kundli calculation service facade -- Phase 5 (Birth Chart / Kundli
Engine).

    AstronomicalCalculationRequest -> KundliCalculationService -> Kundli

Wraps Phase 4's `AstronomicalCalculationService` rather than duplicating
any Swiss Ephemeris call: the only new ephemeris primitive Phase 5 needs
(the Ascendant) is added to `ephemeris.py`, the same single adapter
boundary Phase 4 established.
"""

from __future__ import annotations

from pandit_astro_engine import ephemeris
from pandit_astro_engine._version import __version__
from pandit_astro_engine.aspects import aspected_houses
from pandit_astro_engine.dignity import evaluate_dignity
from pandit_astro_engine.kundli_models import (
    DivisionalChart,
    DivisionalPlanetPlacement,
    HouseInfo,
    Kundli,
    KundliMetadata,
    KundliPlanet,
    NakshatraPlacement,
    RashiPlacement,
)
from pandit_astro_engine.lordship import sign_lord
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationResult,
    CelestialBody,
    PlanetState,
    ZodiacType,
)
from pandit_astro_engine.nakshatra import nakshatra_position
from pandit_astro_engine.rashi import (
    degree_within_sign,
    rashi_from_index,
    rashi_index,
    sign_index_from_longitude,
)
from pandit_astro_engine.service import AstronomicalCalculationService
from pandit_astro_engine.vargas import SUPPORTED_VARGAS, calculate_varga_sign

STANDARDS_VERSION = "1.3.0"


class KundliCalculationService:
    """Stateless facade, matching `AstronomicalCalculationService`'s shape.
    Accepts an existing astronomical service instance so callers who already
    hold one (e.g. to share ephemeris-path configuration) never trigger a
    second, differently-configured one."""

    def __init__(self, astronomical_service: AstronomicalCalculationService | None = None) -> None:
        self._astronomical_service = astronomical_service or AstronomicalCalculationService()

    def calculate(self, request: AstronomicalCalculationRequest) -> Kundli:
        astronomical = self._astronomical_service.calculate(request)

        ascendant_longitude = ephemeris.calculate_ascendant(
            astronomical.metadata.time_resolution.julian_day_ut,
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            sidereal=request.config.zodiac == ZodiacType.SIDEREAL,
        )
        ascendant_sign_index = sign_index_from_longitude(ascendant_longitude)

        planet_states = _collect_planet_states(astronomical)

        planets = [
            _build_kundli_planet(body, state, ascendant_sign_index)
            for body, state in planet_states.items()
        ]

        charts = {
            varga: _build_divisional_chart(varga, planet_states, ascendant_longitude)
            for varga in SUPPORTED_VARGAS
        }

        moon_state = planet_states.get(CelestialBody.MOON)
        chandra_chart = _build_chandra_chart(planet_states, moon_state) if moon_state else None

        return Kundli(
            astronomical=astronomical,
            lagna_longitude=ascendant_longitude,
            lagna=RashiPlacement(
                rashi=rashi_from_index(ascendant_sign_index),
                degree_in_sign=degree_within_sign(ascendant_longitude),
            ),
            houses=_build_houses(ascendant_sign_index),
            planets=planets,
            charts=charts,
            chandra_chart=chandra_chart,
            metadata=KundliMetadata(
                engine_version=__version__, standards_version=STANDARDS_VERSION
            ),
        )


def _collect_planet_states(astronomical: CalculationResult) -> dict[CelestialBody, PlanetState]:
    states: dict[CelestialBody, PlanetState] = {}
    for body in CelestialBody:
        state = getattr(astronomical.planets, body.value)
        if state is not None:
            states[body] = state
    return states


def _build_houses(ascendant_sign_index: int) -> list[HouseInfo]:
    houses = []
    for house_number in range(1, 13):
        rashi = rashi_from_index(ascendant_sign_index + (house_number - 1))
        houses.append(HouseInfo(house=house_number, rashi=rashi, lord=sign_lord(rashi)))
    return houses


def _build_kundli_planet(
    body: CelestialBody, state: PlanetState, ascendant_sign_index: int
) -> KundliPlanet:
    sign_index = sign_index_from_longitude(state.longitude)
    rashi = rashi_from_index(sign_index)
    degree_in_sign = degree_within_sign(state.longitude)
    house = ((sign_index - ascendant_sign_index) % 12) + 1
    nakshatra = nakshatra_position(state.longitude)

    return KundliPlanet(
        body=body,
        longitude=state.longitude,
        rashi=rashi,
        degree_in_sign=degree_in_sign,
        house=house,
        nakshatra=NakshatraPlacement(
            nakshatra=nakshatra.nakshatra,
            pada=nakshatra.pada,
            lord=nakshatra.lord,
            near_boundary=nakshatra.near_boundary,
        ),
        dignity=evaluate_dignity(body, rashi, degree_in_sign),
        retrograde=state.retrograde,
        combust=state.combustion.is_combust if state.combustion is not None else None,
        aspected_houses=aspected_houses(body, house),
        ephemeris_mode=state.ephemeris_mode,
    )


def _build_divisional_chart(
    varga: int, planet_states: dict[CelestialBody, PlanetState], ascendant_longitude: float
) -> DivisionalChart:
    ascendant_rashi = calculate_varga_sign(varga, ascendant_longitude)
    ascendant_sign_index = rashi_index(ascendant_rashi)

    planets = []
    for body, state in planet_states.items():
        varga_rashi = calculate_varga_sign(varga, state.longitude)
        varga_sign_index = rashi_index(varga_rashi)
        house = ((varga_sign_index - ascendant_sign_index) % 12) + 1
        planets.append(
            DivisionalPlanetPlacement(
                body=body, rashi=varga_rashi, house=house, house_lord=sign_lord(varga_rashi)
            )
        )

    return DivisionalChart(
        varga=varga,
        label=f"D{varga}",
        ascendant_rashi=ascendant_rashi,
        houses=_build_houses(ascendant_sign_index),
        planets=planets,
    )


def _build_chandra_chart(
    planet_states: dict[CelestialBody, PlanetState], moon_state: PlanetState
) -> DivisionalChart:
    """Chandra Lagna: the same whole-sign methodology as D1, but with the
    Moon's own sign as house 1 instead of the Ascendant (docs/ASTROLOGY_STANDARDS.md
    "Default Vedic profile" whole-sign convention, applied with the Moon as
    the reference point rather than the Ascendant)."""
    ascendant_sign_index = sign_index_from_longitude(moon_state.longitude)

    planets = []
    for body, state in planet_states.items():
        sign_index = sign_index_from_longitude(state.longitude)
        rashi = rashi_from_index(sign_index)
        house = ((sign_index - ascendant_sign_index) % 12) + 1
        planets.append(
            DivisionalPlanetPlacement(
                body=body, rashi=rashi, house=house, house_lord=sign_lord(rashi)
            )
        )

    return DivisionalChart(
        varga=1,
        label="Chandra Lagna",
        ascendant_rashi=rashi_from_index(ascendant_sign_index),
        houses=_build_houses(ascendant_sign_index),
        planets=planets,
    )
