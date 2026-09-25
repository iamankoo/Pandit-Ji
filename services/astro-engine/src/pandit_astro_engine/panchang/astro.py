"""Astronomical quantities behind the Panchang (Phase 10; standards v1.23.0,
PC-05 to PC-08). True (apparent) geocentric longitudes (CRC recommendation
(9)); sidereal = tropical minus the Lahiri ayanamsa with nutation, read
without changing the applied sidereal mode.

Element transitions are found by bracketing and bisection on a quantity
that only increases (the Moon's elongation, the sidereal Moon, the sum of
the sidereal Sun and Moon, the Sun's longitude), to 1e-7 day (under 0.01 s).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pandit_astro_engine import ephemeris

_SUN = ephemeris.SWE_BODY_ID["sun"]
_MOON = ephemeris.SWE_BODY_ID["moon"]
_TOLERANCE_DAYS = 1e-7


@dataclass(frozen=True)
class Kinematics:
    """Maximum step (days) for which the quantity is certain to advance by
    less than half a circle, so the unwrapped progress is unambiguous."""

    step_days: float


class Sky:
    """Memo-free accessors with a fixed Moshier-fallback policy."""

    def __init__(self, *, allow_moshier_fallback: bool) -> None:
        self._fallback = allow_moshier_fallback

    def sun(self, jd: float) -> float:
        return ephemeris.calculate_body(
            jd, _SUN, sidereal=False, allow_moshier_fallback=self._fallback
        ).longitude

    def moon(self, jd: float) -> float:
        return ephemeris.calculate_body(
            jd, _MOON, sidereal=False, allow_moshier_fallback=self._fallback
        ).longitude

    @staticmethod
    def lahiri(jd: float) -> float:
        return ephemeris.reference_ayanamsa_with_nutation_degrees("lahiri", jd)

    def elongation(self, jd: float) -> float:
        return (self.moon(jd) - self.sun(jd)) % 360.0

    def moon_sidereal(self, jd: float) -> float:
        return (self.moon(jd) - self.lahiri(jd)) % 360.0

    def sun_sidereal(self, jd: float) -> float:
        return (self.sun(jd) - self.lahiri(jd)) % 360.0

    def yoga_sum(self, jd: float) -> float:
        aya = self.lahiri(jd)
        return (self.sun(jd) + self.moon(jd) - 2.0 * aya) % 360.0

    def ascendant_sidereal(self, jd: float, *, latitude: float, longitude: float) -> float:
        tropical = ephemeris.calculate_ascendant(
            jd, latitude=latitude, longitude=longitude, sidereal=False
        )
        return (tropical - self.lahiri(jd)) % 360.0


#: Safe bracketing steps: elongation < 16 deg/day, Moon < 16, sum < 17.5,
#: Sun about 1 deg/day, ascendant < 450 deg/day (steps of 5 minutes).
ELONGATION = Kinematics(step_days=0.5)
MOON = Kinematics(step_days=0.5)
YOGA = Kinematics(step_days=0.5)
SUN = Kinematics(step_days=10.0)
ASCENDANT = Kinematics(step_days=5.0 / 1440.0)


def _advance(a: float, b: float) -> float:
    return (b - a) % 360.0


def next_crossing(
    fn: Callable[[float], float], kin: Kinematics, span: float, jd_start: float
) -> tuple[float, int]:
    """The first instant strictly after `jd_start` at which the monotonic
    quantity `fn` reaches a multiple of `span`, and the index (0-based) of
    the part that begins there."""
    v0 = fn(jd_start)
    part = int(v0 // span)
    target = (part + 1) * span  # may be 360
    need = target - v0
    lo, vlo, done = jd_start, v0, 0.0
    while True:
        hi = lo + kin.step_days
        vhi = fn(hi)
        step = _advance(vlo, vhi)
        if done + step >= need:
            break
        done += step
        lo, vlo = hi, vhi
    rest = need - done
    while hi - lo > _TOLERANCE_DAYS:
        mid = (lo + hi) / 2.0
        vmid = fn(mid)
        if _advance(vlo, vmid) >= rest:
            hi = mid
        else:
            rest -= _advance(vlo, vmid)
            lo, vlo = mid, vmid
    return hi, int(round(target / span)) % int(round(360.0 / span))


def previous_crossing(
    fn: Callable[[float], float], kin: Kinematics, span: float, jd_start: float
) -> float:
    """The last instant at or before `jd_start` at which `fn` reached a
    multiple of `span` (the start of the part current at `jd_start`)."""
    v0 = fn(jd_start)
    need = v0 - (v0 // span) * span
    hi, vhi, done = jd_start, v0, 0.0
    while True:
        lo = hi - kin.step_days
        vlo = fn(lo)
        step = _advance(vlo, vhi)
        if done + step >= need:
            break
        done += step
        hi, vhi = lo, vlo
    rest = need - done  # progress needed backwards from hi
    while hi - lo > _TOLERANCE_DAYS:
        mid = (lo + hi) / 2.0
        vmid = fn(mid)
        if _advance(vmid, vhi) >= rest:
            lo = mid
        else:
            rest -= _advance(vmid, vhi)
            hi, vhi = mid, vmid
    return lo


def part_index(value: float, span: float) -> int:
    """0-based part containing `value` (half-open: a boundary value belongs
    to the part that begins there)."""
    parts = int(round(360.0 / span))
    return int(value // span) % parts
