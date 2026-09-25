"""Pure formulas of the modern Shadbala profile `SHADBALA_RAMAN_GRAHA_BHAVA_BALAS`
(Phase 9 closure; `docs/ASTROLOGY_STANDARDS.md` v1.21.0, SR-01 to SR-24).

Source: B. V. Raman, *Graha and Bhava Balas* (second edition; archive.org OCR
and page images, `research/ASTROLOGY_SOURCES.md` Group 22). Raman states he
follows Sripati. This module is a separate methodology from the verse-literal
BPHS profile (`components.py`): nothing here is called by the BPHS profile,
and the Raman service never falls back to a BPHS value. Where Raman's rule
is arithmetically the same as a BPHS rule (Uchcha, Ojayugma, Kendra, Dig,
Nathonnatha, Tribhaga, Naisargika), the shared helper in `components.py` is
reused and the provenance cites Raman.

Every number below is Raman's, read from the page images of his worked
Standard Horoscope and his Tables IV-IX (mean motions derived from the
ten-thousand-day columns).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from enum import Enum

from pandit_astro_engine.models import CelestialBody as B

# --------------------------------------------------------------------------
# Sthana: Saptavargaja values and Drekkana (Arts. 30, 36-39)
# --------------------------------------------------------------------------

#: Art. 30: Moolatrikona 45 (in the Rasi only), own 30, great friend 22.5,
#: friend 15, neutral 7.5, enemy 3.75, bitter enemy 1.875.
RAMAN_SAPTAVARGAJA: dict[str, float] = {
    "moolatrikona": 45.0,
    "own": 30.0,
    "great_friend": 22.5,
    "friend": 15.0,
    "equal": 7.5,
    "enemy": 3.75,
    "great_enemy": 1.875,
}


class DrekkanaReading(str, Enum):
    """Raman's text (Art. 36) gives male 1st, hermaphrodite middle, female
    last; his own worked Example 12 gives the Moon (female) the value in the
    second Drekkana, i.e. male 1st, female 2nd, neuter 3rd. No default."""

    TEXT_ARTICLE_36 = "text_article_36"
    WORKED_EXAMPLE_12 = "worked_example_12"


_DREKKANA_BY_READING: dict[DrekkanaReading, dict[str, int]] = {
    DrekkanaReading.TEXT_ARTICLE_36: {"male": 0, "neuter": 1, "female": 2},
    DrekkanaReading.WORKED_EXAMPLE_12: {"male": 0, "female": 1, "neuter": 2},
}


def raman_drekkana_bala(gender: str, degree_in_sign: float, reading: DrekkanaReading) -> float:
    part = min(int(degree_in_sign // 10.0), 2)
    return 15.0 if part == _DREKKANA_BY_READING[reading][gender] else 0.0


# --------------------------------------------------------------------------
# Kala: Paksha (Arts. 52-55), ahargana lords (Arts. 58-67), Hora (68-70),
# Ayana (71-75), Yuddha (76-77)
# --------------------------------------------------------------------------


class MoonPakshaReading(str, Enum):
    """Art. 53 calls the increasing Moon benefic and the decreasing Moon
    malefic, "i.e." benefic from the 8th day of the bright half to the 8th day
    of the dark half -- two different rules. No default."""

    WAXING_HALF = "waxing_half"
    EIGHTH_DAY_WINDOW = "eighth_day_window"


def raman_moon_is_benefic(elongation: float, reading: MoonPakshaReading) -> bool:
    """`elongation` = (Moon - Sun) mod 360. The eighth-day window is read
    inclusively: from the start of the 8th tithi of the bright half (84
    degrees) to the end of the 8th tithi of the dark half (276 degrees)."""
    e = elongation % 360.0
    if reading is MoonPakshaReading.WAXING_HALF:
        return e < 180.0
    return 84.0 <= e < 276.0


#: Art. 64: condensed ahargana = days from 1 January 1900 + 26,543; the
#: remainders are counted from Wednesday (Art. 63).
AHARGANA_OFFSET_1900 = 26_543
_EPOCH_1900 = dt.date(1900, 1, 1)
WEEKDAY_LORD_SUNDAY_FIRST: tuple[B, ...] = (
    B.SUN,
    B.MOON,
    B.MARS,
    B.MERCURY,
    B.JUPITER,
    B.VENUS,
    B.SATURN,
)
_WEDNESDAY = 3


def condensed_ahargana(hindu_date: dt.date) -> int:
    return (hindu_date - _EPOCH_1900).days + AHARGANA_OFFSET_1900


def _count_from_wednesday(remainder: int) -> int:
    """Sunday-zero weekday of a remainder counted from Wednesday (1 =
    Wednesday itself; 0 counts as 7)."""
    r = remainder if remainder else 7
    return (_WEDNESDAY + r - 1) % 7


def abda_lord(ahargana: int) -> B:
    """Art. 60: complete 360-day years x 3 + 1, remainder of 7."""
    return WEEKDAY_LORD_SUNDAY_FIRST[_count_from_wednesday((ahargana // 360 * 3 + 1) % 7)]


def masa_lord(ahargana: int) -> B:
    """Art. 61: complete 30-day months x 2 + 1, remainder of 7."""
    return WEEKDAY_LORD_SUNDAY_FIRST[_count_from_wednesday((ahargana // 30 * 2 + 1) % 7)]


def ahargana_weekday(ahargana: int) -> int:
    """Art. 62: the ahargana's own weekday (Sunday = 0), a consistency check."""
    return _count_from_wednesday(ahargana % 7)


#: Art. 69: the Hora sequence -- each hour's lord is the next in this order,
#: the first Hora of the day being the weekday lord.
HORA_ORDER: tuple[B, ...] = (B.SUN, B.VENUS, B.MERCURY, B.MOON, B.SATURN, B.JUPITER, B.MARS)


def hora_lord(weekday_sunday_zero: int, hours_since_sunrise: float) -> B:
    """Art. 70 Rule 1: equal one-hour Horas from sunrise."""
    if not 0.0 <= hours_since_sunrise < 24.0:
        raise ValueError("hours since sunrise must be in [0, 24)")
    start = HORA_ORDER.index(WEEKDAY_LORD_SUNDAY_FIRST[weekday_sunday_zero])
    return HORA_ORDER[(start + int(hours_since_sunrise)) % 7]


#: Art. 73: declination added in each successive 15 degrees of bhuja, in arc
#: minutes (the Hindu maximum of 24 degrees).
KRANTI_STEPS_ARCMIN: tuple[float, ...] = (362.0, 341.0, 299.0, 236.0, 150.0, 52.0)


def raman_kranti(sayana_longitude: float) -> float:
    """Signed declination in degrees (north positive) of an ecliptic point,
    by Raman's 15-degree table with proportion inside a step."""
    lon = sayana_longitude % 360.0
    bhuja = lon % 180.0
    if bhuja > 90.0:
        bhuja = 180.0 - bhuja
    steps = int(bhuja // 15.0)
    minutes = sum(KRANTI_STEPS_ARCMIN[:steps])
    if steps < 6:
        minutes += (bhuja - 15.0 * steps) / 15.0 * KRANTI_STEPS_ARCMIN[steps]
    return (minutes / 60.0) * (1.0 if lon < 180.0 else -1.0)


def raman_ayana_bala(body: B, kranti: float) -> float:
    """Art. 75 (Kesava Daivajna): (24 +/- kranti) / 48 x 60; north is
    additive for Venus, Sun, Mars, Jupiter, south for Saturn and the Moon;
    Mercury always additive; the Sun's value doubled."""
    if body is B.MERCURY:
        signed = abs(kranti)
    elif body in (B.MOON, B.SATURN):
        signed = -kranti
    else:
        signed = kranti
    value = (24.0 + signed) / 48.0 * 60.0
    return value * 2.0 if body is B.SUN else value


#: Art. 77: disc diameters in arc seconds (Bimba Parimana).
BIMBA_ARCSEC: dict[B, float] = {
    B.MARS: 9.4,
    B.MERCURY: 6.6,
    B.JUPITER: 190.4,
    B.VENUS: 16.6,
    B.SATURN: 158.0,
}
WAR_PLANETS: tuple[B, ...] = (B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN)
WAR_LIMIT_DEGREES = 1.0

# --------------------------------------------------------------------------
# Cheshta (Arts. 87-107; Tables IV-IX)
# --------------------------------------------------------------------------

#: Epoch of the mean-motion tables: 1 January 1900, 0h (mean midnight) at
#: 76 degrees E, as a Julian Day (UT).
CHESHTA_EPOCH_JD_UT = 2415020.5 - 76.0 / 360.0

#: (epoch value in degrees, degrees per day from the ten-thousand-day column,
#: correction constant, correction per year since 1900, correction sign).
MEAN_MOTION: dict[str, tuple[float, float, float, float, float]] = {
    "sun": (257.4568, 9856.0265 / 10_000, 0.0, 0.0, 0.0),
    "mars": (270.22, 5240.19 / 10_000, 0.0, 0.0, 0.0),
    "jupiter": (220.04, 830.96 / 10_000, 3.33, 0.0067, -1.0),
    "saturn": (236.74, 334.39 / 10_000, 5.0, 0.001, 1.0),
    "mercury_sighrocca": (164.0, 40923.18 / 10_000, 6.67, -0.00133, 1.0),
    "venus_sighrocca": (328.51, 16021.46 / 10_000, 5.0, 0.001, -1.0),
}


def cheshta_interval(julian_day_ut: float) -> float:
    return julian_day_ut - CHESHTA_EPOCH_JD_UT


def mean_element(key: str, interval_days: float, years_since_1900: int) -> float:
    epoch, rate, c0, c1, sign = MEAN_MOTION[key]
    return (epoch + rate * interval_days + sign * (c0 + c1 * years_since_1900)) % 360.0


def mean_and_sighrocca(body: B, interval_days: float, years_since_1900: int) -> tuple[float, float]:
    """(mean longitude, sighrocca) in Raman's sidereal frame. Superior planets:
    their own mean and the mean Sun as sighrocca (Art. 101). Mercury and
    Venus: the mean Sun as mean longitude (Art. 95) and their own sighrocca."""
    sun = mean_element("sun", interval_days, years_since_1900)
    if body in (B.MARS, B.JUPITER, B.SATURN):
        return mean_element(body.value, interval_days, years_since_1900), sun
    if body in (B.MERCURY, B.VENUS):
        return sun, mean_element(f"{body.value}_sighrocca", interval_days, years_since_1900)
    raise ValueError("Raman gives Cheshta Bala only for Mars to Saturn")


def reduced_cheshta_kendra(sighrocca: float, mean: float, true: float) -> float:
    """Art. 105-106: sighrocca - (mean + true)/2, reduced to [0, 180]."""
    mid = (mean + true) / 2.0
    if abs(mean - true) > 180.0:  # average across 0 degrees on the short arc
        mid = (mid + 180.0) % 360.0
    kendra = (sighrocca - mid) % 360.0
    return 360.0 - kendra if kendra > 180.0 else kendra


# --------------------------------------------------------------------------
# Drik (Arts. 109-120)
# --------------------------------------------------------------------------

#: Art. 115: special aspects -- (lower, upper) angle ranges and extra value.
VISESHA: dict[B, tuple[tuple[tuple[float, float], ...], float]] = {
    B.SATURN: (((60.0, 90.0), (270.0, 300.0)), 45.0),
    B.JUPITER: (((120.0, 150.0), (240.0, 270.0)), 30.0),
    B.MARS: (((90.0, 120.0), (210.0, 240.0)), 15.0),
}


def drishti_value(angle: float) -> float:
    """Art. 114 (Sripati): the aspect value for a Dristi Kendra in degrees."""
    k = angle % 360.0
    if k < 30.0 or k >= 300.0:
        return 0.0
    if k < 60.0:
        return (k - 30.0) / 2.0
    if k < 90.0:
        return (k - 60.0) + 15.0
    if k < 120.0:
        return (120.0 - k) / 2.0 + 30.0
    if k < 150.0:
        return 150.0 - k
    if k < 180.0:
        return (k - 150.0) * 2.0
    return (300.0 - k) / 2.0


def visesha_value(aspecting: B, angle: float) -> float:
    ranges, extra = VISESHA.get(aspecting, ((), 0.0))
    k = angle % 360.0
    return extra if any(lo <= k < hi for lo, hi in ranges) else 0.0


def dristi_pinda(
    aspected: B, longitudes: Mapping[B, float], natures: Mapping[B, str | None]
) -> tuple[float | None, dict[B, float]]:
    """Signed sum of the aspects on `aspected` from the other six planets
    (benefics +, malefics -). None when an aspecting planet with a non-zero
    aspect has no determinable nature (Moon at the phase boundary, Mercury
    with mixed association)."""
    cells: dict[B, float] = {}
    total = 0.0
    for body, lon in longitudes.items():
        if body is aspected:
            continue
        angle = (longitudes[aspected] - lon) % 360.0
        value = drishti_value(angle) + visesha_value(body, angle)
        if value == 0.0:
            continue
        nature = natures[body]
        if nature is None:
            return None, cells
        signed = value if nature == "benefic" else -value
        cells[body] = signed
        total += signed
    return total, cells
