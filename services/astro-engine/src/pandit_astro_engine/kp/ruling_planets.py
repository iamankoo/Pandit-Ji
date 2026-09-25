"""KP Ruling Planets of a moment (Phase 9 WP-E; `docs/ASTROLOGY_STANDARDS.md`
v1.15.0, KP-10). Pure function over already-computed positions.

KP Reader VI, "Ruling Planets": the lord of the star in which the Ascendant
rises, the lord of the Ascendant sign, the lord of the Moon's star, the lord
of the Moon's sign, and the lord of the day. Rahu or Ketu "act as an agent
of the lord of the sign" they occupy and join when that lord is the day
lord, the Ascendant sign lord or the Moon sign lord (the Reader's examples
are all sign-lord or day-lord cases, so star-lord members add no node).
Members "deposited in the constellation of a retrograde planet should be
rejected": reported as a flag, never silently removed. Mean nodes are
retrograde by definition, so for a node star lord the flag is
NOT_EVALUABLE(node_retrogression_unresolved).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from pandit_astro_engine.kp.subdivision import kp_lords
from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import rashi_from_longitude

#: Weekday lords, Sunday first (KP Reader VI, "Everyday has its lord").
WEEKDAY_LORD_SUNDAY_FIRST: tuple[CelestialBody, ...] = (
    CelestialBody.SUN,
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
)

NODES = (CelestialBody.RAHU, CelestialBody.KETU)


class RulingRole(str, Enum):
    ASCENDANT_STAR_LORD = "ascendant_star_lord"
    ASCENDANT_SIGN_LORD = "ascendant_sign_lord"
    MOON_STAR_LORD = "moon_star_lord"
    MOON_SIGN_LORD = "moon_sign_lord"
    DAY_LORD = "day_lord"
    NODE_AGENT = "node_agent"


class RetrogradeStarFlag(str, Enum):
    IN_STAR_OF_RETROGRADE = "in_star_of_retrograde"
    NOT_IN_STAR_OF_RETROGRADE = "not_in_star_of_retrograde"
    NODE_RETROGRESSION_UNRESOLVED = "node_retrogression_unresolved"


@dataclass(frozen=True)
class RulingMember:
    body: CelestialBody
    role: RulingRole
    represents: CelestialBody | None
    star_lord_of_body: CelestialBody
    retrograde_star_flag: RetrogradeStarFlag


def ruling_planets(
    *,
    ascendant: float,
    longitudes: Mapping[CelestialBody, float],
    retrograde: Mapping[CelestialBody, bool],
    weekday_sunday_zero: int,
) -> tuple[RulingMember, ...]:
    """`longitudes` must cover all nine bodies (sidereal, KP ayanamsa);
    `weekday_sunday_zero` is 0 for Sunday ... 6 for Saturday."""
    missing = set(CelestialBody) - set(longitudes)
    if missing:
        raise ValueError(f"ruling planets need all nine bodies; missing {sorted(missing)}")
    if not 0 <= weekday_sunday_zero <= 6:
        raise ValueError("weekday_sunday_zero must be 0-6")

    asc = kp_lords(ascendant)
    moon = kp_lords(longitudes[CelestialBody.MOON])
    day_lord = WEEKDAY_LORD_SUNDAY_FIRST[weekday_sunday_zero]
    base: list[tuple[CelestialBody, RulingRole, CelestialBody | None]] = [
        (asc.star_lord, RulingRole.ASCENDANT_STAR_LORD, None),
        (asc.sign_lord, RulingRole.ASCENDANT_SIGN_LORD, None),
        (moon.star_lord, RulingRole.MOON_STAR_LORD, None),
        (moon.sign_lord, RulingRole.MOON_SIGN_LORD, None),
        (day_lord, RulingRole.DAY_LORD, None),
    ]
    sign_lord_members = {asc.sign_lord, moon.sign_lord, day_lord}
    for node in NODES:
        owner = RASHI_LORD[rashi_from_longitude(longitudes[node])]
        if owner in sign_lord_members:
            base.append((node, RulingRole.NODE_AGENT, owner))

    members: list[RulingMember] = []
    for body, role, represents in base:
        star = kp_lords(longitudes[body]).star_lord
        if star in NODES:
            flag = RetrogradeStarFlag.NODE_RETROGRESSION_UNRESOLVED
        elif retrograde[star]:
            flag = RetrogradeStarFlag.IN_STAR_OF_RETROGRADE
        else:
            flag = RetrogradeStarFlag.NOT_IN_STAR_OF_RETROGRADE
        members.append(RulingMember(body, role, represents, star, flag))
    return tuple(members)
