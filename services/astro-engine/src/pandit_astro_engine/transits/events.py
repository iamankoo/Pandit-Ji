"""Ingress and station solver (Phase 8, docs/ASTROLOGY_STANDARDS.md TR-08, TR-10).

A body is sampled at a body-specific step, on a grid anchored to absolute multiples
of that step (so an event's instant does not depend on the window that contains it).
Between two samples:

* if the speed changes sign, the station is located by bisection and the step is
  split there, so two boundary crossings around a station inside one step are
  not missed (each half is monotone);
* if the sign (or Nakshatra) differs between the ends of a monotone piece, the
  crossing is located by bisection on the state.

A crossing instant is the first instant, within `SEARCH_TOLERANCE_DAYS`, at
which the new state holds: the later interval owns a shared boundary (half-open
intervals). Events are reported for the half-open window [start, end); the scan
starts one step before `start` so an ingress exactly at `start` is found, and runs to
the first sample at or after `end`.

Everything here is a numerical solution and never "exact".
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_ORDER, nakshatra_position
from pandit_astro_engine.rashi import sign_index_from_longitude
from pandit_astro_engine.transits.constants import (
    MAX_EVENTS,
    SCAN_STEP_DAYS,
    SEARCH_TOLERANCE_DAYS,
)
from pandit_astro_engine.transits.models import EventKind
from pandit_astro_engine.transits.positions import BodyPosition, PositionProvider

_NAKSHATRA_INDEX = {nakshatra: index for index, nakshatra in enumerate(NAKSHATRA_ORDER)}


class EventLimitExceededError(Exception):
    """More than `MAX_EVENTS` events in one request; no partial list is kept."""


@dataclass(frozen=True)
class RawEvent:
    kind: EventKind
    body: CelestialBody
    julian_day_ut: float
    from_index: int | None
    to_index: int | None
    position: BodyPosition


def sign_state(position: BodyPosition) -> int:
    return sign_index_from_longitude(position.longitude)


def nakshatra_state(position: BodyPosition) -> int:
    return _NAKSHATRA_INDEX[nakshatra_position(position.longitude).nakshatra]


def retrograde_state(position: BodyPosition) -> bool:
    return position.retrograde


class _Budget:
    def __init__(self, limit: int) -> None:
        self.remaining = limit

    def take(self) -> None:
        self.remaining -= 1
        if self.remaining < 0:
            raise EventLimitExceededError


def _first_change(
    provider: PositionProvider,
    body: CelestialBody,
    lo: float,
    hi: float,
    state_fn: Callable[[BodyPosition], object],
    state_lo: object,
) -> float:
    """First instant (within tolerance) at which the state differs from
    `state_lo`. Requires `state(lo) == state_lo`, `state(hi) != state_lo` and a
    single change inside (lo, hi)."""
    while hi - lo > SEARCH_TOLERANCE_DAYS:
        mid = 0.5 * (lo + hi)
        if state_fn(provider.position(mid, body)) == state_lo:
            lo = mid
        else:
            hi = mid
    return hi


def scan_body(
    provider: PositionProvider,
    body: CelestialBody,
    jd_start: float,
    jd_end: float,
    kinds: frozenset[EventKind],
    budget: _Budget | None = None,
) -> list[RawEvent]:
    """Events of `body` in the half-open window [jd_start, jd_end)."""
    budget = budget if budget is not None else _Budget(MAX_EVENTS)
    step = SCAN_STEP_DAYS[body]
    want_sign = EventKind.SIGN_INGRESS in kinds
    want_nakshatra = EventKind.NAKSHATRA_INGRESS in kinds
    want_station = bool(kinds & {EventKind.STATION_RETROGRADE, EventKind.STATION_DIRECT})
    events: list[RawEvent] = []

    def emit(event: RawEvent) -> None:
        if jd_start <= event.julian_day_ut < jd_end:
            budget.take()
            events.append(event)

    # The sample grid is anchored to absolute multiples of the step (not to the window), so the
    # same event is bracketed and solved identically whatever window contains it. It starts one
    # step before the window (pre-roll) and runs to the first sample at or after the end.
    k = math.floor(jd_start / step) - 1
    t0 = k * step
    p0 = provider.position(t0, body)
    while t0 < jd_end:
        k += 1
        t1 = k * step
        p1 = provider.position(t1, body)
        pieces: list[tuple[float, BodyPosition, float, BodyPosition]] = [(t0, p0, t1, p1)]
        if p0.retrograde != p1.retrograde:
            ts = _first_change(provider, body, t0, t1, retrograde_state, p0.retrograde)
            ps = provider.position(ts, body)
            if want_station:
                kind = EventKind.STATION_RETROGRADE if ps.retrograde else EventKind.STATION_DIRECT
                if kind in kinds:
                    emit(RawEvent(kind, body, ts, None, None, ps))
            pieces = [(t0, p0, ts, ps), (ts, ps, t1, p1)]
        for a, pa, b, pb in pieces:
            for wanted, kind, state_fn in (
                (want_sign, EventKind.SIGN_INGRESS, sign_state),
                (want_nakshatra, EventKind.NAKSHATRA_INGRESS, nakshatra_state),
            ):
                if not wanted:
                    continue
                state_a = state_fn(pa)
                state_b = state_fn(pb)
                if state_a != state_b:
                    tc = _first_change(provider, body, a, b, state_fn, state_a)
                    pc = provider.position(tc, body)
                    emit(RawEvent(kind, body, tc, state_a, state_fn(pc), pc))
        t0, p0 = t1, p1
    return events


_KIND_ORDER = {
    EventKind.SIGN_INGRESS: 0,
    EventKind.NAKSHATRA_INGRESS: 1,
    EventKind.STATION_RETROGRADE: 2,
    EventKind.STATION_DIRECT: 3,
}
_BODY_ORDER = {body: index for index, body in enumerate(CelestialBody)}


def scan_window(
    provider: PositionProvider,
    bodies: tuple[CelestialBody, ...],
    jd_start: float,
    jd_end: float,
    kinds: frozenset[EventKind],
) -> list[RawEvent]:
    """All requested events for the requested bodies, in a deterministic order:
    by instant, then body order, then kind order."""
    budget = _Budget(MAX_EVENTS)
    events: list[RawEvent] = []
    for body in dict.fromkeys(bodies):  # de-duplicate, keep order
        events.extend(scan_body(provider, body, jd_start, jd_end, kinds, budget))
    events.sort(key=lambda e: (e.julian_day_ut, _BODY_ORDER[e.body], _KIND_ORDER[e.kind]))
    return events
