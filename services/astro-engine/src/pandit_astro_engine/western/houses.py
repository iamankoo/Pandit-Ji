"""House placement against computed cusps (Phase 9 WP-D, WD-08).

A body is placed by its ecliptic longitude alone (ecliptic latitude is not
used), in the half-open arc [cusp n, cusp n+1) measured in zodiacal order,
with house 12 running to cusp 1. Exact rational arithmetic on the float
values means a body exactly on a cusp belongs to the house that cusp opens.
"""

from __future__ import annotations

from fractions import Fraction

from pandit_astro_engine.western.zodiac import normalize_longitude

_FULL = Fraction(360)


def _arc(start: Fraction, end: Fraction) -> Fraction:
    """Zodiacal-order arc from `start` to `end`, in [0, 360)."""
    return (end - start) % _FULL


def validate_cusps(cusps: tuple[float, ...]) -> None:
    """Twelve cusps in zodiacal order whose arcs are all positive and close
    the circle exactly once."""
    if len(cusps) != 12:
        raise ValueError(f"expected 12 cusps, got {len(cusps)}")
    exact = [Fraction(normalize_longitude(c)) for c in cusps]
    arcs = [_arc(exact[i], exact[(i + 1) % 12]) for i in range(12)]
    if any(a == 0 for a in arcs) or sum(arcs) != _FULL:
        raise ValueError("house cusps are not in strictly increasing zodiacal order")


def house_of(longitude: float, cusps: tuple[float, ...]) -> int:
    """Placidus (or any quadrant) house number 1-12 for an ecliptic longitude."""
    validate_cusps(cusps)
    point = Fraction(normalize_longitude(longitude))
    exact = [Fraction(normalize_longitude(c)) for c in cusps]
    for index in range(12):
        start = exact[index]
        end = exact[(index + 1) % 12]
        if _arc(start, point) < _arc(start, end):
            return index + 1
    raise AssertionError("unreachable: validated cusps cover the circle")  # pragma: no cover
