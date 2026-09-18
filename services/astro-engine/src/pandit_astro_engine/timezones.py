"""Deterministic, testable timezone conversion.

IANA timezone identifiers via the stdlib `zoneinfo` module (backed by the
`tzdata` package for portability, per pyproject.toml) -- this gives correct
historical offset/DST rules "for free" (docs/ASTROLOGY_STANDARDS.md "Time
standards": historical timezone changes, DST). Never uses hard-coded IST
(or any other) offset logic; arbitrary valid IANA zones are supported.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pandit_astro_engine.errors import (
    AmbiguousLocalTimeError,
    InvalidTimezoneError,
)
from pandit_astro_engine.models import DisambiguationPolicy, LocalDateTimeInput, TimeResolution


def resolve_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise InvalidTimezoneError(timezone_name) from exc


def _split_seconds(second: float) -> tuple[int, int]:
    whole = int(second)
    microsecond = round((second - whole) * 1_000_000)
    return whole, microsecond


def resolve_local_datetime(local_input: LocalDateTimeInput) -> tuple[dt.datetime, TimeResolution]:
    """Resolve a `LocalDateTimeInput` to an aware UTC `datetime` plus a full
    `TimeResolution` record. Raises `NonexistentLocalTimeError` /
    `AmbiguousLocalTimeError` if the local time is a DST edge case and
    `disambiguation` is `STRICT` (the default) -- never silently guesses.
    """
    tz = resolve_timezone(local_input.timezone)
    second_whole, microsecond = _split_seconds(local_input.second)

    naive = dt.datetime(
        local_input.year,
        local_input.month,
        local_input.day,
        local_input.hour,
        local_input.minute,
        second_whole,
        microsecond,
    )

    aware_fold0 = naive.replace(tzinfo=tz, fold=0)
    aware_fold1 = naive.replace(tzinfo=tz, fold=1)
    utc_fold0 = aware_fold0.astimezone(dt.timezone.utc)
    utc_fold1 = aware_fold1.astimezone(dt.timezone.utc)

    was_ambiguous = utc_fold0 != utc_fold1

    # Nonexistent-time detection (PEP 495): round-trip fold=0's UTC instant
    # back through the same zone and compare to the original naive input.
    round_trip_local = utc_fold0.astimezone(tz).replace(tzinfo=None)
    was_nonexistent = round_trip_local != naive

    policy = local_input.disambiguation
    if was_nonexistent and policy == DisambiguationPolicy.STRICT:
        from pandit_astro_engine.errors import NonexistentLocalTimeError

        raise NonexistentLocalTimeError(naive.isoformat(), local_input.timezone)
    if was_ambiguous and policy == DisambiguationPolicy.STRICT:
        raise AmbiguousLocalTimeError(
            naive.isoformat(),
            local_input.timezone,
            earlier_utc=utc_fold0.isoformat(),
            later_utc=utc_fold1.isoformat(),
        )

    use_fold1 = policy == DisambiguationPolicy.LATER
    chosen_aware = aware_fold1 if use_fold1 else aware_fold0
    chosen_utc = utc_fold1 if use_fold1 else utc_fold0

    utc_offset = chosen_aware.utcoffset()
    dst_offset = chosen_aware.dst()

    resolution = TimeResolution(
        input_local_datetime=naive.isoformat(),
        timezone=local_input.timezone,
        utc_offset_seconds=int(utc_offset.total_seconds()) if utc_offset else 0,
        utc_datetime=chosen_utc,
        julian_day_ut=0.0,  # filled in by the caller once it has swe.utc_to_jd available
        julian_day_et=0.0,
        dst_active=bool(dst_offset and dst_offset.total_seconds() != 0),
        was_ambiguous=was_ambiguous,
        was_nonexistent=was_nonexistent,
        disambiguation_applied=policy if (was_ambiguous or was_nonexistent) else None,
    )
    return chosen_utc, resolution
