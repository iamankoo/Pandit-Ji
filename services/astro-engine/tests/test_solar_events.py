import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine.models import Location, SolarEventStatus
from pandit_astro_engine.solar_events import calculate_solar_events


@pytest.fixture(autouse=True)
def _no_ephemeris_path() -> None:
    ephemeris.configure_ephemeris_path(None)


def test_ordinary_location_has_both_events() -> None:
    # rise_trans searches forward from the given instant -- start well before
    # local sunrise (2024-06-14 20:00 UT = 2024-06-15 01:30 IST) so the rise
    # and set found both belong to the same local day, in chronological order.
    # (Starting from local daytime instead would correctly return *tomorrow's*
    # sunrise alongside *today's* sunset -- see README.md "Known limitations".)
    jd_ut, _ = ephemeris.utc_to_julian_day(2024, 6, 14, 20, 0, 0.0)
    events = calculate_solar_events(jd_ut, Location(latitude=28.6139, longitude=77.2090))
    assert events.sunrise.status == SolarEventStatus.OCCURRED
    assert events.sunset.status == SolarEventStatus.OCCURRED
    assert events.sunrise.utc_datetime < events.sunset.utc_datetime


def test_equatorial_location_has_both_events() -> None:
    jd_ut, _ = ephemeris.utc_to_julian_day(2024, 3, 20, 0, 0, 0.0)
    events = calculate_solar_events(jd_ut, Location(latitude=0.0, longitude=0.0))
    assert events.sunrise.status == SolarEventStatus.OCCURRED
    assert events.sunset.status == SolarEventStatus.OCCURRED


def test_high_latitude_polar_night_has_no_sunrise() -> None:
    # Svalbard (~78N) in December: polar night, sun never rises.
    jd_ut, _ = ephemeris.utc_to_julian_day(2024, 12, 21, 0, 0, 0.0)
    events = calculate_solar_events(jd_ut, Location(latitude=78.2232, longitude=15.6267))
    assert events.sunrise.status == SolarEventStatus.CIRCUMPOLAR_NO_EVENT
    assert events.sunrise.utc_datetime is None
    assert events.sunset.status == SolarEventStatus.CIRCUMPOLAR_NO_EVENT


def test_high_latitude_midnight_sun_has_no_sunset() -> None:
    # Svalbard (~78N) in June: midnight sun, sun never sets.
    jd_ut, _ = ephemeris.utc_to_julian_day(2024, 6, 21, 0, 0, 0.0)
    events = calculate_solar_events(jd_ut, Location(latitude=78.2232, longitude=15.6267))
    assert events.sunset.status == SolarEventStatus.CIRCUMPOLAR_NO_EVENT
    assert events.sunrise.status == SolarEventStatus.CIRCUMPOLAR_NO_EVENT


def test_determinism() -> None:
    jd_ut, _ = ephemeris.utc_to_julian_day(2024, 6, 15, 0, 0, 0.0)
    loc = Location(latitude=28.6139, longitude=77.2090)
    events1 = calculate_solar_events(jd_ut, loc)
    events2 = calculate_solar_events(jd_ut, loc)
    assert events1.model_dump() == events2.model_dump()
