"""The ingress and station solver on exact synthetic motion
(docs/ASTROLOGY_STANDARDS.md TR-08, TR-10)."""

from __future__ import annotations

import pytest
from transit_helpers import JD0, SyntheticProvider, linear, parabola, sinusoid, static

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.transits import events as EV
from pandit_astro_engine.transits.constants import SCAN_STEP_DAYS, SEARCH_TOLERANCE_DAYS
from pandit_astro_engine.transits.models import EventKind

SIGN = frozenset({EventKind.SIGN_INGRESS})
NAK = frozenset({EventKind.NAKSHATRA_INGRESS})
STATION = frozenset({EventKind.STATION_RETROGRADE, EventKind.STATION_DIRECT})
ALL = SIGN | NAK | STATION


def scan(provider, body, start, end, kinds):  # type: ignore[no-untyped-def]
    return EV.scan_body(provider, body, JD0 + start, JD0 + end, kinds)


# --------------------------------------------------------------------------
# Sign ingress: exactness and boundary ownership
# --------------------------------------------------------------------------


def test_forward_ingress_is_found_within_the_search_tolerance() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})  # crosses 30 at day 5.0
    (event,) = scan(provider, B.SUN, 0, 20, SIGN)
    assert event.kind == EventKind.SIGN_INGRESS
    assert (event.from_index, event.to_index) == (0, 1)
    assert 0.0 <= event.julian_day_ut - (JD0 + 5.0) <= SEARCH_TOLERANCE_DAYS


def test_the_later_interval_owns_the_shared_boundary() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    (event,) = scan(provider, B.SUN, 0, 20, SIGN)
    assert EV.sign_state(provider.position(event.julian_day_ut, B.SUN)) == 1
    just_before = event.julian_day_ut - 2 * SEARCH_TOLERANCE_DAYS
    assert EV.sign_state(provider.position(just_before, B.SUN)) == 0
    # A body exactly at 30.0 degrees is in the new sign (half-open, lower-inclusive).
    exact = SyntheticProvider({B.SUN: static(30.0)})
    assert EV.sign_state(exact.position(JD0, B.SUN)) == 1


def test_longitude_wrap_from_pisces_to_aries_is_an_ingress() -> None:
    provider = SyntheticProvider({B.MARS: linear(359.5, 0.25)})
    (event,) = scan(provider, B.MARS, 0, 10, SIGN)
    assert (event.from_index, event.to_index) == (11, 0)
    assert event.julian_day_ut == pytest.approx(JD0 + 2.0, abs=1e-7)


def test_a_body_staying_in_one_sign_has_no_events() -> None:
    provider = SyntheticProvider({B.SATURN: linear(100.0, 0.02)})
    assert scan(provider, B.SATURN, 0, 100, ALL) == []


def test_two_ingresses_in_one_window_are_chained_and_ordered() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.0, 1.0)})  # crosses 30 at 1, 60 at 31
    events = scan(provider, B.SUN, 0, 40, SIGN)
    assert [(e.from_index, e.to_index) for e in events] == [(0, 1), (1, 2)]
    assert events[0].julian_day_ut < events[1].julian_day_ut
    assert events[1].julian_day_ut == pytest.approx(JD0 + 31.0, abs=1e-7)


def test_backward_ingress_and_retrograde_reentry() -> None:
    # Oscillates around 30 degrees with a 100-day period: up at day 0, down at day 50.
    provider = SyntheticProvider({B.SATURN: sinusoid(30.0, 1.0, 100.0)})
    events = scan(provider, B.SATURN, 10, 190, SIGN)
    # Crossings of 30 degrees: down at day 50, up at 100, down at 150 (the start is above 30).
    assert [(e.from_index, e.to_index) for e in events] == [(1, 0), (0, 1), (1, 0)]
    for event, day in zip(events, (50.0, 100.0, 150.0), strict=True):
        assert event.julian_day_ut == pytest.approx(JD0 + day, abs=1e-6)
    for event in events:
        forward = event.to_index == (event.from_index + 1) % 12
        assert event.position.retrograde == (not forward)


def test_ingress_exactly_on_a_scan_sample_is_still_found_once() -> None:
    step = SCAN_STEP_DAYS[B.SUN]
    provider = SyntheticProvider({B.SUN: linear(30.0 - step * 0.5, 0.5)})  # crosses at 2 * step
    events = scan(provider, B.SUN, 0, 10, SIGN)
    assert len(events) == 1


# --------------------------------------------------------------------------
# Window: half-open [start, end), pre-roll
# --------------------------------------------------------------------------


def test_an_ingress_exactly_at_the_window_start_is_included() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    events = scan(provider, B.SUN, 5.0, 20, SIGN)
    assert len(events) == 1
    assert events[0].julian_day_ut >= JD0 + 5.0


def test_an_ingress_exactly_at_the_window_end_is_excluded() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    assert scan(provider, B.SUN, 0, 5.0, SIGN) == []
    assert len(scan(provider, B.SUN, 0, 5.0 + 1e-6, SIGN)) == 1


def test_an_ingress_before_the_window_is_not_reported() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    assert scan(provider, B.SUN, 5.5, 20, SIGN) == []


def test_adjacent_windows_partition_the_events() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.0, 1.0)})
    whole = scan(provider, B.SUN, 0, 40, SIGN)
    left = scan(provider, B.SUN, 0, 20, SIGN)
    right = scan(provider, B.SUN, 20, 40, SIGN)
    assert [e.julian_day_ut for e in whole] == [e.julian_day_ut for e in left + right]


# --------------------------------------------------------------------------
# Stations
# --------------------------------------------------------------------------


def test_stations_alternate_and_sit_where_the_speed_changes_sign() -> None:
    provider = SyntheticProvider({B.MARS: sinusoid(100.0, 6.0, 60.0, drift=0.5)})
    events = scan(provider, B.MARS, 0, 300, STATION)
    assert len(events) >= 8
    kinds = [e.kind for e in events]
    for previous, current in zip(kinds, kinds[1:], strict=False):
        assert previous != current
    for event in events:
        assert abs(event.position.speed_longitude) < 1e-6
        assert event.position.retrograde == (event.kind == EventKind.STATION_RETROGRADE)


def test_a_body_that_never_reverses_has_no_stations() -> None:
    provider = SyntheticProvider({B.SUN: linear(10.0, 0.9)})
    assert scan(provider, B.SUN, 0, 400, STATION) == []


def test_mean_node_like_constant_retrograde_has_no_stations() -> None:
    provider = SyntheticProvider({B.RAHU: linear(100.0, -0.053)})
    assert scan(provider, B.RAHU, 0, 3000, STATION) == []
    events = scan(provider, B.RAHU, 0, 3000, SIGN)
    assert events and all(e.to_index == (e.from_index - 1) % 12 for e in events)
    assert all(e.position.retrograde for e in events)


def test_a_double_crossing_around_a_station_inside_one_step_is_not_missed() -> None:
    # Saturn's step is 5 days. The longitude peaks at 30.0001 at day 2.5 and is below 30 at
    # both step ends: only the station split can see the up- and the down-crossing.
    step = SCAN_STEP_DAYS[B.SATURN]
    assert step == 5.0
    provider = SyntheticProvider({B.SATURN: parabola(30.0001, 2.5, 1e-4)})
    events = scan(provider, B.SATURN, 0, 5.0, SIGN | STATION)
    by_kind = [e.kind for e in events]
    assert by_kind.count(EventKind.SIGN_INGRESS) == 2
    assert by_kind.count(EventKind.STATION_RETROGRADE) == 1
    ingress = [e for e in events if e.kind == EventKind.SIGN_INGRESS]
    assert (ingress[0].from_index, ingress[0].to_index) == (0, 1)
    assert (ingress[1].from_index, ingress[1].to_index) == (1, 0)
    assert ingress[0].julian_day_ut == pytest.approx(JD0 + 1.5, abs=1e-6)
    assert ingress[1].julian_day_ut == pytest.approx(JD0 + 3.5, abs=1e-6)
    assert ingress[0].position.retrograde is False and ingress[1].position.retrograde is True


def test_a_station_at_an_exact_sign_boundary_is_consistent() -> None:
    provider = SyntheticProvider({B.SATURN: parabola(30.0, 10.0, 1e-3)})
    events = scan(provider, B.SATURN, 0, 30, SIGN | STATION)
    assert [e.kind for e in events].count(EventKind.STATION_RETROGRADE) == 1
    # The peak is exactly 30.0, i.e. in the new sign at the peak instant only: an ingress and
    # an immediate re-ingress, both at the peak (within the search tolerance), or neither.
    ingress = [e for e in events if e.kind == EventKind.SIGN_INGRESS]
    assert len(ingress) in (0, 2)
    for event in events:
        assert event.julian_day_ut == pytest.approx(JD0 + 10.0, abs=1e-5)
    if ingress:
        assert [(e.from_index, e.to_index) for e in ingress] == [(0, 1), (1, 0)]


# --------------------------------------------------------------------------
# Nakshatra ingress
# --------------------------------------------------------------------------


def test_nakshatra_ingress_uses_the_exact_thirteen_twenty_boundary() -> None:
    boundary = 40.0 / 3.0  # 13 deg 20 min: Ashwini | Bharani
    provider = SyntheticProvider({B.MOON: linear(boundary - 0.5, 1.0)})
    (event,) = scan(provider, B.MOON, 0, 5, NAK)
    assert event.kind == EventKind.NAKSHATRA_INGRESS
    assert (event.from_index, event.to_index) == (0, 1)
    assert event.julian_day_ut == pytest.approx(JD0 + 0.5, abs=1e-6)


def test_nakshatra_ingress_is_not_reported_unless_asked() -> None:
    provider = SyntheticProvider({B.MOON: linear(13.0, 1.0)})
    assert scan(provider, B.MOON, 0, 5, SIGN | STATION) == []


def test_a_fast_moon_is_never_stepped_over_a_nakshatra() -> None:
    provider = SyntheticProvider({B.MOON: linear(0.0, 15.0)})  # fastest plausible Moon
    events = scan(provider, B.MOON, 0, 30, NAK)
    # 450 degrees: boundaries at 0 (the start itself, 26 -> 0), 13.33, ..., 446.67: 34 of them.
    assert len(events) == 34
    assert [e.to_index for e in events] == [i % 27 for i in range(34)]


# --------------------------------------------------------------------------
# scan_window: ordering, de-duplication, limits, determinism
# --------------------------------------------------------------------------


def test_scan_window_orders_by_instant_then_body_then_kind() -> None:
    provider = SyntheticProvider(
        {B.SUN: linear(29.0, 1.0), B.MARS: linear(29.0, 1.0), B.MOON: linear(29.0, 1.0)}
    )
    events = EV.scan_window(provider, (B.MARS, B.MOON, B.SUN), JD0, JD0 + 3, SIGN)
    assert len(events) == 3
    # Identical motion gives identical instants, so the tie is broken by the fixed body order.
    assert len({e.julian_day_ut for e in events}) == 1
    assert [e.body for e in events] == [B.SUN, B.MOON, B.MARS]
    keys = [(e.julian_day_ut, list(B).index(e.body)) for e in events]
    assert keys == sorted(keys)


def test_scan_window_ignores_duplicate_bodies() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    once = EV.scan_window(provider, (B.SUN,), JD0, JD0 + 20, SIGN)
    twice = EV.scan_window(provider, (B.SUN, B.SUN), JD0, JD0 + 20, SIGN)
    assert once == twice and len(once) == 1


def test_the_event_limit_raises_and_keeps_no_partial_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EV, "MAX_EVENTS", 3)
    provider = SyntheticProvider({B.SUN: linear(0.0, 1.0)})  # a new sign every 30 days
    with pytest.raises(EV.EventLimitExceededError):
        EV.scan_window(provider, (B.SUN,), JD0, JD0 + 400, SIGN)
    # Under the limit: boundaries at day 0 (the start), 30 and 60 are exactly 3 events.
    assert len(EV.scan_window(provider, (B.SUN,), JD0, JD0 + 89, SIGN)) == 3


def test_the_event_budget_is_shared_across_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EV, "MAX_EVENTS", 3)
    provider = SyntheticProvider({B.SUN: linear(0.0, 1.0), B.MARS: linear(0.0, 1.0)})
    with pytest.raises(EV.EventLimitExceededError):
        EV.scan_window(provider, (B.SUN, B.MARS), JD0, JD0 + 100, SIGN)


def test_repeated_scans_are_identical() -> None:
    provider = SyntheticProvider({B.MERCURY: sinusoid(30.0, 4.0, 40.0, drift=0.3)})
    first = EV.scan_window(provider, (B.MERCURY,), JD0, JD0 + 400, ALL)
    second = EV.scan_window(provider, (B.MERCURY,), JD0, JD0 + 400, ALL)
    assert first == second and first


def test_the_search_uses_few_position_calls() -> None:
    provider = SyntheticProvider({B.SATURN: linear(29.99, 0.05)})
    scan(provider, B.SATURN, 0, 50, SIGN)
    assert provider.calls < 60


def test_an_events_instant_does_not_depend_on_the_window_that_contains_it() -> None:
    # The scan grid is anchored to absolute multiples of the step, so an event is bracketed and
    # solved identically whatever window it falls in (no dependence on the window start).
    provider = SyntheticProvider({B.MARS: sinusoid(100.0, 6.0, 60.0, drift=0.5)})
    reference = scan(provider, B.MARS, -60, 400, STATION | SIGN)
    assert len(reference) > 10
    for start, end in ((-7.3, 301.9), (13.7, 250.1), (40.2, 150.0), (0.0, 300.0)):
        part = scan(provider, B.MARS, start, end, STATION | SIGN)
        expected = [e for e in reference if JD0 + start <= e.julian_day_ut < JD0 + end]
        assert expected
        assert [(e.kind, e.julian_day_ut) for e in part] == [
            (e.kind, e.julian_day_ut) for e in expected
        ]
