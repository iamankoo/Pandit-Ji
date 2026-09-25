"""Daily Panchang: unit, edge-case, timezone, location, determinism and
regression tests (standards v1.23.0, PC-01 to PC-24)."""

from __future__ import annotations

import datetime as dt
import json

import pytest
import swisseph as swe

from pandit_astro_engine import ephemeris
from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.models import Location
from pandit_astro_engine.panchang import (
    PanchangRequest,
    PanchangService,
    SauraFrame,
    SunriseConvention,
)
from pandit_astro_engine.panchang.constants import (
    KaranaName,
    MonthName,
    Paksha,
    TithiName,
    hora_sequence,
    karana_name,
    saura_month_of_sign,
    tithi_name,
    tithi_number_in_paksha,
    tithi_paksha,
)
from pandit_astro_engine.panchang.models import (
    DailyPanchang,
    DayPartKind,
    EventStatus,
    PanchangReason,
    PanchangStatus,
)
from pandit_astro_engine.panchang.profiles import PROVENANCE, EvidenceLabel

DELHI = Location(latitude=28.61, longitude=77.21)
KOLKATA = Location(latitude=22.57, longitude=88.36)
MUMBAI = Location(latitude=19.08, longitude=72.88)
TROMSO = Location(latitude=69.65, longitude=18.96)
NEW_YORK = Location(latitude=40.71, longitude=-74.01)


@pytest.fixture(scope="module")
def service() -> PanchangService:
    return PanchangService(None)


def _day(service: PanchangService, date: dt.date, loc: Location = DELHI, tz: str = "Asia/Kolkata",
         **kw: object) -> DailyPanchang:  # fmt: skip
    return service.daily(PanchangRequest(date=date, location=loc, timezone=tz, **kw))  # type: ignore[arg-type]


# ---------------------------------------------------------------- vocab


def test_tithi_vocabulary() -> None:
    assert tithi_name(1) is TithiName.PRATIPADA and tithi_name(16) is TithiName.PRATIPADA
    assert tithi_name(15) is TithiName.PURNIMA and tithi_name(30) is TithiName.AMAVASYA
    assert tithi_name(29) is TithiName.CHATURDASHI
    assert tithi_paksha(15) is Paksha.SHUKLA and tithi_paksha(16) is Paksha.KRISHNA
    assert [tithi_number_in_paksha(i) for i in (1, 15, 16, 29, 30)] == [1, 15, 1, 14, 30]


def test_karana_cycle() -> None:
    names = [karana_name(i) for i in range(1, 61)]
    assert names[0] is KaranaName.KIMSTUGHNA
    assert names[1:8] == list(KaranaName)[:7]
    assert names[56:] == [KaranaName.VISHTI, KaranaName.SHAKUNI, KaranaName.CHATUSHPADA,
                          KaranaName.NAGA]  # fmt: skip
    movable = [n for n in names if n in list(KaranaName)[:7]]
    assert len(movable) == 56 and all(movable.count(k) == 8 for k in list(KaranaName)[:7])


def test_hora_sequence_is_chaldean() -> None:
    assert hora_sequence(B.SUN, 8) == (B.SUN, B.VENUS, B.MERCURY, B.MOON, B.SATURN, B.JUPITER,
                                       B.MARS, B.SUN)  # fmt: skip
    # the 25th hora of any day is the lord of the next weekday
    days = (B.SUN, B.MOON, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN)
    for i, lord in enumerate(days):
        assert hora_sequence(lord, 25)[24] is days[(i + 1) % 7]


def test_saura_month_names() -> None:
    assert saura_month_of_sign(0) is MonthName.VAISHAKHA  # Mesha
    assert saura_month_of_sign(11) is MonthName.CHAITRA  # Meena


def test_every_provenance_entry_has_a_reference() -> None:
    assert all(p.references for p in PROVENANCE)
    labels = {p.entry_id: p.label for p in PROVENANCE}
    assert labels["prov.rahu_kalam"] is EvidenceLabel.TRANSLATOR_NOTE


# ------------------------------------------------------------- the day


def test_day_contract(service: PanchangService) -> None:
    p = _day(service, dt.date(2026, 3, 20))
    assert p.status is PanchangStatus.SUCCESS and p.reason is None
    assert p.standards_version == "1.24.0" and p.profile_id == "PANCHANG_DRIK_CRC_1955_V2"
    assert p.sunrise_convention is SunriseConvention.CRC_1955_CENTRE_REFRACTION_30
    assert p.vara is not None and p.vara.weekday.value == "friday" and p.vara.lord is B.VENUS
    sr = p.sunrise.instant
    nsr = p.next_sunrise.instant
    assert sr is not None and nsr is not None
    for spans in (p.tithis, p.nakshatras, p.yogas, p.karanas):
        assert spans[0].current_at_sunrise and spans[0].start.julian_day_ut <= sr.julian_day_ut
        assert spans[-1].current_at_next_sunrise
        for a, b in zip(spans, spans[1:], strict=False):
            assert a.end.julian_day_ut == b.start.julian_day_ut  # contiguous
    # every tithi boundary inside the day is also a karana boundary
    karana_ends = {round(k.end.julian_day_ut, 7) for k in p.karanas}
    for t in p.tithis[:-1]:
        assert round(t.end.julian_day_ut, 7) in karana_ends
    assert {m.saura_frame for m in p.lunar_months} == set(SauraFrame)
    assert {n.item for n in p.not_implemented} >= {"choghadiya", "gowri_panchangam"}
    assert p.provenance


def test_day_parts_and_horas(service: PanchangService) -> None:
    p = _day(service, dt.date(2026, 3, 22))  # a Sunday
    assert p.vara is not None and p.vara.lord is B.SUN
    parts = {(d.kind, d.period): d for d in p.day_parts}
    assert parts[(DayPartKind.RAHU_KALAM, "day")].part == 8
    assert parts[(DayPartKind.YAMAGANDA, "day")].part == 5
    assert parts[(DayPartKind.GULIKA_KALAM, "day")].part == 7
    assert parts[(DayPartKind.GULIKA_KALAM, "night")].part == 3
    sr, ss = p.sunrise.instant, p.sunset.instant
    assert sr is not None and ss is not None
    rahu = parts[(DayPartKind.RAHU_KALAM, "day")]
    assert rahu.end.julian_day_ut == pytest.approx(ss.julian_day_ut)
    assert rahu.evidence_label is EvidenceLabel.TRANSLATOR_NOTE
    assert p.horas[0].lord is B.SUN and p.horas[0].start.julian_day_ut == sr.julian_day_ut
    assert p.horas[-1].end.julian_day_ut <= p.next_sunrise.instant.julian_day_ut  # type: ignore[union-attr]
    assert all(
        (h.end.julian_day_ut - h.start.julian_day_ut) * 24 == pytest.approx(1.0)
        for h in p.horas[:-1]
    )


def test_bhadra_is_the_vishti_karana(service: PanchangService) -> None:
    for offset in range(8):
        p = _day(service, dt.date(2026, 4, 1) + dt.timedelta(days=offset))
        vishti = [k for k in p.karanas if k.name == KaranaName.VISHTI.value]
        assert len(p.bhadra) == len(vishti)
        for b, k in zip(p.bhadra, vishti, strict=True):
            assert (b.start, b.end) == (k.start, k.end)


def test_nakshatra_panchaka_interval(service: PanchangService) -> None:
    found = False
    for offset in range(30):
        p = _day(service, dt.date(2026, 5, 1) + dt.timedelta(days=offset))
        for interval in p.nakshatra_panchaka:
            found = True
            span = (interval.end.julian_day_ut - interval.start.julian_day_ut) * 24
            if not interval.starts_before_day and not interval.ends_after_day:
                continue
            assert 90 < span < 150  # 60 degrees of the Moon: about four and a half days
    assert found


# ------------------------------------------------ month and calendar rules


def test_adhika_months_under_the_two_saura_frames(service: PanchangService) -> None:
    """2023: the Lahiri frame gives adhika Shravana, as the published modern
    almanacs do (secondary evidence); the CRC fixed frame puts the extra
    month a month later. Both are reported; neither is chosen."""
    p = _day(service, dt.date(2023, 8, 1))
    months = {m.saura_frame: m for m in p.lunar_months}
    lahiri = months[SauraFrame.LAHIRI_VARIABLE]
    crc = months[SauraFrame.CRC_FIXED_23_15]
    assert (lahiri.amanta_month, lahiri.amanta_adhika) == (MonthName.SHRAVANA, True)
    assert (crc.amanta_month, crc.amanta_adhika) == (MonthName.SHRAVANA, False)
    later = {m.saura_frame: m for m in _day(service, dt.date(2023, 8, 25)).lunar_months}
    assert later[SauraFrame.CRC_FIXED_23_15].amanta_adhika
    assert later[SauraFrame.CRC_FIXED_23_15].amanta_month is MonthName.BHADRAPADA
    assert not later[SauraFrame.LAHIRI_VARIABLE].amanta_adhika


def test_purnimanta_naming(service: PanchangService) -> None:
    # 2023-08-10: dark half of adhika Shravana (Lahiri): purnimanta keeps adhika Shravana
    p = _day(service, dt.date(2023, 8, 10))
    lahiri = next(m for m in p.lunar_months if m.saura_frame is SauraFrame.LAHIRI_VARIABLE)
    assert lahiri.paksha is Paksha.KRISHNA and lahiri.amanta_adhika
    assert (lahiri.purnimanta_month, lahiri.purnimanta_adhika) == (MonthName.SHRAVANA, True)
    # 2023-07-10: dark half of the month before the adhika month: the next natural name
    q = _day(service, dt.date(2023, 7, 10))
    lahiri = next(m for m in q.lunar_months if m.saura_frame is SauraFrame.LAHIRI_VARIABLE)
    assert lahiri.amanta_month is MonthName.ASHADHA and lahiri.paksha is Paksha.KRISHNA
    assert (lahiri.purnimanta_month, lahiri.purnimanta_adhika) == (MonthName.SHRAVANA, False)


def test_kshaya_month_is_reported(service: PanchangService) -> None:
    p = _day(service, dt.date(1983, 2, 20))
    lahiri = next(m for m in p.lunar_months if m.saura_frame is SauraFrame.LAHIRI_VARIABLE)
    assert lahiri.suppressed_month_before is MonthName.MAGHA
    assert lahiri.amanta_month is MonthName.PHALGUNA


def test_years(service: PanchangService) -> None:
    p = _day(service, dt.date(2026, 9, 25))
    for m in p.lunar_months:
        assert (m.saka_year_expired, m.vikrama_year_chaitradi_expired) == (1948, 2083)


# ------------------------------------------------- location and timezone


def test_location_changes_the_tithi_of_the_day(service: PanchangService) -> None:
    """2026-01-07: the tithi ends between Kolkata's and Mumbai's sunrise, so
    the two cities name the day differently (Sewell and Dikshit Art. 33)."""
    kol = _day(service, dt.date(2026, 1, 7), KOLKATA)
    mum = _day(service, dt.date(2026, 1, 7), MUMBAI)
    assert kol.tithi_at_sunrise is not None and mum.tithi_at_sunrise is not None
    assert (kol.tithi_at_sunrise.index, mum.tithi_at_sunrise.index) == (19, 20)
    assert (
        kol.tithis[0].end.julian_day_ut
        == pytest.approx(mum.tithis[0].start.julian_day_ut, abs=1e-6)
        or kol.tithis[0].end.julian_day_ut < mum.sunrise.instant.julian_day_ut
    )  # type: ignore[union-attr]


def test_zone_changes_only_the_labels_not_the_instants(service: PanchangService) -> None:
    """Delhi in winter: local midnight in UTC (05:30 IST) is still before
    sunrise, so both requests find the same sunrise and the same instants."""
    ist = _day(service, dt.date(2024, 1, 15), DELHI, "Asia/Kolkata")
    utc = _day(service, dt.date(2024, 1, 15), DELHI, "UTC")
    assert ist.sunrise.instant is not None and utc.sunrise.instant is not None
    assert ist.sunrise.instant.utc == utc.sunrise.instant.utc
    assert [t.end.utc for t in ist.tithis] == [t.end.utc for t in utc.tithis]
    assert ist.sunrise.instant.local.utcoffset() == dt.timedelta(hours=5, minutes=30)
    assert utc.sunrise.instant.local.utcoffset() == dt.timedelta(0)


def test_dst_zone(service: PanchangService) -> None:
    before = _day(service, dt.date(2026, 3, 7), NEW_YORK, "America/New_York")
    after = _day(service, dt.date(2026, 3, 9), NEW_YORK, "America/New_York")
    assert before.sunrise.instant is not None and after.sunrise.instant is not None
    assert before.sunrise.instant.local.utcoffset() == dt.timedelta(hours=-5)
    assert after.sunrise.instant.local.utcoffset() == dt.timedelta(hours=-4)
    # the local clock jumps an hour; the sunrise moves by about two minutes in UTC
    shift = (after.sunrise.instant.julian_day_ut - before.sunrise.instant.julian_day_ut) * 1440
    assert -6 < shift - 2 * 1440 < 0


@pytest.mark.parametrize("date", [dt.date(2026, 12, 21), dt.date(2026, 6, 21)])
def test_polar_day_and_night_are_not_evaluable(service: PanchangService, date: dt.date) -> None:
    p = _day(service, date, TROMSO, "Europe/Oslo")
    assert p.status is PanchangStatus.NOT_EVALUABLE
    assert p.reason is PanchangReason.SUNRISE_NOT_OCCURRING
    assert p.tithis == () and p.lunar_months == ()
    assert p.sunrise.status is EventStatus.CIRCUMPOLAR_NO_EVENT


def test_timezone_is_required() -> None:
    with pytest.raises(ValueError):
        PanchangRequest(date=dt.date(2026, 1, 1), location=DELHI)  # type: ignore[call-arg]


def test_unknown_timezone_is_rejected(service: PanchangService) -> None:
    with pytest.raises(Exception):  # noqa: B017 - InvalidTimezoneError
        _day(service, dt.date(2026, 1, 1), DELHI, "Mars/Olympus")


# ----------------------------------------------- determinism and state


def test_deterministic(service: PanchangService) -> None:
    a = _day(service, dt.date(2026, 7, 4)).model_dump(mode="json")
    b = _day(service, dt.date(2026, 7, 4)).model_dump(mode="json")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_panchang_leaves_the_applied_sidereal_mode_alone(service: PanchangService) -> None:
    ephemeris.set_sidereal_mode(ephemeris.Ayanamsa.LAHIRI)
    before = swe.get_ayanamsa_ex_ut(2461000.5, 0)[1]
    _day(service, dt.date(2026, 7, 4))
    assert swe.get_ayanamsa_ex_ut(2461000.5, 0)[1] == before


def test_moonrise_may_be_absent_from_a_day(service: PanchangService) -> None:
    statuses = {
        _day(service, dt.date(2026, 5, 1) + dt.timedelta(days=i)).moonrise.status for i in range(31)
    }
    assert EventStatus.NO_EVENT_IN_DAY in statuses and EventStatus.OCCURRED in statuses


def test_lahiri_is_the_default_saura_frame_and_crc_the_labelled_alternative(
    service: PanchangService,
) -> None:
    """Owner decision of 2026-09-25 (PC-15): Lahiri by default; the CRC fixed
    frame on request; the month facts of both frames always present."""
    default = _day(service, dt.date(2023, 8, 1))
    assert default.saura_frame is SauraFrame.LAHIRI_VARIABLE
    assert default.lunar_month is not None
    assert default.lunar_month.saura_frame is SauraFrame.LAHIRI_VARIABLE
    assert (default.lunar_month.amanta_month, default.lunar_month.amanta_adhika) == (
        MonthName.SHRAVANA,
        True,
    )
    crc = _day(service, dt.date(2023, 8, 1), saura_frame=SauraFrame.CRC_FIXED_23_15)
    assert crc.saura_frame is SauraFrame.CRC_FIXED_23_15
    assert crc.lunar_month is not None and not crc.lunar_month.amanta_adhika
    assert crc.lunar_months == default.lunar_months  # both frames always reported
    labels = {p.entry_id: p.label for p in PROVENANCE}
    assert labels["prov.saura_frames"] is EvidenceLabel.MODERN_TRADITION
