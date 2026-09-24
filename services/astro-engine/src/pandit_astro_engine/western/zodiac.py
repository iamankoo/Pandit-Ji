"""Tropical sign classification (Phase 9 WP-D, WD-02).

Signs are 30-degree segments from 0 Aries at the vernal point. Intervals
are half-open, [start, start + 30), with 360 = 0, and the index is computed
with exact rational arithmetic on the float value, the same engineering
convention the Nakshatra classification uses (standards v1.4.1), so a
longitude exactly on a boundary always belongs to the later sign.
"""

from __future__ import annotations

import math
from fractions import Fraction

from pandit_astro_engine.western.constants import SIGN_ORDER, TropicalSign


def normalize_longitude(longitude: float) -> float:
    """Return a longitude in [0, 360). Rejects NaN and infinities."""
    if not math.isfinite(longitude):
        raise ValueError(f"longitude must be finite, got {longitude!r}")
    value = longitude % 360.0
    return 0.0 if value == 360.0 else value


def sign_index(longitude: float) -> int:
    value = normalize_longitude(longitude)
    return int(Fraction(value) * 12 // 360)


def tropical_sign(longitude: float) -> TropicalSign:
    return SIGN_ORDER[sign_index(longitude)]


def degree_in_sign(longitude: float) -> float:
    value = normalize_longitude(longitude)
    return float(Fraction(value) - 30 * sign_index(value))
