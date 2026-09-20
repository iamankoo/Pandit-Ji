"""Input validation, status/reason contract and birth-time precision."""

from __future__ import annotations

import datetime as dt
import math

import pytest
from dasha_helpers import BIRTH, build

from pandit_astro_engine.dashas import (
    BirthTimeInput,
    BirthTimeStatus,
    DashaConfiguration,
    DashaReason,
    DashaRequest,
    DashaStatus,
    calculate_vimshottari,
)
from pandit_astro_engine.dashas.models import MoonUncertaintyRange
from pandit_astro_engine.dashas.profiles import (
    BALANCE_BPHS_TIME_ID,
    BALANCE_PHALADEEPIKA_ID,
    YEAR_SIDEREAL_ID,
    YEAR_SUN_RETURN_ID,
)


def _fails(facts, status: DashaStatus, reason: DashaReason) -> None:  # type: ignore[no-untyped-def]
    assert facts.status is status
    assert facts.reason_code is reason
    assert facts.periods == ()
    assert facts.starting is None


# ---------------------------------------------------------------- invalid input


def test_missing_moon_longitude_is_rejected_not_guessed() -> None:
    _fails(build(None), DashaStatus.INVALID_INPUT, DashaReason.MOON_LONGITUDE_MISSING)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_longitude_is_rejected(value: float) -> None:
    _fails(build(value), DashaStatus.INVALID_INPUT, DashaReason.NON_FINITE_LONGITUDE)


def test_naive_birth_datetime_is_rejected() -> None:
    naive = dt.datetime(1990, 6, 15, 4, 30)
    _fails(build(10.0, birth=naive), DashaStatus.INVALID_INPUT, DashaReason.NAIVE_DATETIME)


@pytest.mark.parametrize("depth", [0, 4, -1, 99])
def test_unsupported_hierarchy_depth_is_rejected(depth: int) -> None:
    facts = build(10.0, config=DashaConfiguration(depth=depth))
    _fails(facts, DashaStatus.INVALID_INPUT, DashaReason.UNSUPPORTED_HIERARCHY_DEPTH)
    assert "Sookshma" in (facts.detail or "")  # deeper levels are explicitly out of scope


@pytest.mark.parametrize("horizon", [0, -5, 241])
def test_invalid_horizon_is_rejected(horizon: int) -> None:
    _fails(
        build(10.0, config=DashaConfiguration(horizon_years=horizon)),
        DashaStatus.INVALID_INPUT,
        DashaReason.INVALID_HORIZON,
    )


def test_unknown_profile_ids_are_unsupported_not_silently_defaulted() -> None:
    _fails(
        build(10.0, config=DashaConfiguration(balance_profile_id="NOPE")),
        DashaStatus.UNSUPPORTED_PROFILE,
        DashaReason.UNKNOWN_BALANCE_PROFILE,
    )
    _fails(
        build(10.0, config=DashaConfiguration(year_length_profile_id="NOPE")),
        DashaStatus.UNSUPPORTED_PROFILE,
        DashaReason.UNKNOWN_YEAR_LENGTH_PROFILE,
    )


@pytest.mark.parametrize("profile_id", [BALANCE_BPHS_TIME_ID, BALANCE_PHALADEEPIKA_ID])
def test_documented_source_alternatives_are_unavailable_not_approximated(profile_id: str) -> None:
    facts = build(10.0, config=DashaConfiguration(balance_profile_id=profile_id))
    _fails(facts, DashaStatus.UNSUPPORTED_PROFILE, DashaReason.PROFILE_INACTIVE)
    assert profile_id in (facts.detail or "")


@pytest.mark.parametrize("profile_id", [YEAR_SIDEREAL_ID, YEAR_SUN_RETURN_ID])
def test_inactive_year_length_profiles_are_unavailable(profile_id: str) -> None:
    facts = build(10.0, config=DashaConfiguration(year_length_profile_id=profile_id))
    _fails(facts, DashaStatus.UNSUPPORTED_PROFILE, DashaReason.PROFILE_INACTIVE)


def test_failed_results_still_record_the_requested_profiles_and_versions() -> None:
    facts = build(None, config=DashaConfiguration(year_length_profile_id="YEAR_360_FIXED_DAY"))
    assert facts.profile_ids.year_length_profile_id == "YEAR_360_FIXED_DAY"
    assert facts.standards_version == "1.5.0"
    assert facts.boundary_convention == "half_open_start_inclusive_end_exclusive"
    assert facts.engine_version


def test_a_failure_without_a_reason_code_cannot_be_constructed() -> None:
    from pandit_astro_engine.dashas import DashaFacts
    from pandit_astro_engine.dashas.models import PeriodProfileIds, PrecisionAssessment

    with pytest.raises(ValueError):
        DashaFacts(
            status=DashaStatus.INVALID_INPUT,
            engine_version="x",
            profile_ids=PeriodProfileIds(
                balance_profile_id="a", year_length_profile_id="b", subperiod_profile_id="c"
            ),
            precision=PrecisionAssessment(birth_time_status=BirthTimeStatus.EXACT),
        )


# ---------------------------------------------------------------- precision


def _approx(nominal: float, low: float, high: float, seconds: float = 600.0) -> DashaRequest:
    return DashaRequest(
        moon_longitude_degrees=nominal,
        birth_utc=BIRTH,
        birth_time=BirthTimeInput(status=BirthTimeStatus.APPROXIMATE, uncertainty_seconds=seconds),
        uncertainty_range=MoonUncertaintyRange(
            moon_longitude_at_earliest=low, moon_longitude_at_latest=high
        ),
    )


def test_exact_birth_time_reports_exact_precision() -> None:
    facts = build(10.0)
    assert facts.status is DashaStatus.SUCCESS
    assert facts.precision.birth_time_status is BirthTimeStatus.EXACT
    assert facts.precision.starting_lord_stable is None


def test_unknown_birth_time_is_not_evaluable() -> None:
    facts = build(10.0, birth_time=BirthTimeInput(status=BirthTimeStatus.NOT_EVALUABLE))
    _fails(facts, DashaStatus.NOT_EVALUABLE, DashaReason.BIRTH_TIME_UNKNOWN)


def test_approximate_time_without_an_interval_is_not_evaluable_not_treated_as_exact() -> None:
    facts = build(10.0, birth_time=BirthTimeInput(status=BirthTimeStatus.APPROXIMATE))
    _fails(facts, DashaStatus.NOT_EVALUABLE, DashaReason.UNCERTAINTY_INTERVAL_MISSING)
    with_seconds_only = build(
        10.0,
        birth_time=BirthTimeInput(status=BirthTimeStatus.APPROXIMATE, uncertainty_seconds=60),
    )
    _fails(with_seconds_only, DashaStatus.NOT_EVALUABLE, DashaReason.UNCERTAINTY_INTERVAL_MISSING)


def test_approximate_with_a_stable_starting_lord_is_approximate_with_metadata() -> None:
    facts = calculate_vimshottari(_approx(6.0, 5.9, 6.1))
    assert facts.status is DashaStatus.APPROXIMATE
    assert facts.reason_code is None
    p = facts.precision
    assert p.birth_time_status is BirthTimeStatus.APPROXIMATE
    assert p.starting_lord_stable is True
    assert p.nakshatra_boundary_within_interval is False
    assert p.uncertainty_seconds == 600.0
    assert p.balance_fraction_min is not None and p.balance_fraction_max is not None
    assert p.balance_fraction_min.to_fraction() < p.balance_fraction_max.to_fraction()
    assert p.first_mahadasha_end_earliest_utc is not None
    assert p.first_mahadasha_end_latest_utc is not None
    assert p.first_mahadasha_end_earliest_utc <= p.first_mahadasha_end_latest_utc
    assert p.envelope_method == "interval_endpoints_and_nominal_instant"
    assert "birth_time_approximate" in facts.warnings
    assert all(node.calculation_status is DashaStatus.APPROXIMATE for node in facts.periods)


def test_interval_crossing_a_nakshatra_boundary_is_not_evaluable() -> None:
    facts = calculate_vimshottari(_approx(13.3, 13.2, 13.4))  # Ashwini -> Bharani at 13.333
    _fails(facts, DashaStatus.NOT_EVALUABLE, DashaReason.STARTING_LORD_AMBIGUOUS)
    assert facts.precision.starting_lord_stable is False
    assert facts.precision.nakshatra_boundary_within_interval is True


def test_interval_touching_a_boundary_exactly_counts_as_crossing() -> None:
    # The upper end sits exactly on the boundary, which belongs to the upper Nakshatra.
    facts = calculate_vimshottari(_approx(13.0, 12.9, 40.0 / 3.0))
    _fails(facts, DashaStatus.NOT_EVALUABLE, DashaReason.STARTING_LORD_AMBIGUOUS)


def test_interval_ending_just_below_a_boundary_is_stable() -> None:
    top = math.nextafter(40.0 / 3.0, 0.0)
    facts = calculate_vimshottari(_approx(13.3, 13.2, top))
    assert facts.status is DashaStatus.APPROXIMATE


def test_interval_crossing_the_360_degree_wrap_is_evaluated_continuously() -> None:
    # Revati -> Ashwini: the last Nakshatra runs into the first, and the lord changes.
    facts = calculate_vimshottari(_approx(359.99, 359.9, 0.05))
    _fails(facts, DashaStatus.NOT_EVALUABLE, DashaReason.STARTING_LORD_AMBIGUOUS)


def test_pada_boundary_crossing_within_a_stable_nakshatra_is_only_a_warning() -> None:
    facts = calculate_vimshottari(_approx(3.3, 3.2, 3.4))  # pada 1 -> 2 at 3.333 deg
    assert facts.status is DashaStatus.APPROXIMATE
    assert facts.precision.pada_boundary_within_interval is True
    assert "pada_boundary_within_birth_time_interval" in facts.warnings


def test_invalid_uncertainty_values_are_rejected() -> None:
    for seconds in (0.0, -5.0, float("nan"), float("inf")):
        facts = calculate_vimshottari(_approx(6.0, 5.9, 6.1, seconds=seconds))
        assert facts.status is DashaStatus.INVALID_INPUT
        assert facts.reason_code is DashaReason.INVALID_UNCERTAINTY


def test_inconsistent_moon_range_is_rejected() -> None:
    # nominal outside the supplied range
    facts = calculate_vimshottari(_approx(50.0, 5.9, 6.1))
    _fails(facts, DashaStatus.INVALID_INPUT, DashaReason.MOON_RANGE_INCONSISTENT)
    # implausibly wide range
    facts = calculate_vimshottari(_approx(6.0, 0.0, 200.0))
    _fails(facts, DashaStatus.INVALID_INPUT, DashaReason.MOON_RANGE_INCONSISTENT)


def test_non_finite_range_is_rejected() -> None:
    facts = calculate_vimshottari(_approx(6.0, float("nan"), 6.1))
    _fails(facts, DashaStatus.INVALID_INPUT, DashaReason.NON_FINITE_LONGITUDE)


def test_the_first_mahadasha_end_moves_with_the_birth_time_across_the_interval() -> None:
    facts = calculate_vimshottari(_approx(6.0, 5.9, 6.1, seconds=3600.0))
    p = facts.precision
    assert p.first_mahadasha_end_earliest_utc != p.first_mahadasha_end_latest_utc
    nominal_end = facts.periods[0].end_utc
    assert p.first_mahadasha_end_earliest_utc <= nominal_end <= p.first_mahadasha_end_latest_utc
