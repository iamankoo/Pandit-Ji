"""Pure Shadbala component formulas (Phase 9 WP-F; `docs/ASTROLOGY_STANDARDS.md`
v1.16.0, SB-03 to SB-16; BPHS Ch. 27, Santhanam translation, OCR level).

Every function takes already-computed chart quantities and returns Virupas
(or a reason it cannot); no ephemeris access. Values are unrounded floats.
"""

from __future__ import annotations

from collections.abc import Mapping

from pandit_astro_engine.dignity import debilitation_point
from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.rashi import Rashi, rashi_index
from pandit_astro_engine.shadbala.constants import (
    COMPOUND,
    DREKKANA_OF_GENDER,
    GENDER,
    MOOLATRIKONA,
    MOON_BOUNDARY_EPSILON_DEGREES,
    MOON_WAXING_ELONGATION,
    NAISARGIKA_MULTIPLIER,
    NATHA_GROUP,
    NATURAL_BENEFICS,
    NATURAL_ENEMIES,
    NATURAL_FRIENDS,
    NATURAL_MALEFICS,
    SAPTAVARGAJA_VIRUPAS,
    TEMPORAL_FRIEND_HOUSES,
    TRIBHAGA_DAY,
    TRIBHAGA_NIGHT,
    UNNATHA_GROUP,
    VARA_BALA_VIRUPAS,
    VIRUPAS_PER_RUPA,
    WEEKDAY_LORD_SUNDAY_FIRST,
)


def _arc_over_three(longitude: float, reference: float) -> float:
    """(longitude - reference) folded to [0, 180] degrees, divided by 3 --
    the shared arithmetic of Uchcha Bala (v. 1) and Dig Bala (v. 7)."""
    diff = (longitude - reference) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff / 3.0


def debilitation_longitude(body: B) -> float:
    rashi, degree = debilitation_point(body)
    return rashi_index(rashi) * 30.0 + degree


def uchcha_bala(body: B, longitude: float) -> float:
    return _arc_over_three(longitude, debilitation_longitude(body))


def dig_bala(longitude: float, zero_point: float) -> float:
    return _arc_over_three(longitude, zero_point)


def _house_count(from_sign: Rashi, to_sign: Rashi) -> int:
    return (rashi_index(to_sign) - rashi_index(from_sign)) % 12 + 1


def compound_relationship(body: B, other: B, d1_signs: Mapping[B, Rashi]) -> str:
    """Ch. 3 v. 55-58 compound relationship of `body` towards `other`, the
    temporal part from the Rasi chart."""
    if other in NATURAL_FRIENDS[body]:
        natural = "friend"
    elif other in NATURAL_ENEMIES[body]:
        natural = "enemy"
    else:
        natural = "equal"
    house = _house_count(d1_signs[body], d1_signs[other])
    temporal = "friend" if house in TEMPORAL_FRIEND_HOUSES else "enemy"
    return COMPOUND[(natural, temporal)]


def _own_signs(body: B) -> frozenset[Rashi]:
    return frozenset(r for r, lord in RASHI_LORD.items() if lord == body)


def saptavarga_category(
    body: B,
    varga: int,
    sign: Rashi,
    d1_degree_in_sign: float,
    d1_signs: Mapping[B, Rashi],
) -> str | None:
    """Placement class of one varga sign; None where D1 puts the planet in
    its Moolatrikona sign but outside the Ch. 3 degree range (the verse's
    'Moolatrikona Rasi' and Ch. 3 v. 51-54 disagree there)."""
    mt_sign, mt_from, mt_to = MOOLATRIKONA[body]
    if sign == mt_sign:
        if varga != 1:
            return "moolatrikona"
        if mt_from <= d1_degree_in_sign < mt_to:
            return "moolatrikona"
        return None
    if sign in _own_signs(body):
        return "own"
    return compound_relationship(body, RASHI_LORD[sign], d1_signs)


def saptavarga_virupas(category: str) -> float:
    return SAPTAVARGAJA_VIRUPAS[category]


def _is_odd_sign(sign: Rashi) -> bool:
    return rashi_index(sign) % 2 == 0  # Aries (index 0) is the first, odd sign


def ojayugma_bala(body: B, d1_sign: Rashi, d9_sign: Rashi) -> float:
    wants_even = body in (B.MOON, B.VENUS)
    quarter = VIRUPAS_PER_RUPA / 4.0
    return sum(quarter for s in (d1_sign, d9_sign) if _is_odd_sign(s) != wants_even)


def kendradi_bala(lagna_sign: Rashi, planet_sign: Rashi) -> float:
    house = _house_count(lagna_sign, planet_sign)
    if house in (1, 4, 7, 10):
        return VIRUPAS_PER_RUPA
    if house in (2, 5, 8, 11):
        return VIRUPAS_PER_RUPA / 2.0
    return VIRUPAS_PER_RUPA / 4.0


def drekkana_bala(body: B, degree_in_sign: float) -> float:
    part = min(int(degree_in_sign // 10.0), 2)
    return VIRUPAS_PER_RUPA / 4.0 if part == DREKKANA_OF_GENDER[GENDER[body]] else 0.0


def unnata_ghatis(apparent_solar_hours: float) -> float:
    """Apparent time from the nearer apparent midnight, in ghatis [0, 30]
    (one hour = 2.5 ghatis)."""
    hours = apparent_solar_hours % 24.0
    return min(hours, 24.0 - hours) * 2.5


def nathonnatha_bala(body: B, unnata: float) -> float:
    natha = 2.0 * (30.0 - unnata)
    if body in NATHA_GROUP:
        return natha
    if body in UNNATHA_GROUP:
        return VIRUPAS_PER_RUPA - natha
    return VIRUPAS_PER_RUPA  # Mercury


def elongation(moon: float, sun: float) -> float:
    return (moon - sun) % 360.0


def paksha_benefic_value(moon: float, sun: float) -> float:
    return _arc_over_three(moon, sun)


def moon_nature(moon: float, sun: float) -> str | None:
    """'benefic' (waxing), 'malefic' (waning) or None at the phase boundary."""
    e = elongation(moon, sun)
    start, end = MOON_WAXING_ELONGATION
    if min(abs(e - start), abs(e - end), abs(e - 360.0)) < MOON_BOUNDARY_EPSILON_DEGREES:
        return None
    return "benefic" if start <= e < end else "malefic"


def natural_nature(body: B, longitudes: Mapping[B, float], signs: Mapping[B, Rashi]) -> str | None:
    """Ch. 3 v. 11 with the Phase 6 conventions. None: Moon at the phase
    boundary, or Mercury joined by both a benefic and a malefic."""
    if body in NATURAL_MALEFICS:
        return "malefic"
    if body in NATURAL_BENEFICS:
        return "benefic"
    if body is B.MOON:
        return moon_nature(longitudes[B.MOON], longitudes[B.SUN])
    benefic = malefic = False
    for other, sign in signs.items():
        if other is B.MERCURY or sign != signs[B.MERCURY]:
            continue
        nature = natural_nature(other, longitudes, signs)
        if nature is None:
            return None
        benefic |= nature == "benefic"
        malefic |= nature == "malefic"
    if benefic and malefic:
        return None
    return "malefic" if malefic else "benefic"


def paksha_bala(nature: str, moon: float, sun: float) -> float:
    value = paksha_benefic_value(moon, sun)
    return value if nature == "benefic" else VIRUPAS_PER_RUPA - value


def tribhaga_bala(body: B, is_day: bool, third: int) -> float:
    if body is B.JUPITER:
        return VIRUPAS_PER_RUPA
    holders = TRIBHAGA_DAY if is_day else TRIBHAGA_NIGHT
    return VIRUPAS_PER_RUPA if holders[third - 1] is body else 0.0


def vara_bala(body: B, weekday_sunday_zero: int) -> float:
    return VARA_BALA_VIRUPAS if WEEKDAY_LORD_SUNDAY_FIRST[weekday_sunday_zero] is body else 0.0


def naisargika_bala(body: B) -> float:
    return VIRUPAS_PER_RUPA * NAISARGIKA_MULTIPLIER[body] / 7.0
