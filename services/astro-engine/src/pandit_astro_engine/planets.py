"""Per-body calculation orchestration: combines the raw ephemeris adapter
output with the derived-status layers (retrograde, combustion, degree
decomposition) into a `PlanetState`. No direct `swisseph` import here --
everything ephemeris-specific goes through `ephemeris.py` (Phase 4 prompt
§38's adapter boundary).

Retrograde semantics (Phase 4 prompt §16): Swiss Ephemeris's `calc_ut` speed
value is the rate of change of ecliptic longitude in degrees/day; a negative
value *is* the definition of retrograde apparent motion (the body's ecliptic
longitude is decreasing) for every naturally-orbiting body, and this is
documented Swiss Ephemeris behavior, not an inferred heuristic. Applied
uniformly to Rahu/Ketu too: the Mean Node's speed is definitionally always
negative (continuous slow regression), and the True Node's occasional
positive-speed stations are a real, if rare, astronomical event under the
same speed-sign semantics -- there is no second, different "retrograde"
concept for nodes that this engine needs to invent.
"""

from __future__ import annotations

import swisseph as swe

from pandit_astro_engine import combustion, ephemeris
from pandit_astro_engine.models import (
    CalculationConfig,
    CelestialBody,
    CombustionStatus,
    DegreeComponents,
    EphemerisMode,
    NodeConvention,
    PlanetState,
    ZodiacType,
)

_NODE_SWE_ID = {
    NodeConvention.MEAN: swe.MEAN_NODE,
    NodeConvention.TRUE: swe.TRUE_NODE,
}


def _to_planet_state(
    body: CelestialBody,
    raw: ephemeris.RawBodyPosition,
    *,
    node_convention: NodeConvention | None = None,
) -> PlanetState:
    retrograde = raw.speed_longitude < 0
    return PlanetState(
        body=body,
        ephemeris_mode=raw.mode,
        longitude=raw.longitude,
        latitude=raw.latitude,
        distance_au=raw.distance_au,
        speed_longitude=raw.speed_longitude,
        speed_latitude=raw.speed_latitude,
        retrograde=retrograde,
        degree_components=DegreeComponents.from_longitude(raw.longitude),
        node_convention=node_convention,
    )


_COMBUSTION_ELIGIBLE = (
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
)


def calculate_all_bodies(
    julian_day_ut: float,
    config: CalculationConfig,
    bodies: list[CelestialBody],
) -> tuple[dict[CelestialBody, PlanetState], EphemerisMode]:
    """Returns (states keyed by body, the ephemeris mode actually used --
    identical across bodies within one call, reported once). Only the
    requested `bodies` appear in the returned dict, but dependencies
    (Rahu for Ketu; Sun for any combustion-eligible planet) are always
    computed internally when needed, even if not themselves requested,
    since Ketu/combustion must never silently go missing just because
    their input wasn't separately asked for.
    """
    sidereal = config.zodiac == ZodiacType.SIDEREAL
    if sidereal:
        assert config.ayanamsa is not None  # enforced by CalculationConfig validator
        ephemeris.set_sidereal_mode(config.ayanamsa)

    requested = set(bodies)
    needs_rahu = CelestialBody.RAHU in requested or CelestialBody.KETU in requested
    needs_sun = bool(requested & set(_COMBUSTION_ELIGIBLE)) or CelestialBody.SUN in requested

    to_calculate: set[CelestialBody] = set(requested) - {CelestialBody.KETU}
    if needs_rahu:
        to_calculate.add(CelestialBody.RAHU)
    if needs_sun:
        to_calculate.add(CelestialBody.SUN)

    raw_by_body: dict[CelestialBody, ephemeris.RawBodyPosition] = {}
    modes: set[EphemerisMode] = set()

    for body in to_calculate:
        swe_id = (
            _NODE_SWE_ID[config.node_convention]
            if body == CelestialBody.RAHU
            else ephemeris.SWE_BODY_ID[body.value]
        )
        raw = ephemeris.calculate_body(
            julian_day_ut,
            swe_id,
            sidereal=sidereal,
            allow_moshier_fallback=config.allow_moshier_fallback,
        )
        raw_by_body[body] = raw
        modes.add(raw.mode)

    computed: dict[CelestialBody, PlanetState] = {}
    for body, raw in raw_by_body.items():
        node_convention = config.node_convention if body == CelestialBody.RAHU else None
        computed[body] = _to_planet_state(body, raw, node_convention=node_convention)

    if needs_rahu:
        rahu_state = computed[CelestialBody.RAHU]
        ketu_longitude = (rahu_state.longitude + 180.0) % 360.0
        computed[CelestialBody.KETU] = PlanetState(
            body=CelestialBody.KETU,
            ephemeris_mode=rahu_state.ephemeris_mode,
            longitude=ketu_longitude,
            latitude=-rahu_state.latitude,
            distance_au=rahu_state.distance_au,
            speed_longitude=rahu_state.speed_longitude,
            speed_latitude=-rahu_state.speed_latitude,
            retrograde=rahu_state.retrograde,
            degree_components=DegreeComponents.from_longitude(ketu_longitude),
            node_convention=config.node_convention,
        )

    if needs_sun:
        sun_longitude = computed[CelestialBody.SUN].longitude
        for body in _COMBUSTION_ELIGIBLE:
            state = computed.get(body)
            if state is None:
                continue
            combustion_status: CombustionStatus | None = combustion.evaluate_combustion(
                body,
                state.longitude,
                sun_longitude,
                is_retrograde=state.retrograde,
            )
            computed[body] = state.model_copy(update={"combustion": combustion_status})

    states = {body: state for body, state in computed.items() if body in requested}
    mode = _aggregate_mode(modes)
    return states, mode


# Priority order for the aggregate metadata.ephemeris_mode: if any computed
# body actually used a lower-precision mode, the aggregate must disclose the
# weakest one present -- never an arbitrary pick from a set. Per-body mode
# is always available on each PlanetState regardless (see models.PlanetState).
_MODE_PRIORITY = (EphemerisMode.MOSHIER, EphemerisMode.JPL, EphemerisMode.SWISS_EPHEMERIS_FILES)


def _aggregate_mode(modes: set[EphemerisMode]) -> EphemerisMode:
    for candidate in _MODE_PRIORITY:
        if candidate in modes:
            return candidate
    return EphemerisMode.MOSHIER
