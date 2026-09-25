"""Pure Four Pillars arithmetic (Phase 9 WP-H; `docs/ASTROLOGY_STANDARDS.md`
v1.18.0, CN-03 to CN-10). No ephemeris access.

Year: the sexagenary year opens at 立春 (Sun at apparent longitude 315); the
Lichun-year Y has index (Y - 4) mod 60, 1984 being 甲子 (CN-04).
Month: the twelve months open at the "jie" terms 315, 345, 15, ... degrees;
the first (寅) month's stem follows 《三命通會》 卷二 論遁月時: "甲己之年丙作首，
乙庚之歲戊為頭，丙辛之歲尋庚上，丁壬壬位順行流，更有戊癸何處起？甲寅之上好追求"
(CN-05).
Day: a continuous sixty-day count, index (JDN + 49) mod 60, 甲子 = 0 (CN-06).
Hour: twelve double hours, 子 = 23:00-01:00; the 子 hour's stem follows
論遁月時: "甲己還加甲，乙庚丙作初，丙辛從戊起，丁壬庚子居，戊癸何方發？壬子是直途"
(CN-07).
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine.chinese.constants import (
    BRANCHES,
    FIRST_JIE_LONGITUDE,
    JDN_SEXAGENARY_OFFSET,
    STEMS,
    Branch,
    Stem,
)


def sexagenary(index: int) -> tuple[Stem, Branch]:
    """Stem and branch of a sexagenary index, 0 (甲子) to 59 (癸亥)."""
    if not 0 <= index < 60:
        raise ValueError(f"sexagenary index must be 0-59, got {index}")
    return STEMS[index % 10], BRANCHES[index % 12]


def sexagenary_index(stem: Stem, branch: Branch) -> int:
    s, b = STEMS.index(stem), BRANCHES.index(branch)
    if s % 2 != b % 2:
        raise ValueError(f"{stem.value}-{branch.value} is not a sexagenary pair")
    return next(i for i in range(60) if i % 10 == s and i % 12 == b)


def year_index(lichun_year: int) -> int:
    return (lichun_year - 4) % 60


def month_sector(sun_longitude: float) -> int:
    """0 for the 寅 month (from 315 degrees) to 11 for the 丑 month."""
    return int(((sun_longitude - FIRST_JIE_LONGITUDE) % 360.0) // 30.0)


def month_index(year_stem: Stem, sector: int) -> int:
    first_stem = (2 * (STEMS.index(year_stem) % 5) + 2) % 10
    stem = (first_stem + sector) % 10
    branch = (2 + sector) % 12  # 寅 is branch index 2
    return sexagenary_index(STEMS[stem], BRANCHES[branch])


def julian_day_number(date: dt.date) -> int:
    """Julian Day Number of a proleptic Gregorian date (noon-based)."""
    return date.toordinal() + 1_721_425


def day_index(date: dt.date) -> int:
    return (julian_day_number(date) + JDN_SEXAGENARY_OFFSET) % 60


def hour_branch(local_hours: float) -> Branch:
    """Double hour of a local time in hours [0, 24): 子 23:00-01:00, 丑
    01:00-03:00, ... 亥 21:00-23:00."""
    return BRANCHES[int(((local_hours + 1.0) % 24.0) // 2.0)]


def hour_index(day_stem: Stem, branch: Branch) -> int:
    first_stem = (2 * (STEMS.index(day_stem) % 5)) % 10
    b = BRANCHES.index(branch)
    return sexagenary_index(STEMS[(first_stem + b) % 10], branch)
