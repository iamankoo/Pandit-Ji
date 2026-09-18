"""Divisional chart (Varga) derivation formulas -- Phase 5 (Birth Chart /
Kundli Engine).

docs/ASTROLOGY_STANDARDS.md "Varga derivation formulas" (locked v1.3.0) is
the sole source of truth for every formula below; do not change one here
without a corresponding standards-document version bump. Every varga is
derived purely from a planet's D1 sidereal longitude -- never independently
observed or separately calculated from the ephemeris (§Divisional-chart
framework).

Each `_dN` function takes the planet's D1 sign index (0=Aries..11=Pisces)
and its degree within that sign (0.0..30.0, exclusive upper bound) and
returns the resulting varga sign index (0..11).
"""

from __future__ import annotations

from collections.abc import Callable

from pandit_astro_engine.errors import UnsupportedConfigurationError
from pandit_astro_engine.rashi import RASHI_MODALITY, Modality, Rashi, rashi_from_index, rashi_index

#: The locked Shodashvarga set.
SUPPORTED_VARGAS: tuple[int, ...] = (1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60)


def _is_odd_sign(sign_index: int) -> bool:
    """Sign number (1-indexed) odd <=> zodiacal index (0-indexed) even."""
    return sign_index % 2 == 0


def _modality_of(sign_index: int) -> Modality:
    return RASHI_MODALITY[rashi_from_index(sign_index)]


def _part_index(degree_in_sign: float, division_degrees: float, num_parts: int) -> int:
    # min(...) guards the exact-30.0 upper-boundary edge case (float
    # imprecision could otherwise push floor division to `num_parts`).
    return min(int(degree_in_sign // division_degrees), num_parts - 1)


def _d1(sign_index: int, degree_in_sign: float) -> int:
    return sign_index


def _d2(sign_index: int, degree_in_sign: float) -> int:
    leo, cancer = rashi_index(Rashi.LEO), rashi_index(Rashi.CANCER)
    first_half = degree_in_sign < 15.0
    if _is_odd_sign(sign_index):
        return leo if first_half else cancer
    return cancer if first_half else leo


def _d3(sign_index: int, degree_in_sign: float) -> int:
    # BPHS trine-counting: same / 5th / 9th sign from D1 sign -- locked over
    # the sequential alternate (docs/ASTROLOGY_STANDARDS.md).
    part = _part_index(degree_in_sign, 10.0, 3)
    return sign_index + (0, 4, 8)[part]


def _d4(sign_index: int, degree_in_sign: float) -> int:
    part = _part_index(degree_in_sign, 7.5, 4)
    return sign_index + (0, 3, 6, 9)[part]


def _d7(sign_index: int, degree_in_sign: float) -> int:
    division = 30.0 / 7.0
    part = _part_index(degree_in_sign, division, 7)
    start = sign_index if _is_odd_sign(sign_index) else sign_index + 6
    return start + part


def _d9(sign_index: int, degree_in_sign: float) -> int:
    division = 30.0 / 9.0
    part = _part_index(degree_in_sign, division, 9)
    modality_start = {
        Modality.MOVABLE: 0,
        Modality.FIXED: 8,
        Modality.DUAL: 4,
    }[_modality_of(sign_index)]
    return sign_index + modality_start + part


def _d10(sign_index: int, degree_in_sign: float) -> int:
    part = _part_index(degree_in_sign, 3.0, 10)
    start = sign_index if _is_odd_sign(sign_index) else sign_index + 8
    return start + part


def _d12(sign_index: int, degree_in_sign: float) -> int:
    part = _part_index(degree_in_sign, 2.5, 12)
    return sign_index + part


def _d16(sign_index: int, degree_in_sign: float) -> int:
    division = 30.0 / 16.0
    part = _part_index(degree_in_sign, division, 16)
    start = {
        Modality.MOVABLE: rashi_index(Rashi.ARIES),
        Modality.FIXED: rashi_index(Rashi.LEO),
        Modality.DUAL: rashi_index(Rashi.SAGITTARIUS),
    }[_modality_of(sign_index)]
    return start + part


def _d20(sign_index: int, degree_in_sign: float) -> int:
    division = 1.5
    part = _part_index(degree_in_sign, division, 20)
    start = {
        Modality.MOVABLE: rashi_index(Rashi.ARIES),
        Modality.FIXED: rashi_index(Rashi.SAGITTARIUS),
        Modality.DUAL: rashi_index(Rashi.LEO),
    }[_modality_of(sign_index)]
    return start + part


def _d24(sign_index: int, degree_in_sign: float) -> int:
    division = 1.25
    part = _part_index(degree_in_sign, division, 24)
    start = rashi_index(Rashi.LEO) if _is_odd_sign(sign_index) else rashi_index(Rashi.CANCER)
    return start + part


def _d27(sign_index: int, degree_in_sign: float) -> int:
    division = 30.0 / 27.0
    part = _part_index(degree_in_sign, division, 27)
    start = {
        Modality.MOVABLE: rashi_index(Rashi.ARIES),
        Modality.FIXED: rashi_index(Rashi.CANCER),
        Modality.DUAL: rashi_index(Rashi.LIBRA),
    }[_modality_of(sign_index)]
    return start + part


#: D30 assigns an *absolute* target sign per ruler/degree-range -- unlike
#: every other varga, the result does not count forward from the D1 sign
#: (docs/ASTROLOGY_STANDARDS.md).
_D30_ODD_RANGES: tuple[tuple[float, Rashi], ...] = (
    (5.0, Rashi.ARIES),  # Mars
    (10.0, Rashi.AQUARIUS),  # Saturn
    (18.0, Rashi.SAGITTARIUS),  # Jupiter
    (25.0, Rashi.GEMINI),  # Mercury
    (30.0, Rashi.LIBRA),  # Venus
)
_D30_EVEN_RANGES: tuple[tuple[float, Rashi], ...] = (
    (5.0, Rashi.TAURUS),  # Venus
    (12.0, Rashi.VIRGO),  # Mercury
    (20.0, Rashi.PISCES),  # Jupiter
    (25.0, Rashi.CAPRICORN),  # Saturn
    (30.0, Rashi.SCORPIO),  # Mars
)


def _d30(sign_index: int, degree_in_sign: float) -> int:
    ranges = _D30_ODD_RANGES if _is_odd_sign(sign_index) else _D30_EVEN_RANGES
    for upper_bound, rashi in ranges:
        if degree_in_sign < upper_bound:
            return rashi_index(rashi)
    return rashi_index(ranges[-1][1])  # exact 30.0 edge case


def _d40(sign_index: int, degree_in_sign: float) -> int:
    division = 0.75
    part = _part_index(degree_in_sign, division, 40)
    start = rashi_index(Rashi.ARIES) if _is_odd_sign(sign_index) else rashi_index(Rashi.LIBRA)
    return start + part


def _d45(sign_index: int, degree_in_sign: float) -> int:
    division = 2.0 / 3.0
    part = _part_index(degree_in_sign, division, 45)
    start = {
        Modality.MOVABLE: rashi_index(Rashi.ARIES),
        Modality.FIXED: rashi_index(Rashi.LEO),
        Modality.DUAL: rashi_index(Rashi.SAGITTARIUS),
    }[_modality_of(sign_index)]
    return start + part


def _d60(sign_index: int, degree_in_sign: float) -> int:
    division = 0.5
    part = _part_index(degree_in_sign, division, 60)
    return sign_index + part


_VARGA_FUNCTIONS: dict[int, Callable[[int, float], int]] = {
    1: _d1,
    2: _d2,
    3: _d3,
    4: _d4,
    7: _d7,
    9: _d9,
    10: _d10,
    12: _d12,
    16: _d16,
    20: _d20,
    24: _d24,
    27: _d27,
    30: _d30,
    40: _d40,
    45: _d45,
    60: _d60,
}


def calculate_varga_sign(varga: int, longitude: float) -> Rashi:
    """The varga-chart sign a body/point at absolute sidereal `longitude`
    falls into, for one of the locked Shodashvarga divisions."""
    from pandit_astro_engine.rashi import degree_within_sign, sign_index_from_longitude

    if varga not in _VARGA_FUNCTIONS:
        raise UnsupportedConfigurationError(
            f"Varga D{varga} is not part of the locked Shodashvarga set {SUPPORTED_VARGAS}."
        )
    sign_index = sign_index_from_longitude(longitude)
    degree_in_sign = degree_within_sign(longitude)
    result_index = _VARGA_FUNCTIONS[varga](sign_index, degree_in_sign)
    return rashi_from_index(result_index)
