"""Modern Shadbala profile SHADBALA_RAMAN_GRAHA_BHAVA_BALAS (standards
v1.21.0, SR-01 to SR-24).

Component formulas are checked on B. V. Raman's own printed inputs for his
worked Standard Horoscope against his printed results (fixture
`raman_standard_horoscope.json`, page-image transcription); where his printed
figure disagrees with his own stated rule, the test asserts the rule and the
fixture records the slip. The service is checked for its contract, profile
separation from the BPHS profile, NOT_EVALUABLE paths and determinism.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.rashi import rashi_from_longitude
from pandit_astro_engine.shadbala import components as calc
from pandit_astro_engine.shadbala import raman as rm
from pandit_astro_engine.shadbala.models import (
    ComponentStatus,
    RamanShadbalaRequest,
    ShadbalaReason,
    ShadbalaRequest,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala.profiles import (
    PROFILE_ID,
    RAMAN_COMPONENTS,
    RAMAN_PROFILE_ID,
    Component,
)
from pandit_astro_engine.shadbala.raman import DrekkanaReading, MoonPakshaReading
from pandit_astro_engine.shadbala.raman_service import RamanShadbalaService, _saptavarga
from pandit_astro_engine.shadbala.service import ShadbalaService

DOC = json.loads(
    (Path(__file__).parent / "fixtures" / "raman_standard_horoscope.json").read_text(
        encoding="utf-8"
    )
)
INP, PR = DOC["inputs"], DOC["printed"]
SEVEN = (B.SUN, B.MOON, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN)


def _dm(pair: list[int]) -> float:
    return pair[0] + pair[1] / 60.0


LON = {B(k): _dm(v) for k, v in INP["nirayana_longitudes_dm"].items()}
SIGNS = {b: rashi_from_longitude(v) for b, v in LON.items()}
AYANAMSA = _dm(INP["ayanamsa_dm"])


# --------------------------------------------------------------------------
# Sthana
# --------------------------------------------------------------------------


@pytest.mark.parametrize("body", SEVEN)
def test_uchcha(body: B) -> None:
    # Raman prints one decimal, sometimes truncated (printed_slips.uchcha_rounding).
    assert calc.uchcha_bala(body, LON[body]) == pytest.approx(PR["uchcha"][body.value], abs=0.08)


def test_saptavarga_relations_47_of_49_and_totals() -> None:
    matches = 0
    for body in SEVEN:
        total, placements = _saptavarga(body, LON[body], SIGNS)
        got = [p.category for p in placements]
        expected = PR["saptavarga_relations_p18"][body.value]
        matches += sum(g == e for g, e in zip(got, expected, strict=True))
        if body not in (B.MARS, B.SATURN):
            assert total == pytest.approx(PR["saptavargaja_totals"][body.value])
    assert matches == 47
    # The two recorded differences follow the locked Phase 5 varga schemes.
    mars = [p.category for p in _saptavarga(B.MARS, LON[B.MARS], SIGNS)[1]]
    saturn = [p.category for p in _saptavarga(B.SATURN, LON[B.SATURN], SIGNS)[1]]
    assert mars[6] == "equal" and saturn[3] == "great_friend"


def test_raman_saptavargaja_values() -> None:
    assert rm.RAMAN_SAPTAVARGAJA == {
        "moolatrikona": 45.0,
        "own": 30.0,
        "great_friend": 22.5,
        "friend": 15.0,
        "equal": 7.5,
        "enemy": 3.75,
        "great_enemy": 1.875,
    }


def test_moolatrikona_only_in_the_rasi() -> None:
    # Sun at Leo 10 deg: D1 Moolatrikona (45); a Leo navamsa counts as own (30).
    total, placements = _saptavarga(B.SUN, 130.0, {**SIGNS, B.SUN: rashi_from_longitude(130.0)})
    assert placements[0].category == "moolatrikona" and placements[0].virupas == 45.0
    assert all(p.category != "moolatrikona" for p in placements[1:])


@pytest.mark.parametrize("body", SEVEN)
def test_ojayugma_and_kendra(body: B) -> None:
    from pandit_astro_engine.vargas import calculate_varga_sign

    d9 = calculate_varga_sign(9, LON[body])
    assert calc.ojayugma_bala(body, SIGNS[body], d9) == PR["ojayugma"][body.value]
    lagna = rashi_from_longitude(_dm(INP["ascendant_dm"]))
    assert calc.kendradi_bala(lagna, SIGNS[body]) == PR["kendra"][body.value]


def test_drekkana_readings() -> None:
    gender = {B.SUN: "male", B.MOON: "female", B.MARS: "male", B.MERCURY: "neuter",
              B.JUPITER: "male", B.VENUS: "female", B.SATURN: "neuter"}  # fmt: skip
    for body in SEVEN:
        value = rm.raman_drekkana_bala(
            gender[body], LON[body] % 30.0, DrekkanaReading.WORKED_EXAMPLE_12
        )
        assert value == PR["drekkana_worked_example"][body.value]
    # The Art. 36 text reading gives the Moon (female, 2nd decanate) nothing.
    assert rm.raman_drekkana_bala("female", 15.0, DrekkanaReading.TEXT_ARTICLE_36) == 0.0
    assert rm.raman_drekkana_bala("female", 25.0, DrekkanaReading.TEXT_ARTICLE_36) == 15.0
    assert rm.raman_drekkana_bala("neuter", 15.0, DrekkanaReading.TEXT_ARTICLE_36) == 15.0
    assert rm.raman_drekkana_bala("male", 5.0, DrekkanaReading.TEXT_ARTICLE_36) == 15.0


@pytest.mark.parametrize("body", SEVEN)
def test_dig(body: B) -> None:
    from pandit_astro_engine.shadbala.constants import DIG_BALA_ZERO_POINT, Angle

    asc, mc = _dm(INP["ascendant_dm"]), _dm(INP["midheaven_dm"])
    angles = {Angle.ASCENDANT: asc, Angle.DESCENDANT: (asc + 180) % 360, Angle.MERIDIAN: mc,
              Angle.NADIR: (mc + 180) % 360}  # fmt: skip
    got = calc.dig_bala(LON[body], angles[DIG_BALA_ZERO_POINT[body]])
    assert got == pytest.approx(PR["dig"][body.value], abs=0.01)


# --------------------------------------------------------------------------
# Kala
# --------------------------------------------------------------------------


@pytest.mark.parametrize("body", SEVEN)
def test_nathonnatha(body: B) -> None:
    got = calc.nathonnatha_bala(body, INP["unnata_ghatis"])
    assert got == pytest.approx(PR["nathonnatha"][body.value], abs=0.01)


def test_paksha_with_the_moon_doubled() -> None:
    natures = {b: calc.natural_nature(b, LON, SIGNS) for b in SEVEN}
    for body in SEVEN:
        if body is B.MOON:
            e = calc.elongation(LON[B.MOON], LON[B.SUN])
            for reading in MoonPakshaReading:
                benefic = rm.raman_moon_is_benefic(e, reading)
                value = 2 * calc.paksha_bala(
                    "benefic" if benefic else "malefic", LON[B.MOON], LON[B.SUN]
                )
                assert value == pytest.approx(PR["paksha"]["moon"], abs=0.02)
            continue
        got = calc.paksha_bala(natures[body] or "", LON[B.MOON], LON[B.SUN])
        assert got == pytest.approx(PR["paksha"][body.value], abs=0.01)


def test_moon_readings_differ_where_expected() -> None:
    w, e8 = MoonPakshaReading.WAXING_HALF, MoonPakshaReading.EIGHTH_DAY_WINDOW
    assert rm.raman_moon_is_benefic(50.0, w) and not rm.raman_moon_is_benefic(50.0, e8)
    assert not rm.raman_moon_is_benefic(200.0, w) and rm.raman_moon_is_benefic(200.0, e8)
    assert rm.raman_moon_is_benefic(120.0, w) and rm.raman_moon_is_benefic(120.0, e8)
    assert not rm.raman_moon_is_benefic(300.0, w) and not rm.raman_moon_is_benefic(300.0, e8)
    assert rm.raman_moon_is_benefic(84.0, e8) and not rm.raman_moon_is_benefic(276.0, e8)


def test_tribhaga() -> None:
    holders = {b for b in SEVEN if calc.tribhaga_bala(b, True, INP["day_third"]) > 0}
    assert holders == {B(k) for k in PR["tribhaga"]}


def test_ahargana_lords_standard_horoscope() -> None:
    a = rm.condensed_ahargana(dt.date.fromisoformat(INP["birth_date"]))
    assert a == PR["condensed_ahargana"]
    assert rm.abda_lord(a).value == PR["abda_lord"]
    assert rm.masa_lord(a).value == PR["masa_lord"]
    assert rm.ahargana_weekday(a) == INP["birth_weekday_sunday_zero"]
    assert (
        rm.hora_lord(INP["birth_weekday_sunday_zero"], INP["hours_since_sunrise"]).value
        == (PR["hora_lord"])
    )


def test_ahargana_agrees_with_the_santhanam_bphs_note_example() -> None:
    # BPHS Ch. 27 note (Santhanam, p. 271): 1 June 1984 -> year lord Jupiter (Thursday),
    # month lord Venus (Friday), a Friday. Independent of Raman's epoch.
    a = rm.condensed_ahargana(dt.date(1984, 6, 1))
    assert rm.abda_lord(a) is B.JUPITER
    assert rm.masa_lord(a) is B.VENUS
    assert rm.ahargana_weekday(a) == 5


def test_ahargana_weekday_matches_the_calendar() -> None:
    day = dt.date(1850, 1, 1)
    for k in range(0, 100_000, 997):
        d = day + dt.timedelta(days=k)
        assert rm.ahargana_weekday(rm.condensed_ahargana(d)) == (d.weekday() + 1) % 7


def test_hora_sequence() -> None:
    assert [rm.hora_lord(0, h).value for h in (0.5, 1.5, 2.5, 7.5)] == [
        "sun",
        "venus",
        "mercury",
        "sun",
    ]
    assert rm.hora_lord(1, 0.0) is B.MOON
    with pytest.raises(ValueError):
        rm.hora_lord(0, 24.0)


@pytest.mark.parametrize("body", SEVEN)
def test_kranti_and_ayana(body: B) -> None:
    kranti = rm.raman_kranti(LON[body] + AYANAMSA)
    assert kranti == pytest.approx(PR["krantis_deg"][body.value], abs=0.02)
    ayana = rm.raman_ayana_bala(body, kranti)
    if body in (B.MARS, B.VENUS):  # printed slips, see the fixture
        assert ayana == pytest.approx(PR["ayana"][body.value] + 0.5, abs=0.03)
    else:
        assert ayana == pytest.approx(PR["ayana"][body.value], abs=0.03)


def test_kranti_table_limits() -> None:
    assert rm.raman_kranti(0.0) == 0.0
    assert rm.raman_kranti(90.0) == pytest.approx(24.0)
    assert rm.raman_kranti(270.0) == pytest.approx(-24.0)
    assert rm.raman_kranti(180.0) == pytest.approx(0.0)
    assert rm.raman_kranti(15.0) == pytest.approx(362 / 60)


# --------------------------------------------------------------------------
# Cheshta, Naisargika, Drik
# --------------------------------------------------------------------------


def test_cheshta_interval_from_the_epoch() -> None:
    lmt_hours = 14.0 - (5 + 10 / 60 + 20 / 3600)  # 2 p.m. LMT at 5h 10m 20s E, in UT
    jd = 2421882.5 + lmt_hours / 24.0  # 16 October 1918, 0h UT = JD 2421882.5
    assert rm.cheshta_interval(jd) == pytest.approx(INP["cheshta_total_interval_days"], abs=0.002)


@pytest.mark.parametrize("body", [B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN])
def test_cheshta(body: B) -> None:
    mean, sighrocca = rm.mean_and_sighrocca(
        body, INP["cheshta_total_interval_days"], INP["years_since_1900"]
    )
    if body in (B.MARS, B.JUPITER, B.SATURN):
        # Raman's Jupiter sum uses a Table VI hundreds entry (66.58) inconsistent with the
        # table's own rate by 0.1 degree; the tolerance covers it.
        assert mean == pytest.approx(PR["mean_longitudes"][body.value], abs=0.08)
        assert sighrocca == pytest.approx(PR["mean_longitudes"]["sun"], abs=0.01)
    else:
        assert mean == pytest.approx(PR["mean_longitudes"]["sun"], abs=0.01)
        assert sighrocca == pytest.approx(PR["sighroccas"][body.value], abs=0.02)
    kendra = rm.reduced_cheshta_kendra(sighrocca, mean, LON[body])
    assert kendra == pytest.approx(PR["reduced_cheshta_kendra"][body.value], abs=0.05)
    assert kendra / 3 == pytest.approx(PR["cheshta"][body.value], abs=0.02)


def test_cheshta_only_for_mars_to_saturn() -> None:
    with pytest.raises(ValueError):
        rm.mean_and_sighrocca(B.SUN, 100.0, 0)


def test_naisargika() -> None:
    assert [round(calc.naisargika_bala(b), 2) for b in SEVEN] == [
        60.0, 51.43, 17.14, 25.71, 34.29, 42.86, 8.57
    ]  # fmt: skip


def test_drishti_values_and_visesha() -> None:
    assert rm.drishti_value(29.99) == 0.0 and rm.drishti_value(300.0) == 0.0
    assert rm.drishti_value(60.0) == 15.0 and rm.drishti_value(90.0) == 45.0
    assert rm.drishti_value(150.0) == 0.0 and rm.drishti_value(180.0) == 60.0
    assert rm.visesha_value(B.SATURN, 75.0) == 45.0 and rm.visesha_value(B.SATURN, 100.0) == 0
    assert rm.visesha_value(B.JUPITER, 250.0) == 30.0
    assert rm.visesha_value(B.MARS, 215.0) == 15.0
    assert rm.visesha_value(B.VENUS, 75.0) == 0.0


def test_dristi_pinda_and_drik() -> None:
    natures = {b: calc.natural_nature(b, LON, SIGNS) for b in SEVEN}
    for body in SEVEN:
        pinda, _cells = rm.dristi_pinda(body, LON, natures)
        assert pinda is not None
        # Four printed cells carry arithmetic slips of up to 0.6 (see the fixture).
        assert pinda == pytest.approx(PR["dristi_pinda"][body.value], abs=0.6)
        assert pinda / 4 == pytest.approx(PR["drik"][body.value], abs=0.15)


def test_dristi_pinda_not_evaluable_when_a_nature_is_unknown() -> None:
    natures = {b: calc.natural_nature(b, LON, SIGNS) for b in SEVEN}
    natures[B.MOON] = None
    pinda, _ = rm.dristi_pinda(B.SUN, LON, natures)  # the Moon aspects the Sun
    assert pinda is None


def test_printed_totals_are_the_sum_of_printed_components() -> None:
    # Internal check of the book's own table (p. 81) with the rule that Drik is signed and
    # the Sun and Moon have no Cheshta Bala.
    sthana = {"sun": 147.975, "moon": 141.65, "mars": 194.7, "mercury": 294.8,
              "jupiter": 157.45, "venus": 157.925, "saturn": 162.4}  # fmt: skip
    dig = PR["dig"]
    kala = {"sun": 104.49, "moon": 202.75, "mars": 28.39, "mercury": 219.92,
            "jupiter": 211.93, "venus": 116.81, "saturn": 115.69}  # fmt: skip
    cheshta = {"sun": 0.0, "moon": 0.0, **PR["cheshta"]}
    nais = {"sun": 60.0, "moon": 51.43, "mars": 17.14, "mercury": 25.7, "jupiter": 34.28,
            "venus": 42.85, "saturn": 8.57}  # fmt: skip
    for k, total in PR["shadbala_virupas"].items():
        s = sthana[k] + dig[k] + kala[k] + cheshta[k] + nais[k] + PR["drik"][k]
        slip = 0.30 if k == "mars" else 0.0  # printed_slips.total_mars
        assert s == pytest.approx(total + slip, abs=0.02), k


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

STANDARD = LocalDateTimeInput(year=1918, month=10, day=16, hour=8, minute=49, second=40,
                              timezone="UTC")  # fmt: skip
BANGALORE = Location(latitude=13.0, longitude=77.5833)


def _req(**kw: object) -> RamanShadbalaRequest:
    base: dict[str, object] = dict(
        local_datetime=STANDARD,
        location=BANGALORE,
        time_precision=ShadbalaTimePrecision.EXACT,
        drekkana_reading=DrekkanaReading.WORKED_EXAMPLE_12,
        moon_paksha_reading=MoonPakshaReading.WAXING_HALF,
    )
    base.update(kw)
    return RamanShadbalaRequest(**base)  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def service() -> RamanShadbalaService:
    return RamanShadbalaService(None)


def test_service_contract_on_the_standard_horoscope_instant(
    service: RamanShadbalaService,
) -> None:
    facts = service.calculate(_req())
    assert facts.profile_id == RAMAN_PROFILE_ID != PROFILE_ID
    assert facts.standards_version == "1.21.0"
    assert facts.cheshta_frame_ayanamsa == "raman" and facts.ayanamsa == "lahiri"
    d = facts.details
    assert (d.abda_lord, d.masa_lord, d.vara_lord, d.hora_lord) == (
        B.SATURN,
        B.MERCURY,
        B.MERCURY,
        B.MOON,
    )
    assert d.condensed_ahargana == 33405
    assert facts.day_night.third == 3
    assert facts.unnata_ghatis == pytest.approx(24.42, abs=0.05)
    for planet in facts.planets:
        total = planet.component(Component.SHADBALA_TOTAL)
        assert total.status is ComponentStatus.SUCCESS
        assert planet.not_evaluated_components == ()
        leaves = [c for c in planet.components if c.component not in (
            Component.STHANA_TOTAL, Component.KALA_TOTAL, Component.SHADBALA_TOTAL)]  # fmt: skip
        assert total.virupas == pytest.approx(sum(c.virupas or 0.0 for c in leaves))
    rupas = dict(facts.totals_in_rupas)
    assert all(v is not None and v > 0 for v in rupas.values())
    sun = facts.planets[0]
    assert sun.component(Component.CHESHTA).status is ComponentStatus.NOT_APPLICABLE
    assert sun.component(Component.YUDDHA).status is ComponentStatus.NOT_APPLICABLE
    assert {p.component for p in facts.provenance} == set(RAMAN_COMPONENTS)
    assert all(p.reference.source_id == "SRC-RAMAN-GRAHA-BHAVA-BALAS" for p in facts.provenance)


def test_profiles_are_never_mixed(service: RamanShadbalaService) -> None:
    raman = service.calculate(_req())
    bphs = ShadbalaService(None).calculate(
        ShadbalaRequest(
            local_datetime=STANDARD, location=BANGALORE, time_precision=ShadbalaTimePrecision.EXACT
        )
    )
    assert bphs.profile_id == PROFILE_ID
    # The BPHS profile still has no total; the Raman profile does.
    for p in bphs.planets:
        assert p.component(Component.SHADBALA_TOTAL).status is ComponentStatus.NOT_EVALUABLE
    for p in raman.planets:
        assert p.component(Component.SHADBALA_TOTAL).status is ComponentStatus.SUCCESS
    # Same arithmetic where the rules coincide, different where they do not.
    for rp, bp in zip(raman.planets, bphs.planets, strict=True):
        assert rp.component(Component.UCHCHA).virupas == bp.component(Component.UCHCHA).virupas
        assert rp.component(Component.DIG).virupas == bp.component(Component.DIG).virupas
    moon_r = raman.planets[1].component(Component.PAKSHA).virupas or 0.0
    moon_b = bphs.planets[1].component(Component.PAKSHA).virupas or 0.0
    assert moon_r == pytest.approx(2 * moon_b)


def test_readings_change_results(service: RamanShadbalaService) -> None:
    a = service.calculate(_req())
    b = service.calculate(_req(drekkana_reading=DrekkanaReading.TEXT_ARTICLE_36))
    da = [p.component(Component.DREKKANA).virupas for p in a.planets]
    db = [p.component(Component.DREKKANA).virupas for p in b.planets]
    assert da != db


def test_readings_have_no_default() -> None:
    with pytest.raises(ValidationError):
        RamanShadbalaRequest(  # type: ignore[call-arg]
            local_datetime=STANDARD, location=BANGALORE, time_precision=ShadbalaTimePrecision.EXACT
        )


def test_unknown_time(service: RamanShadbalaService) -> None:
    facts = service.calculate(_req(time_precision=ShadbalaTimePrecision.UNKNOWN))
    for p in facts.planets:
        assert p.evaluated_components == (Component.NAISARGIKA,)
        assert p.component(Component.SHADBALA_TOTAL).status is ComponentStatus.NOT_EVALUABLE
    assert dict(facts.totals_in_rupas)[B.SUN] is None


def test_polar_night_is_not_evaluable(service: RamanShadbalaService) -> None:
    facts = service.calculate(
        _req(
            local_datetime=LocalDateTimeInput(
                year=2020, month=12, day=21, hour=12, timezone="Arctic/Longyearbyen"
            ),
            location=Location(latitude=78.2, longitude=15.6),
        )
    )
    for p in facts.planets:
        for comp in (Component.TRIBHAGA, Component.ABDA, Component.MASA, Component.VARA,
                     Component.HORA):  # fmt: skip
            assert p.component(comp).reason is ShadbalaReason.SUNRISE_UNAVAILABLE
        assert p.component(Component.SHADBALA_TOTAL).status is ComponentStatus.NOT_EVALUABLE


def test_cheshta_out_of_table_range(service: RamanShadbalaService) -> None:
    facts = service.calculate(
        _req(local_datetime=LocalDateTimeInput(year=1750, month=6, day=1, hour=6, timezone="UTC"))
    )
    mars = facts.planets[2].component(Component.CHESHTA)
    assert mars.reason is ShadbalaReason.CHESHTA_TABLES_OUT_OF_RANGE


def test_planetary_war() -> None:
    from pandit_astro_engine.shadbala.raman_service import _wars

    ok = {c: _fake(c, 10.0) for c in Component}
    lon = {B.MARS: 100.2, B.MERCURY: 150.0, B.JUPITER: 100.7, B.VENUS: 200.0, B.SATURN: 300.0}
    partial = {b: dict(ok) for b in lon}
    partial[B.MARS][Component.UCHCHA] = _fake(Component.UCHCHA, 40.0)
    wars = _wars(lon, partial)
    assert len(wars) == 1
    war = wars[0]
    assert war.winner is B.MARS  # the lesser longitude wins (Art. 76)
    assert war.yuddha_virupas == pytest.approx(30.0 / abs(9.4 - 190.4))
    # A planet in two wars is not resolved.
    lon3 = {**lon, B.SATURN: 101.0}
    assert all(w.yuddha_virupas is None for w in _wars(lon3, {b: dict(ok) for b in lon3}))


def _fake(component: Component, value: float):  # type: ignore[no-untyped-def]
    from pandit_astro_engine.shadbala.models import ComponentResult
    from pandit_astro_engine.shadbala.profiles import EvidenceLabel

    return ComponentResult(
        component=component,
        status=ComponentStatus.SUCCESS,
        virupas=value,
        evidence_label=EvidenceLabel.MODERN_TRADITION,
    )


def test_deterministic(service: RamanShadbalaService) -> None:
    a = service.calculate(_req()).model_dump(mode="json")
    b = service.calculate(_req()).model_dump(mode="json")
    assert a == b
