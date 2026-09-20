"""`DashaCalculationService`: the ephemeris-backed facade (UTC, DST, precision)."""

from __future__ import annotations

import datetime as dt

import pytest

from pandit_astro_engine.dashas import (
    BirthTimeInput,
    BirthTimeStatus,
    DashaCalculationService,
    DashaConfiguration,
    DashaLevel,
    DashaReason,
    DashaStatus,
    DashaTimeline,
)
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationConfig,
    CelestialBody,
    DisambiguationPolicy,
    LocalDateTimeInput,
    Location,
    ZodiacType,
)

UTC = dt.timezone.utc
_DELHI = Location(latitude=28.6139, longitude=77.2090, altitude_meters=216)
_NEW_YORK = Location(latitude=40.7128, longitude=-74.0060)


def _request(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
    *,
    timezone: str = "Asia/Kolkata",
    location: Location = _DELHI,
    disambiguation: DisambiguationPolicy = DisambiguationPolicy.STRICT,
    config: CalculationConfig | None = None,
) -> AstronomicalCalculationRequest:
    return AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            timezone=timezone,
            disambiguation=disambiguation,
        ),
        location=location,
        config=config or CalculationConfig(),
        include_solar_events=False,
    )


@pytest.fixture(scope="module")
def service() -> DashaCalculationService:
    return DashaCalculationService()


def test_independence_chart_dasha_is_consistent_with_the_kundli(
    service: DashaCalculationService,
) -> None:
    """Consistency, not an external golden: the Dasha path and the Phase 5
    Kundli path must agree on the birth Moon's Nakshatra, Pada and lord."""
    request = _request(1947, 8, 15, 0, 0)
    facts = service.calculate(request)
    kundli = KundliCalculationService().calculate(request)
    moon = next(p for p in kundli.planets if p.body is CelestialBody.MOON)

    assert facts.status is DashaStatus.SUCCESS
    assert facts.starting is not None
    assert facts.starting.raw_moon_longitude == moon.longitude
    assert facts.starting.nakshatra is moon.nakshatra.nakshatra
    assert facts.starting.pada == moon.nakshatra.pada
    assert facts.starting.lord is moon.nakshatra.lord
    assert facts.periods[0].lord is moon.nakshatra.lord
    assert facts.depth == 3 and len(facts.periods) > 800


def test_utc_is_canonical_and_local_input_is_preserved(service: DashaCalculationService) -> None:
    facts = service.calculate(_request(1947, 8, 15, 0, 0))
    record = facts.birth_record
    assert record is not None
    assert record.input_local_datetime == "1947-08-15T00:00:00"
    assert record.timezone == "Asia/Kolkata"
    assert record.utc_datetime == dt.datetime(1947, 8, 14, 18, 30, tzinfo=UTC)
    assert facts.birth_utc == record.utc_datetime
    assert record.julian_day_ut > 2_400_000
    assert facts.periods[0].start_utc == record.utc_datetime
    assert facts.time_base == "utc"


def test_the_same_instant_entered_in_two_zones_gives_identical_periods(
    service: DashaCalculationService,
) -> None:
    kolkata = service.calculate(_request(1990, 6, 15, 10, 0))
    utc = service.calculate(_request(1990, 6, 15, 4, 30, timezone="UTC"))
    assert kolkata.birth_utc == utc.birth_utc
    assert kolkata.periods == utc.periods  # arithmetic is UTC-only


def test_timeline_boundaries_do_not_shift_with_local_dst_rules(
    service: DashaCalculationService,
) -> None:
    """Durations are fixed UTC spans: a DST zone gets exactly the same
    period lengths as a non-DST zone for the same instant."""
    new_york = service.calculate(
        _request(2001, 7, 4, 12, 0, timezone="America/New_York", location=_NEW_YORK)
    )
    utc = service.calculate(_request(2001, 7, 4, 16, 0, timezone="UTC", location=_NEW_YORK))
    assert new_york.birth_record is not None and new_york.birth_record.dst_active is True
    assert new_york.birth_utc == utc.birth_utc
    assert [p.duration_microseconds for p in new_york.periods] == [
        p.duration_microseconds for p in utc.periods
    ]


def test_dst_gap_is_rejected_with_a_reason_code(service: DashaCalculationService) -> None:
    facts = service.calculate(
        _request(2023, 3, 12, 2, 30, timezone="America/New_York", location=_NEW_YORK)
    )
    assert facts.status is DashaStatus.INVALID_INPUT
    assert facts.reason_code is DashaReason.NONEXISTENT_LOCAL_TIME
    assert facts.periods == ()


def test_dst_overlap_is_rejected_unless_a_policy_is_given(
    service: DashaCalculationService,
) -> None:
    strict = service.calculate(
        _request(2023, 11, 5, 1, 30, timezone="America/New_York", location=_NEW_YORK)
    )
    assert strict.status is DashaStatus.INVALID_INPUT
    assert strict.reason_code is DashaReason.AMBIGUOUS_LOCAL_TIME

    earlier = service.calculate(
        _request(
            2023,
            11,
            5,
            1,
            30,
            timezone="America/New_York",
            location=_NEW_YORK,
            disambiguation=DisambiguationPolicy.EARLIER,
        )
    )
    later = service.calculate(
        _request(
            2023,
            11,
            5,
            1,
            30,
            timezone="America/New_York",
            location=_NEW_YORK,
            disambiguation=DisambiguationPolicy.LATER,
        )
    )
    assert earlier.status is DashaStatus.SUCCESS and later.status is DashaStatus.SUCCESS
    assert earlier.birth_record is not None and later.birth_record is not None
    assert earlier.birth_record.was_ambiguous is True
    assert earlier.birth_record.disambiguation_applied == "earlier"
    assert later.birth_utc - earlier.birth_utc == dt.timedelta(hours=1)  # type: ignore[operator]


def test_invalid_timezone_and_calendar_date_are_structured_failures(
    service: DashaCalculationService,
) -> None:
    bad_zone = service.calculate(_request(2000, 1, 1, 0, 0, timezone="Mars/Olympus"))
    assert bad_zone.status is DashaStatus.INVALID_INPUT
    assert bad_zone.reason_code is DashaReason.INVALID_TIMEZONE

    bad_date = service.calculate(_request(2001, 2, 30, 0, 0))
    assert bad_date.status is DashaStatus.INVALID_INPUT
    assert bad_date.reason_code is DashaReason.INVALID_LOCAL_DATETIME


def test_a_tropical_request_is_a_configuration_error(service: DashaCalculationService) -> None:
    request = _request(
        1990, 6, 15, 10, 0, config=CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None)
    )
    facts = service.calculate(request)
    assert facts.status is DashaStatus.CONFIGURATION_ERROR
    assert facts.reason_code is DashaReason.SIDEREAL_ZODIAC_REQUIRED


def test_config_errors_from_the_dasha_configuration_flow_through(
    service: DashaCalculationService,
) -> None:
    facts = service.calculate(_request(1990, 6, 15, 10, 0), config=DashaConfiguration(depth=4))
    assert facts.status is DashaStatus.INVALID_INPUT
    assert facts.reason_code is DashaReason.UNSUPPORTED_HIERARCHY_DEPTH
    assert facts.birth_record is not None  # the time conversion is still recorded


def test_approximate_birth_time_through_the_ephemeris(service: DashaCalculationService) -> None:
    request = _request(1990, 6, 15, 10, 0)
    exact = service.calculate(request)
    assert exact.starting is not None
    approx = service.calculate(
        request,
        birth_time=BirthTimeInput(status=BirthTimeStatus.APPROXIMATE, uncertainty_seconds=60.0),
    )
    assert approx.status is DashaStatus.APPROXIMATE
    p = approx.precision
    assert p.starting_lord_stable is True
    assert p.moon_longitude_low is not None and p.moon_longitude_high is not None
    assert p.moon_longitude_low < exact.starting.raw_moon_longitude < p.moon_longitude_high
    assert approx.starting is not None and approx.starting.lord is exact.starting.lord
    # the Moon covers roughly 0.5 deg/hour: 60 s each way is about 0.0083 deg
    assert 0.001 < p.moon_longitude_high - p.moon_longitude_low < 0.05
    assert p.first_mahadasha_end_earliest_utc is not None
    assert p.first_mahadasha_end_earliest_utc < approx.periods[0].end_utc


def test_a_day_wide_birth_time_uncertainty_makes_the_starting_lord_ambiguous(
    service: DashaCalculationService,
) -> None:
    facts = service.calculate(
        _request(1990, 6, 15, 10, 0),
        birth_time=BirthTimeInput(status=BirthTimeStatus.APPROXIMATE, uncertainty_seconds=86_400.0),
    )
    assert facts.status is DashaStatus.NOT_EVALUABLE
    assert facts.reason_code is DashaReason.STARTING_LORD_AMBIGUOUS
    assert facts.periods == ()
    assert facts.precision.nakshatra_boundary_within_interval is True


def test_unknown_birth_time_through_the_service_is_not_evaluable(
    service: DashaCalculationService,
) -> None:
    facts = service.calculate(
        _request(1990, 6, 15, 10, 0),
        birth_time=BirthTimeInput(status=BirthTimeStatus.NOT_EVALUABLE),
    )
    assert facts.status is DashaStatus.NOT_EVALUABLE
    assert facts.reason_code is DashaReason.BIRTH_TIME_UNKNOWN
    assert facts.birth_record is not None


def test_unexpected_errors_become_internal_error_without_a_stack_trace(
    service: DashaCalculationService, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret internal detail with a path C:/private")

    monkeypatch.setattr(service._astronomical, "calculate", boom)
    facts = service.calculate(_request(1990, 6, 15, 10, 0))
    assert facts.status is DashaStatus.INTERNAL_ERROR
    assert facts.reason_code is DashaReason.INTERNAL_ERROR
    assert "secret" not in facts.model_dump_json()
    assert facts.detail is None


def test_service_results_are_deterministic_and_round_trip(
    service: DashaCalculationService,
) -> None:
    from pandit_astro_engine.dashas import DashaFacts

    first = service.calculate(_request(1990, 6, 15, 10, 0))
    second = service.calculate(_request(1990, 6, 15, 10, 0))
    assert first == second
    assert DashaFacts.model_validate_json(first.model_dump_json()) == first


def test_current_period_of_a_real_chart_is_found(service: DashaCalculationService) -> None:
    facts = service.calculate(_request(1990, 6, 15, 10, 0))
    timeline = DashaTimeline(facts)
    result = timeline.resolve(dt.datetime(2026, 9, 20, tzinfo=UTC))
    assert [level.level for level in result.levels] == list(DashaLevel)
    for level in result.levels:
        assert level.start_utc <= dt.datetime(2026, 9, 20, tzinfo=UTC) < level.end_utc
