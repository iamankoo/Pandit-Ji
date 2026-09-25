"""Sunrise-dependent special points (standards v1.23.0, PC-25 to PC-29).

The BPHS translator's worked example (Santhanam, Vol I p. 44: the Sun at
Taurus 10 degrees) is reproduced by the translator-note profile; the verse
profile agrees on Chapa and Upaketu and differs on Vyatipata and Parivesha,
exactly as the registry records. Gulika and Mandi are three readings that
are never merged.
"""

from __future__ import annotations

import pytest

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.panchang.profiles import (
    EvidenceLabel,
    GulikaProfile,
    PranapadaSunReading,
    UpagrahaProfile,
)
from pandit_astro_engine.panchang.special_points import (
    MANDI_DAY_GHATIS,
    PointReason,
    PointStatus,
    SpecialPointsFacts,
    SpecialPointsRequest,
    SpecialPointsService,
    pranapada,
    upagrahas,
    varnada_sign,
)
from pandit_astro_engine.rashi import Rashi

DELHI = Location(latitude=28.61, longitude=77.21)


def _points(profile: UpagrahaProfile) -> dict[str, float]:
    return {p.name: p.longitude or 0.0 for p in upagrahas(40.0) if p.profile == profile.value}


def test_upagrahas_translator_worked_example() -> None:
    note = _points(UpagrahaProfile.BPHS_TRANSLATOR_NOTE)
    assert note["dhooma"] == pytest.approx(173 + 1 / 3)
    assert note["vyatipata"] == pytest.approx(226 + 2 / 3)
    assert note["parivesha"] == pytest.approx(46 + 2 / 3)
    assert note["indrachapa"] == pytest.approx(353 + 1 / 3)
    assert note["upaketu"] == pytest.approx(10.0)


def test_upagraha_verse_reading_differs_only_where_the_registry_says() -> None:
    verse = _points(UpagrahaProfile.BPHS_VERSE)
    note = _points(UpagrahaProfile.BPHS_TRANSLATOR_NOTE)
    assert verse["dhooma"] == pytest.approx(note["dhooma"])
    assert verse["indrachapa"] == pytest.approx(note["indrachapa"])
    assert verse["upaketu"] == pytest.approx(note["upaketu"])
    assert verse["vyatipata"] == pytest.approx(186 + 2 / 3)  # 12 signs - Dhooma
    assert verse["vyatipata"] != pytest.approx(note["vyatipata"])
    assert verse["parivesha"] != pytest.approx(note["parivesha"])
    # Upaketu plus one sign returns the Sun (v. 64)
    for sun in (0.0, 40.0, 123.4, 359.9):
        up = next(p for p in upagrahas(sun) if p.name == "upaketu")
        assert ((up.longitude or 0.0) + 30.0) % 360.0 == pytest.approx(sun % 360.0)


def test_varnada() -> None:
    assert varnada_sign(6, 7) == 0  # translator's example: Libra (7), Scorpio (5) -> Aries
    assert varnada_sign(0, 0) == 10  # 1 + 1 = 2, even: two signs back from Pisces
    assert varnada_sign(0, 2) == 8  # 1 + 3 = 4: Sagittarius
    assert varnada_sign(1, 11) == 0  # Taurus 11 + Pisces 1 = 12: Aries
    assert varnada_sign(0, 3) == 2  # Aries 1 + Cancer 9 = 10: Gemini
    assert varnada_sign(0, 1) == 0  # Aries 1 + Taurus 11 = 12: Aries


def test_varnada_is_defined_for_every_pair() -> None:
    """A difference is taken only when the two counts differ in parity, so
    it is never zero: every pair yields a sign."""
    assert all(0 <= varnada_sign(a, b) < 12 for a in range(12) for b in range(12))


def test_pranapada_modality_offsets() -> None:
    assert pranapada(10.0, 0.0) == pytest.approx(10.0)  # movable (Aries): the Sun
    assert pranapada(40.0, 0.0) == pytest.approx(280.0)  # fixed (Taurus): +240
    assert pranapada(70.0, 0.0) == pytest.approx(190.0)  # dual (Gemini): +120
    assert pranapada(10.0, 15.0) == pytest.approx(40.0)  # 15 palas = one sign


@pytest.fixture(scope="module")
def facts() -> SpecialPointsFacts:
    return SpecialPointsService(None).calculate(
        SpecialPointsRequest(
            local_datetime=LocalDateTimeInput(
                year=1990, month=5, day=17, hour=10, minute=30, timezone="Asia/Kolkata"
            ),
            location=DELHI,
        )
    )


def test_service_contract(facts: SpecialPointsFacts) -> None:
    assert facts.status is PointStatus.SUCCESS and facts.is_daytime
    assert facts.weekday_lord is B.JUPITER  # a Thursday
    names = [(p.name, p.profile) for p in facts.points]
    assert len(names) == len(set(names))
    assert {p.profile for p in facts.points if p.name in ("gulika", "mandi")} == {
        g.value for g in GulikaProfile
    }
    assert {p.profile for p in facts.points if p.name == "pranapada"} == {
        r.value for r in PranapadaSunReading
    }
    assert all(p.status is PointStatus.SUCCESS for p in facts.points)


def test_gulika_readings_are_separate_and_ordered(facts: SpecialPointsFacts) -> None:
    by = {p.profile: p for p in facts.points if p.name in ("gulika", "mandi")}
    start = by[GulikaProfile.GULIKA_PORTION_START_BPHS_TRANSLATION.value].moment
    end = by[GulikaProfile.GULIKA_PORTION_END.value].moment
    mandi = by[GulikaProfile.MANDI_PHALADEEPIKA_GHATI_TABLE.value].moment
    assert start is not None and end is not None and mandi is not None
    assert start.julian_day_ut < mandi.julian_day_ut < end.julian_day_ut
    sr, ss = facts.hindu_day_sunrise, facts.sunset
    assert sr is not None and ss is not None
    eighth = (ss.julian_day_ut - sr.julian_day_ut) / 8
    # Thursday: Saturn's part is the third
    assert start.julian_day_ut == pytest.approx(sr.julian_day_ut + 2 * eighth)
    assert mandi.julian_day_ut == pytest.approx(
        sr.julian_day_ut + MANDI_DAY_GHATIS[4] / 30 * (ss.julian_day_ut - sr.julian_day_ut)
    )
    assert by[GulikaProfile.MANDI_PHALADEEPIKA_GHATI_TABLE.value].evidence_label is (
        EvidenceLabel.SOURCE_SUPPORTED
    )


def test_special_lagna_rates(facts: SpecialPointsFacts) -> None:
    by = {p.name: p.longitude or 0.0 for p in facts.points if p.name.endswith("lagna")}
    g = facts.ghatis_since_sunrise or 0.0
    bhava, hora, ghatika = by["bhava_lagna"], by["hora_lagna"], by["ghatika_lagna"]
    assert (hora - bhava) % 360 == pytest.approx((30 * g / 2.5 - 30 * g / 5) % 360)
    assert (ghatika - bhava) % 360 == pytest.approx((30 * g - 30 * g / 5) % 360)


def test_polar_night_is_not_evaluable() -> None:
    r = SpecialPointsService(None).calculate(
        SpecialPointsRequest(
            local_datetime=LocalDateTimeInput(
                year=2026, month=12, day=21, hour=12, timezone="Europe/Oslo"
            ),
            location=Location(latitude=69.65, longitude=18.96),
        )
    )
    assert r.status is PointStatus.NOT_EVALUABLE
    assert r.reason is PointReason.SUNRISE_NOT_OCCURRING and r.points == ()


def test_before_sunrise_belongs_to_the_previous_hindu_day() -> None:
    r = SpecialPointsService(None).calculate(
        SpecialPointsRequest(
            local_datetime=LocalDateTimeInput(
                year=1990, month=5, day=17, hour=3, minute=0, timezone="Asia/Kolkata"
            ),
            location=DELHI,
        )
    )
    assert r.is_daytime is False and r.weekday_lord is B.MERCURY  # Wednesday's night
    assert r.hindu_day_sunrise is not None
    assert r.hindu_day_sunrise.local.day == 16


def test_varnada_sign_is_a_rashi(facts: SpecialPointsFacts) -> None:
    varnada = next(p for p in facts.points if p.name == "varnada_lagna")
    assert varnada.status is PointStatus.SUCCESS and varnada.sign in tuple(Rashi)
