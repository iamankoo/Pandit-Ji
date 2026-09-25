"""Constants and tables for Shadbala (Phase 9 WP-F; `docs/ASTROLOGY_STANDARDS.md`
v1.16.0, SB-01 to SB-20; BPHS Ch. 27, Santhanam translation, OCR level).

The relationship, Moolatrikona and natural-nature tables restate the locked
Phase 6 tables (`services/knowledge/rules/bphs/tables/*.yaml`, standards
v1.4.0); a test compares them value by value so the two can never drift.
Debilitation points come from the Phase 5 dignity table (not restated).
"""

from __future__ import annotations

from enum import Enum

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.rashi import Rashi

#: Standards version recorded on every Shadbala result (SB-19).
SHADBALA_STANDARDS_VERSION = "1.16.0"

#: System tag: Shadbala is a Parashari (Vedic) fact, under the Vedic default
#: profile (sidereal, Lahiri, whole-sign houses).
SHADBALA_SYSTEM_ID = "vedic_parashari"

#: Ch. 27 v. 1 note: "computed for the seven planets from the Sun to Saturn.
#: The nodes are not considered."
SHADBALA_BODIES: tuple[B, ...] = (B.SUN, B.MOON, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN)

VIRUPAS_PER_RUPA = 60.0


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTER = "neuter"


#: BPHS Ch. 3 v. 19 (verse): Mercury and Saturn neuter; Moon and Venus female;
#: Sun, Mars and Jupiter male.
GENDER: dict[B, Gender] = {
    B.SUN: Gender.MALE,
    B.MARS: Gender.MALE,
    B.JUPITER: Gender.MALE,
    B.MOON: Gender.FEMALE,
    B.VENUS: Gender.FEMALE,
    B.MERCURY: Gender.NEUTER,
    B.SATURN: Gender.NEUTER,
}

#: Ch. 27 v. 6: male, female and neuter planets get a quarter Rupa in the
#: first, second and third decanate respectively (0-based decanate index).
DREKKANA_OF_GENDER: dict[Gender, int] = {Gender.MALE: 0, Gender.FEMALE: 1, Gender.NEUTER: 2}


#: Ch. 27 v. 7: the point where each planet has no directional strength --
#: the 4th house for Sun and Mars, the 7th for Jupiter and Mercury, the 10th
#: for Venus and the Moon, the Ascendant for Saturn. The translation glosses
#: these as the Nadir, descendant, meridian and ascendant.
class Angle(str, Enum):
    ASCENDANT = "ascendant"
    NADIR = "nadir"
    DESCENDANT = "descendant"
    MERIDIAN = "meridian"


DIG_BALA_ZERO_POINT: dict[B, Angle] = {
    B.SUN: Angle.NADIR,
    B.MARS: Angle.NADIR,
    B.JUPITER: Angle.DESCENDANT,
    B.MERCURY: Angle.DESCENDANT,
    B.VENUS: Angle.MERIDIAN,
    B.MOON: Angle.MERIDIAN,
    B.SATURN: Angle.ASCENDANT,
}

#: Ch. 27 v. 8-9: Nathonnatha groups. Mercury always receives one Rupa.
NATHA_GROUP: tuple[B, ...] = (B.MOON, B.MARS, B.SATURN)
UNNATHA_GROUP: tuple[B, ...] = (B.SUN, B.JUPITER, B.VENUS)

#: Ch. 27 v. 12: Tribhaga -- the planet receiving one Rupa in each third of
#: the day and of the night; Jupiter receives one Rupa at all times.
TRIBHAGA_DAY: tuple[B, B, B] = (B.MERCURY, B.SUN, B.SATURN)
TRIBHAGA_NIGHT: tuple[B, B, B] = (B.MOON, B.VENUS, B.MARS)

#: Ch. 27 v. 13: Varsha, Masa, Dina and Hora lords receive 15, 30, 45 and 60.
VARA_BALA_VIRUPAS = 45.0

#: Weekday lords, Sunday first.
WEEKDAY_LORD_SUNDAY_FIRST: tuple[B, ...] = (
    B.SUN,
    B.MOON,
    B.MARS,
    B.MERCURY,
    B.JUPITER,
    B.VENUS,
    B.SATURN,
)

#: Ch. 27 v. 14: one Rupa divided by 7, multiplied by 1-7 for Saturn, Mars,
#: Mercury, Jupiter, Venus, Moon, Sun.
NAISARGIKA_MULTIPLIER: dict[B, int] = {
    B.SATURN: 1,
    B.MARS: 2,
    B.MERCURY: 3,
    B.JUPITER: 4,
    B.VENUS: 5,
    B.MOON: 6,
    B.SUN: 7,
}

#: Ch. 27 v. 2-4: Saptavargaja values in Virupas by placement class.
SAPTAVARGAJA_VIRUPAS: dict[str, float] = {
    "moolatrikona": 45.0,
    "own": 30.0,
    "great_friend": 20.0,
    "friend": 15.0,
    "equal": 10.0,
    "enemy": 4.0,
    "great_enemy": 2.0,
}

#: The seven divisions of Saptavargaja (Ch. 27 v. 2-4 note: Rasi, Hora,
#: Decanate, Saptamamsa, Navamsa, Dvadasamsa, Trimsamsa), computed with the
#: locked Phase 5 varga schemes.
SAPTAVARGA: tuple[int, ...] = (1, 2, 3, 7, 9, 12, 30)

# --------------------------------------------------------------------------
# Phase 6 locked tables, restated (drift-tested against the knowledge YAML)
# --------------------------------------------------------------------------

#: BPHS Ch. 3 v. 55 natural friends and enemies; the rest are equals.
NATURAL_FRIENDS: dict[B, frozenset[B]] = {
    B.SUN: frozenset({B.MOON, B.MARS, B.JUPITER}),
    B.MOON: frozenset({B.SUN, B.MERCURY}),
    B.MARS: frozenset({B.SUN, B.MOON, B.JUPITER}),
    B.MERCURY: frozenset({B.SUN, B.VENUS}),
    B.JUPITER: frozenset({B.SUN, B.MOON, B.MARS}),
    B.VENUS: frozenset({B.MERCURY, B.SATURN}),
    B.SATURN: frozenset({B.MERCURY, B.VENUS}),
}
NATURAL_ENEMIES: dict[B, frozenset[B]] = {
    B.SUN: frozenset({B.VENUS, B.SATURN}),
    B.MOON: frozenset(),
    B.MARS: frozenset({B.MERCURY}),
    B.MERCURY: frozenset({B.MOON}),
    B.JUPITER: frozenset({B.MERCURY, B.VENUS}),
    B.VENUS: frozenset({B.SUN, B.MOON}),
    B.SATURN: frozenset({B.SUN, B.MOON, B.MARS}),
}

#: Ch. 3 v. 56: temporal friend when the other planet is in these houses
#: (whole-sign count from the planet).
TEMPORAL_FRIEND_HOUSES: frozenset[int] = frozenset({2, 3, 4, 10, 11, 12})

#: Ch. 3 v. 57-58: (natural, temporal) -> compound.
COMPOUND: dict[tuple[str, str], str] = {
    ("friend", "friend"): "great_friend",
    ("friend", "enemy"): "equal",
    ("equal", "friend"): "friend",
    ("equal", "enemy"): "enemy",
    ("enemy", "friend"): "equal",
    ("enemy", "enemy"): "great_enemy",
}

#: Ch. 3 v. 51-54 Moolatrikona: (sign, from degree, to degree), [from, to).
MOOLATRIKONA: dict[B, tuple[Rashi, float, float]] = {
    B.SUN: (Rashi.LEO, 0.0, 20.0),
    B.MOON: (Rashi.TAURUS, 3.0, 30.0),
    B.MARS: (Rashi.ARIES, 0.0, 12.0),
    B.MERCURY: (Rashi.VIRGO, 15.0, 20.0),
    B.JUPITER: (Rashi.SAGITTARIUS, 0.0, 10.0),
    B.VENUS: (Rashi.LIBRA, 0.0, 15.0),
    B.SATURN: (Rashi.AQUARIUS, 0.0, 20.0),
}

#: Ch. 3 v. 11 natural nature, with the Phase 6 Pandit Ji conventions
#: (waxing Moon: elongation [0, 180); Mercury "joined" = same sign; mixed
#: association not classified).
NATURAL_MALEFICS: frozenset[B] = frozenset({B.SUN, B.SATURN, B.MARS, B.RAHU, B.KETU})
NATURAL_BENEFICS: frozenset[B] = frozenset({B.JUPITER, B.VENUS})
MOON_WAXING_ELONGATION: tuple[float, float] = (0.0, 180.0)
MOON_BOUNDARY_EPSILON_DEGREES = 1e-6
