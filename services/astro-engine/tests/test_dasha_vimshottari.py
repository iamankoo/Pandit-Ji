"""Pure Vimshottari arithmetic: starting lord, balance, nested periods."""

from __future__ import annotations

import datetime as dt
import math
import random
from fractions import Fraction

import pytest
from dasha_helpers import (
    BIRTH,
    ONE_US,
    SPAN,
    UTC,
    YEARS,
    assert_invariants,
    build,
    children_of,
    exact_full_duration,
    mid_longitude,
)

from pandit_astro_engine.dashas import DashaConfiguration, DashaLevel, DashaStatus
from pandit_astro_engine.dashas.constants import VIMSHOTTARI_SEQUENCE
from pandit_astro_engine.dashas.profiles import (
    YEAR_360_ID,
    YEAR_365_25_ID,
    YEAR_365_2425_ID,
)
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_LORD, NAKSHATRA_ORDER

B = CelestialBody


# ---------------------------------------------------------------- starting lord


@pytest.mark.parametrize("index", range(27))
def test_starting_lord_follows_the_nakshatra_lord_table(index: int) -> None:
    facts = build(mid_longitude(index))
    assert facts.status is DashaStatus.SUCCESS
    assert facts.starting is not None
    assert facts.starting.nakshatra is NAKSHATRA_ORDER[index]
    assert facts.starting.lord is NAKSHATRA_LORD[NAKSHATRA_ORDER[index]]
    assert facts.starting.lord is VIMSHOTTARI_SEQUENCE[index % 9]
    assert facts.periods[0].lord is facts.starting.lord


# ---------------------------------------------------------------- balance


def test_balance_fraction_is_exact_for_an_exactly_representable_longitude() -> None:
    # 10.0 deg is exactly 3/4 of the way through Ashwini (13 deg 20 min = 40/3 deg).
    facts = build(10.0)  # Ashwini, Ketu 7 years
    assert facts.starting is not None
    assert facts.starting.elapsed_fraction.to_fraction() == Fraction(3, 4)
    assert facts.starting.remaining_fraction.to_fraction() == Fraction(1, 4)
    assert facts.starting.remaining_duration_microseconds == exact_full_duration(7) // 4
    assert facts.starting.remaining_duration_microseconds_exact.to_fraction() == (
        Fraction(exact_full_duration(7), 4)
    )


def test_balance_fraction_of_a_mid_nakshatra_longitude_is_the_exact_float_value() -> None:
    facts = build(mid_longitude(0))  # nearest float to 20/3 is not exactly 20/3
    assert facts.starting is not None
    assert abs(facts.starting.remaining_fraction.to_fraction() - Fraction(1, 2)) < Fraction(
        1, 10**15
    )


@pytest.mark.parametrize("index", range(27))
def test_exact_nakshatra_boundary_gives_the_upper_lord_a_full_mahadasha(index: int) -> None:
    boundary = float(SPAN * index)
    facts = build(boundary)
    assert facts.starting is not None
    lord = VIMSHOTTARI_SEQUENCE[index % 9]
    # float(boundary) may sit a hair off the true rational boundary; the exact
    # classification of that float decides, and it must be self-consistent.
    exact = Fraction(boundary)
    expected_index = int(exact * 27 // 360)
    assert facts.starting.nakshatra is NAKSHATRA_ORDER[expected_index % 27]
    if Fraction(boundary) == SPAN * index:
        assert facts.starting.lord is lord
        assert facts.starting.elapsed_fraction.to_fraction() == 0
        assert facts.starting.remaining_fraction.to_fraction() == 1
        assert facts.periods[0].duration_microseconds == exact_full_duration(YEARS[lord])
        assert facts.periods[0].truncated_at_birth is False


def test_exactly_representable_boundaries_get_a_full_first_mahadasha() -> None:
    for degrees, lord in ((40.0, B.MOON), (80.0, B.JUPITER), (120.0, B.KETU), (200.0, B.JUPITER)):
        facts = build(degrees)
        assert facts.starting is not None
        assert facts.starting.lord is lord
        assert facts.starting.remaining_fraction.to_fraction() == 1


def test_just_below_a_boundary_is_the_lower_lord_with_almost_no_balance() -> None:
    facts = build(math.nextafter(40.0, 0.0))  # Krittika, Sun, last instant
    assert facts.starting is not None
    assert facts.starting.lord is B.SUN
    assert facts.starting.remaining_fraction.to_fraction() < Fraction(1, 10**12)
    assert facts.starting.near_boundary is True
    assert facts.periods[0].duration_microseconds < 1000  # a few hundred microseconds
    assert_invariants(facts)


def test_just_above_a_boundary_is_the_upper_lord_with_almost_a_full_balance() -> None:
    facts = build(math.nextafter(40.0, 360.0))
    assert facts.starting is not None
    assert facts.starting.lord is B.MOON
    assert facts.starting.remaining_fraction.to_fraction() > 1 - Fraction(1, 10**12)


def test_360_degrees_is_zero_degrees_ashwini_pada_1() -> None:
    at_360 = build(360.0)
    at_0 = build(0.0)
    assert at_360.starting is not None and at_0.starting is not None
    assert (at_360.starting.nakshatra, at_360.starting.pada) == (at_0.starting.nakshatra, 1)
    assert at_360.starting.lord is B.KETU
    assert at_360.periods == at_0.periods


def test_negative_and_over_360_longitudes_normalize_like_the_phase5_rule() -> None:
    assert build(-1e-9).starting is not None
    assert build(-1e-9).starting.lord is B.MERCURY  # type: ignore[union-attr]  # Revati
    assert build(-320.0).starting.lord is B.MOON  # type: ignore[union-attr]  # = 40 deg, Rohini
    assert build(360.000001).starting.lord is B.KETU  # type: ignore[union-attr]  # Ashwini
    assert build(400.0).periods == build(40.0).periods


def test_known_unchanged_tiny_negative_float_behaviour() -> None:
    """A negative float smaller than ~2.8e-14 degrees normalizes to 360.0 and
    so is 0 (Ashwini): documented standards v1.4.1 behaviour, deliberately
    unchanged."""
    facts = build(-1e-15)
    assert facts.starting is not None
    assert facts.starting.lord is B.KETU
    assert facts.starting.normalized_longitude == 360.0


def test_independent_worked_example_uttara_kalamrita_p142() -> None:
    """Translator's worked example (OCR-level, Tier 3): Moon at 18 deg 34' 3"
    Kumbha (318.5675 deg, Satabhisha, Rahu 18 years) gives an arc-based
    balance of 1 year 11 months 6 days, counting 30-day months. Under the
    360-day year profile the engine's balance must agree to within a day."""
    longitude = 300.0 + 18.0 + 34.0 / 60.0 + 3.0 / 3600.0
    facts = build(longitude, config=DashaConfiguration(year_length_profile_id=YEAR_360_ID))
    assert facts.starting is not None
    assert facts.starting.nakshatra.value == "shatabhisha"
    assert facts.starting.lord is B.RAHU
    days = facts.starting.remaining_duration_microseconds / (86_400 * 10**6)
    assert abs(days - (360 + 11 * 30 + 6)) < 1.0
    assert abs(float(facts.starting.remaining_fraction.approx()) - 0.10744) < 1e-4


# ---------------------------------------------------------------- generation


def test_mahadasha_sequence_rotates_from_the_starting_lord() -> None:
    facts = build(mid_longitude(3))  # Rohini: Moon
    mds = [p for p in facts.periods if p.level is DashaLevel.MAHADASHA]
    lords = [p.lord for p in mds]
    start = VIMSHOTTARI_SEQUENCE.index(B.MOON)
    assert lords == [VIMSHOTTARI_SEQUENCE[(start + i) % 9] for i in range(len(lords))]
    assert lords[0] is B.MOON and lords[1] is B.MARS


def test_full_mahadasha_durations_are_exact_integer_microseconds() -> None:
    facts = build(0.0)  # elapsed 0: nothing truncated
    mds = [p for p in facts.periods if p.level is DashaLevel.MAHADASHA]
    for period in mds:
        assert period.duration_microseconds == exact_full_duration(YEARS[period.lord])
    assert sum(p.duration_microseconds for p in mds[:9]) == exact_full_duration(120)


def test_first_period_starts_at_birth_and_is_truncated_when_balance_is_partial() -> None:
    facts = build(10.0)  # remaining 1/4 of Ketu's 7 years
    first = facts.periods[0]
    assert first.start_utc == BIRTH
    assert first.truncated_at_birth is True
    assert first.nominal_start_utc == BIRTH - dt.timedelta(
        microseconds=exact_full_duration(7) * 3 // 4
    )
    assert first.duration_microseconds == exact_full_duration(7) // 4


def test_antardasha_durations_follow_parent_times_lord_years_over_120() -> None:
    facts = build(0.0)  # Ketu Mahadasha, full, not truncated
    md = facts.periods[0]
    kids = children_of(facts, md.period_id)
    assert [k.lord for k in kids] == list(VIMSHOTTARI_SEQUENCE)
    assert kids[0].lord is md.lord  # first Antardasha belongs to the Mahadasha lord
    for kid in kids:
        exact = Fraction(md.duration_microseconds * YEARS[kid.lord], 120)
        assert abs(kid.duration_microseconds - exact) < 1  # floor error only
    assert sum(k.duration_microseconds for k in kids) == md.duration_microseconds


def test_pratyantar_durations_follow_antardasha_times_lord_years_over_120() -> None:
    facts = build(0.0)
    ad = children_of(facts, facts.periods[0].period_id)[3]  # Moon Antardasha of Ketu
    kids = children_of(facts, ad.period_id)
    assert kids[0].lord is ad.lord
    assert [k.lord for k in kids] == [
        VIMSHOTTARI_SEQUENCE[(VIMSHOTTARI_SEQUENCE.index(ad.lord) + i) % 9] for i in range(9)
    ]
    for kid in kids:
        exact = Fraction(ad.duration_microseconds * YEARS[kid.lord], 120)
        assert abs(kid.duration_microseconds - exact) < 1
    assert sum(k.duration_microseconds for k in kids) == ad.duration_microseconds


def test_balance_mahadasha_keeps_the_tail_of_its_full_subperiods() -> None:
    """Sub-periods of the birth Mahadasha are those of the full parent, with
    the elapsed part dropped (profile DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1)."""
    facts = build(10.0)  # elapsed 3/4 of Ketu's Mahadasha
    md = facts.periods[0]
    kids = children_of(facts, md.period_id)
    assert len(kids) < 9
    assert kids[0].truncated_at_birth is True
    assert kids[0].start_utc == BIRTH
    assert kids[0].sequence_index > 0
    # Each surviving Antardasha ends where the full Mahadasha's schedule says.
    full_ketu_us = exact_full_duration(7)
    cursor = Fraction(-(full_ketu_us * 3 // 4))
    expected_ends = []
    for lord in VIMSHOTTARI_SEQUENCE:
        cursor += Fraction(full_ketu_us * YEARS[lord], 120)
        expected_ends.append(cursor)
    for kid in kids:
        expected = expected_ends[kid.sequence_index]
        assert abs((kid.end_utc - BIRTH) // ONE_US - expected) <= 1


def test_depths_1_2_3_generate_the_right_levels() -> None:
    for depth, levels in (
        (1, {DashaLevel.MAHADASHA}),
        (2, {DashaLevel.MAHADASHA, DashaLevel.ANTARDASHA}),
        (3, set(DashaLevel)),
    ):
        facts = build(123.4, config=DashaConfiguration(depth=depth))
        assert {p.level for p in facts.periods} == levels
        assert facts.depth == depth
        assert_invariants(facts)


def test_timeline_covers_the_requested_horizon() -> None:
    for horizon in (1, 30, 120, 200):
        facts = build(123.4, config=DashaConfiguration(horizon_years=horizon, depth=1))
        year = exact_full_duration(1)
        assert facts.timeline_end_utc is not None
        assert facts.timeline_end_utc >= BIRTH + dt.timedelta(microseconds=horizon * year)


# ---------------------------------------------------------------- invariants


def test_invariants_hold_for_many_random_moon_longitudes() -> None:
    rng = random.Random(20260920)
    for _ in range(60):
        facts = build(rng.uniform(0.0, 360.0))
        assert facts.status is DashaStatus.SUCCESS
        assert_invariants(facts)


def test_invariants_hold_at_every_pada_boundary_neighbourhood() -> None:
    for k in range(108):
        base = float(Fraction(k * 10, 3))
        for longitude in (math.nextafter(base, 0.0), base, math.nextafter(base, 400.0)):
            if longitude < 0:
                continue
            facts = build(longitude, config=DashaConfiguration(depth=3, horizon_years=25))
            assert_invariants(facts)


def test_invariants_hold_for_each_year_length_profile() -> None:
    for profile in (YEAR_365_2425_ID, YEAR_365_25_ID, YEAR_360_ID):
        facts = build(77.7, config=DashaConfiguration(year_length_profile_id=profile))
        assert_invariants(facts)


def test_year_length_profile_changes_durations_but_not_the_sequence() -> None:
    default = build(0.0)
    julian = build(0.0, config=DashaConfiguration(year_length_profile_id=YEAR_365_25_ID))
    assert [p.lord for p in default.periods[:9]] == [p.lord for p in julian.periods[:9]]
    assert julian.periods[0].duration_microseconds > default.periods[0].duration_microseconds
    assert julian.profile_ids.year_length_profile_id == YEAR_365_25_ID
    assert default.profile_ids.year_length_profile_id == YEAR_365_2425_ID


def test_durations_do_not_depend_on_the_calendar_leap_years() -> None:
    """No Gregorian leap-year branching: identical durations for any birth date."""
    a = build(0.0, birth=dt.datetime(2000, 2, 29, 12, 0, tzinfo=UTC))
    b = build(0.0, birth=dt.datetime(2001, 3, 1, 12, 0, tzinfo=UTC))
    assert [p.duration_microseconds for p in a.periods] == [
        p.duration_microseconds for p in b.periods
    ]


def test_local_offset_input_is_converted_to_utc_before_any_arithmetic() -> None:
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    local = dt.datetime(1990, 6, 15, 10, 0, 0, tzinfo=ist)
    utc = dt.datetime(1990, 6, 15, 4, 30, 0, tzinfo=UTC)
    assert build(50.0, birth=local).periods == build(50.0, birth=utc).periods
    assert build(50.0, birth=local).birth_utc == utc


def test_every_node_carries_ids_versions_profiles_and_provenance() -> None:
    facts = build(210.0)
    provenance_ids = {entry.entry_id for entry in facts.provenance}
    for node in facts.periods:
        assert node.period_id.startswith("vim/m")
        assert node.standards_version == "1.5.0"
        assert node.engine_version == facts.engine_version
        assert node.profile_ids == facts.profile_ids
        assert node.calculation_status is DashaStatus.SUCCESS
        assert set(node.provenance_ids) <= provenance_ids and node.provenance_ids
        assert node.path and node.path[-1] == node.lord.value


def test_facts_record_versions_profiles_convention_and_labelled_provenance() -> None:
    facts = build(210.0)
    assert facts.system_id == "vimshottari"
    assert facts.standards_version == "1.5.0"
    assert facts.boundary_convention == "half_open_start_inclusive_end_exclusive"
    assert facts.time_base == "utc"
    assert facts.profile_ids.balance_profile_id == "DASHA_STANDARD_V1_BALANCE_LONGITUDE"
    labels = {entry.evidence_label.value for entry in facts.provenance}
    assert {"source_supported", "engineering_convention", "derived_calculation"} <= labels
    balance = next(e for e in facts.provenance if e.entry_id == "prov.balance")
    assert "does not resolve" in balance.statement  # the source conflict stays visible


def test_deterministic_repeatability() -> None:
    first = build(210.0)
    second = build(210.0)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_serialization_round_trip_preserves_everything() -> None:
    from pandit_astro_engine.dashas import DashaFacts

    facts = build(210.0)
    restored = DashaFacts.model_validate_json(facts.model_dump_json())
    assert restored == facts
    assert restored.starting is not None and facts.starting is not None
    assert restored.starting.nakshatra is facts.starting.nakshatra
    assert restored.starting.pada == facts.starting.pada


def test_performance_of_a_full_nested_timeline_is_reasonable() -> None:
    import time

    started = time.perf_counter()
    for _ in range(5):
        build(123.4)
    per_call = (time.perf_counter() - started) / 5
    assert per_call < 1.0  # generous bound; typical is tens of milliseconds
