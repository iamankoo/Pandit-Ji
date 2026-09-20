"""Period lookup: historical, current, future, boundaries and range status."""

from __future__ import annotations

import datetime as dt
import random
import time

import pytest
from dasha_helpers import BIRTH, ONE_US, UTC, build

from pandit_astro_engine.dashas import (
    DashaConfiguration,
    DashaLevel,
    DashaReason,
    DashaStatus,
    DashaTimeline,
)
from pandit_astro_engine.dashas.models import RangePosition
from pandit_astro_engine.models import CelestialBody

B = CelestialBody


@pytest.fixture(scope="module")
def facts():  # type: ignore[no-untyped-def]
    return build(123.4)


@pytest.fixture(scope="module")
def timeline(facts):  # type: ignore[no-untyped-def]
    return DashaTimeline(facts)


def _md(facts, index: int):  # type: ignore[no-untyped-def]
    return [p for p in facts.periods if p.level is DashaLevel.MAHADASHA][index]


def test_at_birth_the_first_period_owns_the_instant(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    result = timeline.resolve(BIRTH)
    assert result.range_position is RangePosition.WITHIN_TIMELINE
    assert result.levels[0].period_id == facts.periods[0].period_id
    assert result.levels[0].elapsed_microseconds == 0
    assert result.path[0] == facts.starting.lord.value


def test_shared_mahadasha_boundary_belongs_to_the_later_period(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    first, second = _md(facts, 0), _md(facts, 1)
    assert first.end_utc == second.start_utc
    at = timeline.resolve(first.end_utc)
    assert at.levels[0].period_id == second.period_id
    assert at.levels[0].elapsed_microseconds == 0
    before = timeline.resolve(first.end_utc - ONE_US)
    assert before.levels[0].period_id == first.period_id
    assert before.levels[0].remaining_microseconds == 1


def test_every_shared_boundary_at_every_level_belongs_to_the_later_period(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    for level in DashaLevel:
        for transition in timeline.transitions(level):
            after = timeline.resolve(transition.at_utc)
            owner = next(p for p in after.levels if p.level is level)
            assert owner.period_id == transition.to_period_id
            if transition.at_utc - ONE_US >= facts.timeline_start_utc:
                before = timeline.resolve(transition.at_utc - ONE_US)
                previous = next(p for p in before.levels if p.level is level)
                assert previous.period_id == transition.from_period_id


def test_resolution_returns_all_three_levels_that_nest(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    at = BIRTH + dt.timedelta(days=12345)
    result = timeline.resolve(at)
    assert [level.level for level in result.levels] == list(DashaLevel)
    for outer, inner in zip(result.levels, result.levels[1:], strict=False):
        assert outer.start_utc <= inner.start_utc <= at < inner.end_utc <= outer.end_utc
    for level in result.levels:
        assert level.elapsed_microseconds + level.remaining_microseconds == (
            (level.end_utc - level.start_utc) // ONE_US
        )
        assert level.start_utc <= at < level.end_utc


def test_before_the_timeline_is_out_of_range(timeline) -> None:  # type: ignore[no-untyped-def]
    result = timeline.resolve(BIRTH - ONE_US)
    assert result.range_position is RangePosition.BEFORE_TIMELINE
    assert result.levels == ()


def test_the_timeline_end_is_exclusive(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    end = facts.timeline_end_utc
    assert timeline.resolve(end).range_position is RangePosition.AT_OR_AFTER_TIMELINE_END
    assert timeline.resolve(end).levels == ()
    last = timeline.resolve(end - ONE_US)
    assert last.range_position is RangePosition.WITHIN_TIMELINE
    assert len(last.levels) == 3
    assert timeline.resolve(end + dt.timedelta(days=9999)).range_position is (
        RangePosition.AT_OR_AFTER_TIMELINE_END
    )


def test_naive_query_instants_are_rejected(timeline) -> None:  # type: ignore[no-untyped-def]
    result = timeline.resolve(dt.datetime(2000, 1, 1))
    assert result.status is DashaStatus.INVALID_INPUT
    assert result.reason_code is DashaReason.NAIVE_DATETIME


def test_query_instants_in_other_offsets_are_normalized_to_utc(timeline) -> None:  # type: ignore[no-untyped-def]
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    at_utc = BIRTH + dt.timedelta(days=4000)
    assert timeline.resolve(at_utc.astimezone(ist)).levels == timeline.resolve(at_utc).levels


def test_historical_current_and_future_lookups(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    now = BIRTH + dt.timedelta(days=365 * 34)
    past = timeline.resolve(now - dt.timedelta(days=365 * 20))
    current = timeline.resolve(now)
    future = timeline.resolve(now + dt.timedelta(days=365 * 25))
    for result in (past, current, future):
        assert result.range_position is RangePosition.WITHIN_TIMELINE
    assert past.levels[0].end_utc <= current.levels[0].end_utc <= future.levels[0].end_utc
    assert past.levels[0].period_id != future.levels[0].period_id


def test_lookup_agrees_with_a_brute_force_scan_at_random_instants(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    rng = random.Random(7)
    span = (facts.timeline_end_utc - BIRTH) // ONE_US
    for _ in range(300):
        at = BIRTH + dt.timedelta(microseconds=rng.randrange(span))
        result = timeline.resolve(at)
        for level in DashaLevel:
            owners = [
                p for p in facts.periods if p.level is level and p.start_utc <= at < p.end_utc
            ]
            assert len(owners) == 1  # no gap, no overlap
            position = next(p for p in result.levels if p.level is level)
            assert position.period_id == owners[0].period_id


def test_lookup_for_a_depth_limited_timeline(facts) -> None:  # type: ignore[no-untyped-def]
    shallow = DashaTimeline(build(123.4, config=DashaConfiguration(depth=2)))
    result = shallow.resolve(BIRTH + dt.timedelta(days=9000))
    assert [level.level for level in result.levels] == [
        DashaLevel.MAHADASHA,
        DashaLevel.ANTARDASHA,
    ]


def test_lookup_on_a_failed_result_reports_that_status() -> None:
    failed = DashaTimeline(build(None))
    result = failed.resolve(BIRTH)
    assert result.status is DashaStatus.INVALID_INPUT
    assert result.reason_code is DashaReason.MOON_LONGITUDE_MISSING


def test_transitions_link_consecutive_periods(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    mahadashas = [p for p in facts.periods if p.level is DashaLevel.MAHADASHA]
    transitions = timeline.transitions(DashaLevel.MAHADASHA)
    assert len(transitions) == len(mahadashas) - 1
    for transition, (left, right) in zip(
        transitions, zip(mahadashas, mahadashas[1:], strict=False), strict=True
    ):
        assert transition.at_utc == right.start_utc == left.end_utc
        assert (transition.from_lord, transition.to_lord) == (left.lord, right.lord)


def test_periods_in_window_and_by_lord(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    window = timeline.periods_in_window(
        BIRTH, BIRTH + dt.timedelta(days=365 * 30), DashaLevel.MAHADASHA
    )
    assert window.status is DashaStatus.SUCCESS and window.periods
    assert all(p.start_utc < BIRTH + dt.timedelta(days=365 * 30) for p in window.periods)
    reversed_window = timeline.periods_in_window(BIRTH + ONE_US, BIRTH, DashaLevel.MAHADASHA)
    assert reversed_window.reason_code is DashaReason.REVERSED_INTERVAL
    naive = timeline.periods_in_window(dt.datetime(2000, 1, 1), BIRTH, DashaLevel.MAHADASHA)
    assert naive.reason_code is DashaReason.NAIVE_DATETIME

    venus = timeline.periods_for_lord("venus", DashaLevel.ANTARDASHA)
    assert venus.status is DashaStatus.SUCCESS
    assert venus.periods and all(p.lord is B.VENUS for p in venus.periods)
    unknown = timeline.periods_for_lord("pluto", DashaLevel.ANTARDASHA)
    assert unknown.status is DashaStatus.INVALID_INPUT
    assert unknown.reason_code is DashaReason.UNKNOWN_LORD


def test_many_lookups_are_fast(timeline, facts) -> None:  # type: ignore[no-untyped-def]
    rng = random.Random(3)
    span = (facts.timeline_end_utc - BIRTH) // ONE_US
    instants = [BIRTH + dt.timedelta(microseconds=rng.randrange(span)) for _ in range(2000)]
    started = time.perf_counter()
    for at in instants:
        timeline.resolve(at)
    assert time.perf_counter() - started < 2.0


def test_utc_is_the_reference_zone() -> None:
    assert UTC.utcoffset(None) == dt.timedelta(0)
