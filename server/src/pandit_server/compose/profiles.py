"""Birth-profile rules: IANA timezone validation, canonical UTC, and the engine request builders.

Nothing here infers a missing detail. A profile without a birth time has no UTC instant and no
chart; the engines are never given an invented time.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import available_timezones

from pandit_astro_engine.dashas.models import BirthTimeInput, BirthTimeStatus
from pandit_astro_engine.errors import (
    AmbiguousLocalTimeError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    DisambiguationPolicy,
    LocalDateTimeInput,
    Location,
)
from pandit_astro_engine.timezones import resolve_local_datetime

from pandit_server.db.models import BirthProfile
from pandit_server.errors import ApiError
from pandit_server.schemas import BirthProfileIn, BirthProfileOut

_IANA = available_timezones()


def validate_timezone(name: str) -> str:
    if name not in _IANA:
        raise ApiError(422, "invalid_timezone", "timezone must be an IANA identifier.")
    return name


def _local_input(
    birth_date: dt.date, birth_time: dt.time, timezone: str, policy: str
) -> LocalDateTimeInput:
    return LocalDateTimeInput(
        year=birth_date.year,
        month=birth_date.month,
        day=birth_date.day,
        hour=birth_time.hour,
        minute=birth_time.minute,
        second=float(birth_time.second),
        timezone=timezone,
        disambiguation=DisambiguationPolicy(policy),
    )


def resolve_birth_utc(data: BirthProfileIn) -> dt.datetime | None:
    """The canonical UTC instant, or ``None`` when there is no birth time. A DST-ambiguous or
    nonexistent local time is refused under the default ``strict`` policy, never guessed."""
    validate_timezone(data.timezone)
    if data.birth_time is None:
        return None
    try:
        utc, _ = resolve_local_datetime(
            _local_input(data.birth_date, data.birth_time, data.timezone, data.disambiguation)
        )
    except AmbiguousLocalTimeError as exc:
        raise ApiError(
            422,
            "ambiguous_local_time",
            "That local time occurs twice (DST); pick disambiguation 'earlier' or 'later'.",
        ) from exc
    except NonexistentLocalTimeError as exc:
        raise ApiError(
            422, "nonexistent_local_time", "That local time does not exist (DST change)."
        ) from exc
    except InvalidTimezoneError as exc:
        raise ApiError(422, "invalid_timezone", "timezone must be an IANA identifier.") from exc
    return utc


def profile_to_out(profile: BirthProfile) -> BirthProfileOut:
    return BirthProfileOut(
        id=profile.id,
        label=profile.label,
        birth_date=profile.birth_date,
        birth_time=profile.birth_time,
        time_precision=profile.time_precision,
        time_uncertainty_seconds=profile.time_uncertainty_seconds,
        timezone=profile.timezone,
        disambiguation=profile.disambiguation,
        latitude=profile.latitude,
        longitude=profile.longitude,
        altitude_m=profile.altitude_m,
        place_label=profile.place_label,
        birth_utc=profile.birth_utc,
        version=profile.row_version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def require_birth_time(profile: BirthProfile) -> None:
    if profile.birth_time is None:
        raise ApiError(
            422,
            "birth_time_required",
            "This calculation needs the birth time; it is never assumed.",
        )


def to_astro_request(profile: BirthProfile) -> AstronomicalCalculationRequest:
    require_birth_time(profile)
    assert profile.birth_time is not None
    return AstronomicalCalculationRequest(
        local_datetime=_local_input(
            profile.birth_date, profile.birth_time, profile.timezone, profile.disambiguation
        ),
        location=Location(
            latitude=profile.latitude,
            longitude=profile.longitude,
            altitude_meters=profile.altitude_m,
        ),
    )


def to_birth_time_input(profile: BirthProfile) -> BirthTimeInput:
    if profile.time_precision in ("exact", "minute"):
        return BirthTimeInput(status=BirthTimeStatus.EXACT)
    if profile.time_precision == "approximate":
        return BirthTimeInput(
            status=BirthTimeStatus.APPROXIMATE,
            uncertainty_seconds=profile.time_uncertainty_seconds,
        )
    return BirthTimeInput(status=BirthTimeStatus.NOT_EVALUABLE)


def profile_versions(profile: BirthProfile) -> dict[str, Any]:
    """What a cache or stored chart depends on from the profile (its content, via its version)."""
    return {"profile_id": str(profile.id), "row_version": profile.row_version}
