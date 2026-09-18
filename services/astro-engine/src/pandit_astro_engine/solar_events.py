"""Sunrise/sunset (Phase 4 prompt §19). Deterministic, via the Swiss
Ephemeris `rise_trans` adapter call. Explicitly represents a non-occurring
event (circumpolar day/night) rather than fabricating a time.
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine import ephemeris
from pandit_astro_engine.models import Location, SolarEvent, SolarEvents, SolarEventStatus


def _to_solar_event(occurred: bool, julian_day_ut: float | None) -> SolarEvent:
    if not occurred or julian_day_ut is None:
        return SolarEvent(status=SolarEventStatus.CIRCUMPOLAR_NO_EVENT)

    year, month, day, hour, minute, second = ephemeris.julian_day_to_utc_datetime_parts(
        julian_day_ut
    )
    microsecond = round((second - int(second)) * 1_000_000)
    utc_datetime = dt.datetime(
        year, month, day, hour, minute, int(second), microsecond, tzinfo=dt.timezone.utc
    )
    return SolarEvent(
        status=SolarEventStatus.OCCURRED,
        utc_datetime=utc_datetime,
        julian_day_ut=julian_day_ut,
    )


def calculate_solar_events(julian_day_ut_search_start: float, location: Location) -> SolarEvents:
    rise_occurred, rise_jd = ephemeris.rise_or_set(
        julian_day_ut_search_start,
        event="rise",
        longitude=location.longitude,
        latitude=location.latitude,
        altitude_meters=location.altitude_meters,
    )
    set_occurred, set_jd = ephemeris.rise_or_set(
        julian_day_ut_search_start,
        event="set",
        longitude=location.longitude,
        latitude=location.latitude,
        altitude_meters=location.altitude_meters,
    )
    return SolarEvents(
        sunrise=_to_solar_event(rise_occurred, rise_jd),
        sunset=_to_solar_event(set_occurred, set_jd),
    )
