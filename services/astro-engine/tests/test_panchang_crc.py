"""Golden test: the daily Panchang against the printed calendar of the
Calendar Reform Committee (1955), Saka 1876 Caitra and Vaisakha
(22 March - 21 May 1954), transcribed from page images
(`fixtures/crc_1955_calendar_saka_1876.json`; standards v1.23.0 PC-31).

The printed times are rounded to the minute; the engine is required to agree
within one minute for sunrise, sunset, every tithi and nakshatra ending
moment and every printed phenomenon.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from pandit_astro_engine.models import Location
from pandit_astro_engine.panchang import (
    PanchangRequest,
    PanchangService,
    SauraFrame,
    SunriseConvention,
    astro,
)
from pandit_astro_engine.panchang.astro import Sky
from pandit_astro_engine.panchang.models import DailyPanchang, ElementSpan, Instant
from pandit_astro_engine.panchang.service import jd_of

DOC = json.loads(
    (Path(__file__).parent / "fixtures" / "crc_1955_calendar_saka_1876.json").read_text(
        encoding="utf-8"
    )
)
STATION = Location(latitude=DOC["station"]["latitude"], longitude=DOC["station"]["longitude"])
TZ = ZoneInfo(DOC["station"]["timezone"])
TOL_MIN = 1.0
SLIPS = {(s["date"], s["element"], s["index"]) for s in DOC["printed_slips"]}
SLIP_TOL_MIN = 2.5


def _minutes(text: str) -> int:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def _after_midnight(instant: Instant, date: dt.date) -> float:
    base = dt.datetime.combine(date, dt.time(0), tzinfo=TZ)
    return (instant.local - base).total_seconds() / 60.0


def _label(index: int) -> str:
    if index <= 15:
        return f"S{index}"
    return "K30" if index == 30 else f"K{index - 15}"


def _printed(spans: tuple[ElementSpan, ...]) -> list[ElementSpan]:
    """The calendar prints the element current at sunrise and every element
    that ends before the next sunrise."""
    return [s for s in spans if s.current_at_sunrise or not s.current_at_next_sunrise]


@pytest.fixture(scope="module")
def days() -> dict[str, DailyPanchang]:
    service = PanchangService(None)
    return {
        row["date"]: service.daily(
            PanchangRequest(
                date=dt.date.fromisoformat(row["date"]),
                location=STATION,
                timezone=DOC["station"]["timezone"],
            )
        )
        for row in DOC["days"]
    }


@pytest.mark.parametrize("row", DOC["days"], ids=[r["date"] for r in DOC["days"]])
def test_day_matches_printed_calendar(row: dict, days: dict[str, DailyPanchang]) -> None:  # type: ignore[type-arg]
    date = dt.date.fromisoformat(row["date"])
    p = days[row["date"]]
    assert p.sunrise_convention is SunriseConvention.CRC_1955_CENTRE_REFRACTION_30
    assert p.sunrise.instant is not None and p.sunset.instant is not None
    assert abs(_after_midnight(p.sunrise.instant, date) - _minutes(row["sunrise"])) <= TOL_MIN
    assert abs(_after_midnight(p.sunset.instant, date) - _minutes(row["sunset"])) <= TOL_MIN

    tithis = _printed(p.tithis)
    assert [_label(t.index) for t in tithis] == [t[0] for t in row["tithis"]]
    for got, (_, end) in zip(tithis, row["tithis"], strict=True):
        if end is None:
            assert got.current_at_next_sunrise
        else:
            assert abs(_after_midnight(got.end, date) - _minutes(end)) <= TOL_MIN

    naks = _printed(p.nakshatras)
    assert [n.index for n in naks] == [n[0] for n in row["nakshatras"]]
    for got, (_, end) in zip(naks, row["nakshatras"], strict=True):
        if end is None:
            assert got.current_at_next_sunrise
        else:
            tol = SLIP_TOL_MIN if (row["date"], "nakshatra", got.index) in SLIPS else TOL_MIN
            assert abs(_after_midnight(got.end, date) - _minutes(end)) <= tol


def _jd(date: str, time: str) -> float:
    base = dt.datetime.combine(dt.date.fromisoformat(date), dt.time(0), tzinfo=TZ)
    return jd_of(base + dt.timedelta(minutes=_minutes(time)))


@pytest.mark.parametrize(
    "event", DOC["phenomena"], ids=[f"{e['event']}-{e['date']}" for e in DOC["phenomena"]]
)
def test_printed_phenomena(event: dict) -> None:  # type: ignore[type-arg]
    sky = Sky(allow_moshier_fallback=True)
    printed = _jd(event["date"], event["time"])
    start = printed - 0.5
    kind = event["event"]
    if kind in ("new_moon", "full_moon"):
        target = 0.0 if kind == "new_moon" else 180.0

        def fn(j: float) -> float:
            return (sky.elongation(j) - target) % 360.0

        got, _ = astro.next_crossing(fn, astro.ELONGATION, 360.0, start)
    elif kind == "enters_nakshatra":
        span = 360.0 / 27.0

        def fn(j: float) -> float:
            return (sky.sun_sidereal(j) - (event["nakshatra"] - 1) * span) % 360.0

        got, _ = astro.next_crossing(fn, astro.SUN, 360.0, start)
    elif kind == "saura_sign_entry":

        def fn(j: float) -> float:
            return (sky.sun(j) - 23.25 - event["sign"] * 30.0) % 360.0

        got, _ = astro.next_crossing(fn, astro.SUN, 360.0, start)
    elif kind == "tropical_sign_entry":

        def fn(j: float) -> float:
            return (sky.sun(j) - event["sign"] * 30.0) % 360.0

        got, _ = astro.next_crossing(fn, astro.SUN, 360.0, start)
    else:  # tropical_longitude_sum: the printed Vyatipata / Vaidhrti phenomena

        def fn(j: float) -> float:
            return (sky.sun(j) + sky.moon(j) - event["sum"]) % 360.0

        got, _ = astro.next_crossing(fn, astro.YOGA, 360.0, start)
    assert abs(got - printed) * 1440.0 <= TOL_MIN + 0.5  # printed minute + truncation


def test_lunar_month_names(days: dict[str, DailyPanchang]) -> None:
    for block in DOC["lunar_months"]:
        start = dt.date.fromisoformat(block["from"])
        end = dt.date.fromisoformat(block["to"])
        date = start
        while date <= end:
            p = days[date.isoformat()]
            for month in p.lunar_months:
                assert month.amanta_month.value == block["lunar_amanta"], (date, month.saura_frame)
                assert not month.amanta_adhika
            date += dt.timedelta(days=1)


def test_years_and_kshaya_tithi(days: dict[str, DailyPanchang]) -> None:
    before = days["1954-03-31"]
    after = days["1954-04-10"]
    for m in before.lunar_months:
        assert (m.saka_year_expired, m.vikrama_year_chaitradi_expired) == (1875, 2010)
    for m in after.lunar_months:
        assert (m.saka_year_expired, m.vikrama_year_chaitradi_expired) == (1876, 2011)
    k12 = [t for t in before.tithis if t.index == 27]
    assert len(k12) == 1 and k12[0].kshaya  # printed "(12 28 31)": no sunrise in K12
    repeated = days["1954-03-24"].tithis[0]
    assert repeated.index == 20 and repeated.current_at_next_sunrise  # K5 over two sunrises


def test_both_saura_frames_are_reported(days: dict[str, DailyPanchang]) -> None:
    frames = {m.saura_frame for m in days["1954-04-10"].lunar_months}
    assert frames == set(SauraFrame)


def test_upper_limb_convention_is_a_distinct_profile() -> None:
    service = PanchangService(None)
    crc = service.daily(
        PanchangRequest(date=dt.date(1954, 3, 22), location=STATION, timezone="Asia/Kolkata")
    )
    limb = service.daily(
        PanchangRequest(
            date=dt.date(1954, 3, 22),
            location=STATION,
            timezone="Asia/Kolkata",
            sunrise_convention=SunriseConvention.UPPER_LIMB_STANDARD_REFRACTION,
        )
    )
    assert limb.sunrise_convention is SunriseConvention.UPPER_LIMB_STANDARD_REFRACTION
    assert crc.sunrise.instant is not None and limb.sunrise.instant is not None
    delta = (crc.sunrise.instant.julian_day_ut - limb.sunrise.instant.julian_day_ut) * 1440.0
    assert 0.3 < delta < 3.0  # the upper limb rises first
