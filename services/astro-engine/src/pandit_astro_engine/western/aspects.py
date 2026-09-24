"""Western aspect detection (Phase 9 WP-D, WD-09 to WD-14).

Pure function of longitudes and speeds: no ephemeris, no sign or house
input, and no use of Vedic graha drishti, Rashi Drishti or Partial/Degree
Drishti. Each unordered pair of aspect bodies is evaluated once, in the body
profile's order, so a pair never appears twice or mirrored.

Arithmetic: the separation is the shorter arc between the two longitudes,
in [0, 180]; the deviation is its distance from the aspect's exact angle;
an aspect holds when the deviation is at most the allowed orb (inclusive).
The comparison uses exact rational arithmetic on the float inputs, so the
result at an orb boundary does not depend on float rounding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from pandit_astro_engine.western.constants import ASPECT_ANGLE, WesternBody
from pandit_astro_engine.western.models import (
    MotionState,
    NotEvaluablePair,
    WesternAspect,
    WesternReason,
)
from pandit_astro_engine.western.profiles import (
    AspectSetProfileDef,
    OrbProfileDef,
    max_orb,
)
from pandit_astro_engine.western.zodiac import normalize_longitude

_FULL = Fraction(360)
_HALF = Fraction(180)


@dataclass(frozen=True)
class AspectInput:
    body: WesternBody
    longitude: float
    speed_longitude: float


def separation(longitude_a: float, longitude_b: float) -> Fraction:
    """Shorter arc between two longitudes, exact, in [0, 180]."""
    forward = (
        Fraction(normalize_longitude(longitude_b)) - Fraction(normalize_longitude(longitude_a))
    ) % _FULL
    return forward if forward <= _HALF else _FULL - forward


def _motion(
    a: AspectInput, b: AspectInput, angle: Fraction
) -> tuple[MotionState, WesternReason | None]:
    forward = (
        Fraction(normalize_longitude(b.longitude)) - Fraction(normalize_longitude(a.longitude))
    ) % _FULL
    arc = forward if forward <= _HALF else _FULL - forward
    if arc == angle:
        return MotionState.EXACT, None
    relative = Fraction(b.speed_longitude) - Fraction(a.speed_longitude)
    # d(arc)/dt: the forward arc grows with the relative speed; when the
    # shorter arc is measured the other way round, it shrinks instead.
    arc_rate = relative if forward < _HALF else -relative
    deviation_rate = arc_rate if arc > angle else -arc_rate
    if deviation_rate == 0:
        return MotionState.NOT_EVALUABLE, WesternReason.RELATIVE_MOTION_ZERO
    if deviation_rate < 0:
        return MotionState.APPLYING, None
    return MotionState.SEPARATING, None


def evaluate_aspects(
    inputs: Sequence[AspectInput],
    aspect_set: AspectSetProfileDef,
    orbs: OrbProfileDef,
) -> tuple[tuple[WesternAspect, ...], tuple[NotEvaluablePair, ...]]:
    """All in-orb aspects between the given bodies, plus the pairs the orb
    profile cannot evaluate (for example an outer planet under Lilly's
    orbs). At most one aspect can hold per pair: every profile's largest orb
    is below half the smallest gap between aspect angles (checked by tests)."""
    found: list[WesternAspect] = []
    blocked: list[NotEvaluablePair] = []
    for i, first in enumerate(inputs):
        for second in inputs[i + 1 :]:
            allowed_by_aspect = {
                aspect: max_orb(orbs, aspect, first.body, second.body)
                for aspect in aspect_set.aspects
            }
            if any(value is None for value in allowed_by_aspect.values()):
                blocked.append(
                    NotEvaluablePair(
                        body_a=first.body,
                        body_b=second.body,
                        reason=WesternReason.ORB_NOT_DEFINED_FOR_BODY,
                    )
                )
                continue
            arc = separation(first.longitude, second.longitude)
            for aspect in aspect_set.aspects:
                allowed = allowed_by_aspect[aspect]
                assert allowed is not None
                angle = Fraction(ASPECT_ANGLE[aspect])
                deviation = abs(arc - angle)
                if deviation <= Fraction(allowed):
                    state, reason = _motion(first, second, angle)
                    found.append(
                        WesternAspect(
                            body_a=first.body,
                            body_b=second.body,
                            aspect=aspect,
                            exact_angle=float(angle),
                            separation=float(arc),
                            deviation=float(deviation),
                            orb_allowed=allowed,
                            motion_state=state,
                            motion_reason=reason,
                        )
                    )
    return tuple(found), tuple(blocked)
