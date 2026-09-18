import datetime as dt

import pytest

from pandit_astro_engine.errors import (
    AmbiguousLocalTimeError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)
from pandit_astro_engine.models import DisambiguationPolicy, LocalDateTimeInput
from pandit_astro_engine.timezones import resolve_local_datetime, resolve_timezone


def test_resolve_timezone_rejects_unknown_name() -> None:
    with pytest.raises(InvalidTimezoneError):
        resolve_timezone("Not/A_Real_Zone")


def test_ordinary_conversion_ist() -> None:
    local = LocalDateTimeInput(
        year=2024, month=6, day=15, hour=12, minute=0, timezone="Asia/Kolkata"
    )
    utc, resolution = resolve_local_datetime(local)
    assert utc == dt.datetime(2024, 6, 15, 6, 30, tzinfo=dt.timezone.utc)
    assert resolution.utc_offset_seconds == 5 * 3600 + 30 * 60
    assert not resolution.was_ambiguous
    assert not resolution.was_nonexistent


def test_historical_offset_differs_from_modern_kolkata() -> None:
    modern = resolve_local_datetime(
        LocalDateTimeInput(year=2024, month=1, day=1, hour=12, timezone="Asia/Kolkata")
    )[1]
    historical = resolve_local_datetime(
        LocalDateTimeInput(year=1900, month=1, day=1, hour=12, timezone="Asia/Kolkata")
    )[1]
    assert modern.utc_offset_seconds == 19800  # +05:30
    assert historical.utc_offset_seconds != modern.utc_offset_seconds
    assert historical.utc_offset_seconds == 19270  # +05:21:10, historical Madras/Kolkata mean time


def test_ambiguous_local_time_raises_by_default() -> None:
    local = LocalDateTimeInput(
        year=2024, month=11, day=3, hour=1, minute=30, timezone="America/New_York"
    )
    with pytest.raises(AmbiguousLocalTimeError):
        resolve_local_datetime(local)


def test_ambiguous_local_time_resolves_with_explicit_policy() -> None:
    earlier = LocalDateTimeInput(
        year=2024,
        month=11,
        day=3,
        hour=1,
        minute=30,
        timezone="America/New_York",
        disambiguation=DisambiguationPolicy.EARLIER,
    )
    later = LocalDateTimeInput(
        year=2024,
        month=11,
        day=3,
        hour=1,
        minute=30,
        timezone="America/New_York",
        disambiguation=DisambiguationPolicy.LATER,
    )
    utc_earlier, res_earlier = resolve_local_datetime(earlier)
    utc_later, res_later = resolve_local_datetime(later)
    assert utc_earlier < utc_later
    assert res_earlier.was_ambiguous and res_later.was_ambiguous


def test_nonexistent_local_time_raises_by_default() -> None:
    local = LocalDateTimeInput(
        year=2024, month=3, day=10, hour=2, minute=30, timezone="America/New_York"
    )
    with pytest.raises(NonexistentLocalTimeError):
        resolve_local_datetime(local)


def test_nonexistent_local_time_resolves_with_explicit_policy() -> None:
    local = LocalDateTimeInput(
        year=2024,
        month=3,
        day=10,
        hour=2,
        minute=30,
        timezone="America/New_York",
        disambiguation=DisambiguationPolicy.LATER,
    )
    utc, resolution = resolve_local_datetime(local)
    assert resolution.was_nonexistent
    assert utc.tzinfo == dt.timezone.utc


def test_dst_active_flag() -> None:
    summer = resolve_local_datetime(
        LocalDateTimeInput(year=2024, month=7, day=1, hour=12, timezone="America/New_York")
    )[1]
    winter = resolve_local_datetime(
        LocalDateTimeInput(year=2024, month=1, day=1, hour=12, timezone="America/New_York")
    )[1]
    assert summer.dst_active is True
    assert winter.dst_active is False


def test_determinism() -> None:
    local = LocalDateTimeInput(year=2024, month=6, day=15, hour=12, timezone="Asia/Kolkata")
    utc1, _ = resolve_local_datetime(local)
    utc2, _ = resolve_local_datetime(local)
    assert utc1 == utc2
