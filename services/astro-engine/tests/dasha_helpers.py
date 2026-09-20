"""Shared helpers for the Phase 7 Dasha tests."""

from __future__ import annotations

import datetime as dt
from fractions import Fraction

from pandit_astro_engine.dashas import (
    DashaConfiguration,
    DashaFacts,
    DashaLevel,
    DashaRequest,
    calculate_vimshottari,
)
from pandit_astro_engine.dashas.constants import (
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
)
from pandit_astro_engine.dashas.models import BirthTimeInput
from pandit_astro_engine.dashas.profiles import YEAR_365_2425_ID, get_year_length_profile
from pandit_astro_engine.dashas.vimshottari import year_microseconds

UTC = dt.timezone.utc
BIRTH = dt.datetime(1990, 6, 15, 4, 30, 0, tzinfo=UTC)
ONE_US = dt.timedelta(microseconds=1)

#: Width of one Nakshatra in degrees, as an exact fraction.
SPAN = Fraction(40, 3)


def mid_longitude(index: int) -> float:
    """A longitude in the middle of Nakshatra `index`."""
    return float(SPAN * index + SPAN / 2)


def build(
    longitude: float | None,
    *,
    birth: dt.datetime = BIRTH,
    config: DashaConfiguration | None = None,
    birth_time: BirthTimeInput | None = None,
) -> DashaFacts:
    return calculate_vimshottari(
        DashaRequest(
            moon_longitude_degrees=longitude,
            birth_utc=birth,
            config=config or DashaConfiguration(),
            birth_time=birth_time or BirthTimeInput(),
        )
    )


def children_of(facts: DashaFacts, parent_id: str) -> list:  # type: ignore[type-arg]
    return [p for p in facts.periods if p.parent_id == parent_id]


def assert_invariants(facts: DashaFacts) -> None:
    """The mathematical invariants of section 24 of the Phase 7 directive."""
    assert facts.periods, "successful result without periods"
    by_id = {p.period_id: p for p in facts.periods}
    assert len(by_id) == len(facts.periods), "period IDs are not unique"
    sequence = list(VIMSHOTTARI_SEQUENCE)

    mahadashas = [p for p in facts.periods if p.level is DashaLevel.MAHADASHA]
    assert mahadashas[0].start_utc == facts.birth_utc
    for left, right in zip(mahadashas, mahadashas[1:], strict=False):
        assert left.end_utc == right.start_utc  # no gap, no overlap
        expected = sequence[(sequence.index(left.lord) + 1) % 9]
        assert right.lord is expected
    horizon_end = facts.birth_utc + dt.timedelta(microseconds=0)  # birth
    assert mahadashas[-1].end_utc > horizon_end

    for parent in facts.periods:
        kids = children_of(facts, parent.period_id)
        if parent.level is DashaLevel.PRATYANTAR:
            assert not kids
            continue
        if facts.depth == 1 or (facts.depth == 2 and parent.level is DashaLevel.ANTARDASHA):
            assert not kids
            continue
        assert kids, f"{parent.period_id} has no children"
        assert kids[0].start_utc == parent.start_utc
        assert kids[-1].end_utc == parent.end_utc
        for left, right in zip(kids, kids[1:], strict=False):
            assert left.end_utc == right.start_utc
        assert sum(k.duration_microseconds for k in kids) == parent.duration_microseconds
        for k in kids:
            assert parent.start_utc <= k.start_utc <= k.end_utc <= parent.end_utc
            assert k.path[:-1] == parent.path
        # children run through the sequence starting at the parent's own lord,
        # by nominal position (truncated leading children are omitted).
        indexes = [k.sequence_index for k in kids]
        assert indexes == sorted(indexes) and indexes == list(range(indexes[0], 9))
        for k in kids:
            expected_lord = sequence[(sequence.index(parent.lord) + k.sequence_index) % 9]
            assert k.lord is expected_lord
        if not parent.truncated_at_birth:
            assert indexes[0] == 0 and len(kids) == 9
            assert kids[0].lord is parent.lord


def exact_full_duration(years: int, profile_id: str = YEAR_365_2425_ID) -> int:
    profile = get_year_length_profile(profile_id)
    assert profile is not None
    return int(years * year_microseconds(profile))


TOTAL = VIMSHOTTARI_TOTAL_YEARS
YEARS = VIMSHOTTARI_YEARS
