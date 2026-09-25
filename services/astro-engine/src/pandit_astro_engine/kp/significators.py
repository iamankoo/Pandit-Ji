"""KP house occupancy and four-level house significators (Phase 9 WP-E;
`docs/ASTROLOGY_STANDARDS.md` v1.15.0, KP-04, KP-08, KP-09). Pure functions.

House n runs from cusp n (inclusive) to cusp n+1 (exclusive) along the
zodiac (KP Reader III); its lord is the lord of the sign holding cusp n.

Levels, in KP Reader VI's order of strength:
  A: planets in the star of an occupant of the house
  B: the occupants
  C: planets in the star of the house lord
  D: the house lord
The Reader's further levels (planets conjoined with or aspected by the
significators) and the nodes' agency for other planets are not evaluated:
KP's aspect and conjunction conventions are not locked (KP-09).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import rashi_from_longitude

#: Output order of bodies inside every level (the Vimshottari-independent
#: canonical enum order), so results are deterministic.
_BODY_ORDER: tuple[CelestialBody, ...] = tuple(CelestialBody)


def house_of(longitude: float, cusps: Sequence[float]) -> int:
    """House 1-12 containing `longitude`: [cusp n, cusp n+1) measured
    forward along the zodiac."""
    if len(cusps) != 12:
        raise ValueError("exactly 12 cusps are required")
    for index in range(12):
        start = cusps[index]
        end = cusps[(index + 1) % 12]
        span = (end - start) % 360.0
        if (longitude - start) % 360.0 < span:
            return index + 1
    raise ValueError("cusps do not tile the zodiac")  # pragma: no cover - defensive


def house_lord(cusp_longitude: float) -> CelestialBody:
    return RASHI_LORD[rashi_from_longitude(cusp_longitude)]


def _ordered(bodies: set[CelestialBody]) -> tuple[CelestialBody, ...]:
    return tuple(b for b in _BODY_ORDER if b in bodies)


def house_significators(
    cusps: Sequence[float],
    longitudes: Mapping[CelestialBody, float],
    star_lords: Mapping[CelestialBody, CelestialBody],
) -> dict[int, dict[str, tuple[CelestialBody, ...]]]:
    """Per house 1-12, the four levels keyed "a", "b", "c", "d"."""
    occupants: dict[int, set[CelestialBody]] = {h: set() for h in range(1, 13)}
    for body, lon in longitudes.items():
        occupants[house_of(lon, cusps)].add(body)

    result: dict[int, dict[str, tuple[CelestialBody, ...]]] = {}
    for house in range(1, 13):
        lord = house_lord(cusps[house - 1])
        occ = occupants[house]
        level_a = {b for b, star in star_lords.items() if star in occ}
        level_c = {b for b, star in star_lords.items() if star == lord}
        result[house] = {
            "a": _ordered(level_a),
            "b": _ordered(occ),
            "c": _ordered(level_c),
            "d": (lord,),
        }
    return result


def planet_significations(
    houses: Mapping[int, Mapping[str, tuple[CelestialBody, ...]]],
) -> dict[CelestialBody, tuple[int, ...]]:
    """Inverse view: the houses each body signifies at any of the four
    levels, ascending."""
    out: dict[CelestialBody, set[int]] = {}
    for house, levels in houses.items():
        for members in levels.values():
            for body in members:
                out.setdefault(body, set()).add(house)
    return {b: tuple(sorted(out[b])) for b in _BODY_ORDER if b in out}
