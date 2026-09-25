"""KP natal, Ruling Planets and horary services (Phase 9 WP-E, KP-01 to
KP-16): the KP Reader VI worked horary example, the KP Reader I ayanamsa
table, isolation from the Vedic pipeline, NOT_EVALUABLE paths and request
validation."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import swisseph as swe
from pydantic import ValidationError

from pandit_astro_engine.kp import (
    AYANAMSA_KRISHNAMURTI_ID,
    AYANAMSA_KRISHNAMURTI_VP291_ID,
    KP_STANDARDS_VERSION,
    KP_SYSTEM_ID,
    DayLordConvention,
    KpChartRequest,
    KpHoraryRequest,
    KpReason,
    KpRulingPlanetsRequest,
    KpService,
    KpStatus,
    KpTimePrecision,
    RulingRole,
)
from pandit_astro_engine.kp.service import solve_armc_for_ascendant
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CelestialBody,
    LocalDateTimeInput,
    Location,
    NodeConvention,
)
from pandit_astro_engine.rashi import Rashi

FIXTURES = Path(__file__).parent / "fixtures"
KP_SRC = Path(__file__).parents[1] / "src" / "pandit_astro_engine" / "kp"

DELHI = Location(latitude=28.6139, longitude=77.2090)
BOMBAY = Location(latitude=18.97, longitude=72.82)


def _ldt(y: int, mo: int, d: int, h: int, mi: int, tz: str = "Asia/Kolkata") -> LocalDateTimeInput:
    return LocalDateTimeInput(year=y, month=mo, day=d, hour=h, minute=mi, timezone=tz)


def _dms(text: str) -> float:
    parts = [int(x) for x in text.split("-")]
    return parts[0] + parts[1] / 60 + (parts[2] / 3600 if len(parts) > 2 else 0.0)


@pytest.fixture(scope="module")
def service() -> KpService:
    return KpService(None)


def _chart(
    service: KpService,
    *,
    location: Location = DELHI,
    precision: KpTimePrecision = KpTimePrecision.EXACT,
    ayanamsa: str = AYANAMSA_KRISHNAMURTI_ID,
    node: NodeConvention = NodeConvention.MEAN,
) -> object:
    return service.calculate_chart(
        KpChartRequest(
            local_datetime=_ldt(1990, 5, 17, 12, 0),
            location=location,
            time_precision=precision,
            node_convention=node,
            ayanamsa_profile_id=ayanamsa,
        )
    )


# --------------------------------------------------------------------------
# KP Reader VI horary example (number 29, Bombay, 6 May 1969, 17:30 IST)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def reader_example(service: KpService):  # type: ignore[no-untyped-def]
    doc = json.loads((FIXTURES / "kp_reader6_horary_29.json").read_text(encoding="utf-8"))
    facts = service.calculate_horary(
        KpHoraryRequest(
            horary_number=29,
            local_datetime=_ldt(1969, 5, 6, 17, 30),
            location=BOMBAY,
            node_convention=NodeConvention.MEAN,
            day_lord_convention=DayLordConvention.LOCAL_CIVIL_DATE,
        )
    )
    return doc["printed"], facts


def test_reader_example_ascendant_and_seventh_cusp(reader_example) -> None:  # type: ignore[no-untyped-def]
    printed, facts = reader_example
    assert facts.cusps.status is KpStatus.SUCCESS
    first, seventh = facts.cusps.cusps[0], facts.cusps.cusps[6]
    assert first.lordship.sign is Rashi.TAURUS
    assert first.longitude == pytest.approx(40.0, abs=1e-9)
    cusp7 = printed["cusp_7"]
    assert seventh.lordship.sign.value == cusp7["sign"]
    assert seventh.longitude % 30 == pytest.approx(_dms(cusp7["degree_in_sign"]), abs=1 / 60)
    assert seventh.lordship.star_lord.value == cusp7["star_lord"]
    assert seventh.lordship.sub_lord.value == cusp7["sub_lord"]


def test_reader_example_ayanamsa_and_planets(reader_example) -> None:  # type: ignore[no-untyped-def]
    printed, facts = reader_example
    assert facts.ayanamsa_degrees == pytest.approx(_dms(printed["ayanamsa"]), abs=1 / 60)
    planets = {p.body: p for p in facts.planets}
    assert planets[CelestialBody.MOON].longitude % 30 == pytest.approx(
        _dms(printed["moon_degree_in_sign"]), abs=1 / 60
    )
    venus = planets[CelestialBody.VENUS]
    assert venus.lordship is not None and venus.lordship.sign.value == printed["venus_sign"]
    assert venus.longitude % 30 == pytest.approx(_dms(printed["venus_degree_in_sign"]), abs=1 / 60)


def test_reader_example_dasa_balance_follows_from_the_moon(reader_example) -> None:  # type: ignore[no-untyped-def]
    # Printed: "Balance of Venus Dasa 7 years 11 months 12 days". The Moon's star must be a
    # Venus star with about 0.3975 of it left (7.95 of 20 years).
    _printed, facts = reader_example
    moon = next(p for p in facts.planets if p.body is CelestialBody.MOON)
    assert moon.lordship is not None and moon.lordship.star_lord is CelestialBody.VENUS
    remaining = (13 + 20 / 60) - (moon.longitude % (40 / 3))
    years = remaining / (40 / 3) * 20
    assert years == pytest.approx(7 + 11 / 12 + 12 / 360, abs=0.01)


def test_reader_example_intermediate_cusps_within_table_tolerance(reader_example) -> None:  # type: ignore[no-untyped-def]
    printed, facts = reader_example
    cusps = facts.cusps.cusps
    assert cusps[11].longitude % 30 == pytest.approx(
        _dms(printed["cusp_12_degree_in_sign"]), abs=10 / 60
    )
    assert cusps[7].longitude % 30 == pytest.approx(
        _dms(printed["cusp_8_degree_in_sign"]), abs=10 / 60
    )


def test_reader_example_significators_subset_except_documented_houses(reader_example) -> None:  # type: ignore[no-untyped-def]
    printed, facts = reader_example
    for house in facts.significators.houses:
        ours = {
            b.value
            for b in house.level_a_in_star_of_occupants
            + house.level_b_occupants
            + house.level_c_in_star_of_lord
            + house.level_d_lord
        }
        reader = set(printed["significators_by_house"][str(house.house)])
        if house.house == 2:
            assert ours - reader == {"venus"}
        elif house.house == 5:
            assert ours - reader == {"sun"}
        else:
            assert ours <= reader, house.house


# --------------------------------------------------------------------------
# Ayanamsa (KP Reader I table; engineering evidence)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "printed"),
    [
        (1900, "22-22"),
        (1934, "22-50"),
        (1950, "23-04"),
        (1970, "23-20"),
        (1984, "23-32"),
        (2000, "23-46"),
    ],
)
def test_default_ayanamsa_matches_reader1_table(
    service: KpService, year: int, printed: str
) -> None:
    facts = service.calculate_chart(
        KpChartRequest(
            local_datetime=_ldt(year, 1, 1, 5, 30),
            location=DELHI,
            time_precision=KpTimePrecision.EXACT,
            node_convention=NodeConvention.MEAN,
        )
    )
    # The printed table is rounded to the arcminute; nutation adds up to 0.3 arcmin.
    assert facts.ayanamsa_degrees == pytest.approx(_dms(printed), abs=1.0 / 60)


def test_ayanamsa_profiles_differ_and_are_recorded(service: KpService) -> None:
    a = _chart(service)
    b = _chart(service, ayanamsa=AYANAMSA_KRISHNAMURTI_VP291_ID)
    assert a.profiles.ayanamsa_profile_id == AYANAMSA_KRISHNAMURTI_ID  # type: ignore[attr-defined]
    assert b.profiles.ayanamsa_profile_id == AYANAMSA_KRISHNAMURTI_VP291_ID  # type: ignore[attr-defined]
    diff = b.ayanamsa_degrees - a.ayanamsa_degrees  # type: ignore[attr-defined]
    assert 0.5 / 60 < diff < 2.5 / 60


def test_kp_is_not_lahiri(service: KpService) -> None:
    facts = _chart(service)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    jd = facts.time_resolution.julian_day_ut  # type: ignore[attr-defined]
    lahiri = swe.get_ayanamsa_ex_ut(jd, 0)[1]
    assert 3 / 60 < lahiri - facts.ayanamsa_degrees < 8 / 60  # type: ignore[attr-defined]


# --------------------------------------------------------------------------
# Isolation from the Vedic pipeline (the sidereal mode is process-global)
# --------------------------------------------------------------------------


def test_kp_call_does_not_change_a_vedic_kundli(service: KpService) -> None:
    kundli_service = KundliCalculationService()
    request = AstronomicalCalculationRequest(
        local_datetime=_ldt(1990, 5, 17, 12, 0), location=DELHI
    )
    before = kundli_service.calculate(request).model_dump(mode="json")
    _chart(service)
    service.calculate_horary(
        KpHoraryRequest(
            horary_number=100,
            local_datetime=_ldt(2020, 1, 1, 10, 0),
            location=DELHI,
            node_convention=NodeConvention.TRUE,
            day_lord_convention=DayLordConvention.SUNRISE_TO_SUNRISE,
        )
    )
    after = kundli_service.calculate(request).model_dump(mode="json")
    assert before == after


def test_sidereal_mode_restored_after_kp_call(service: KpService) -> None:
    from pandit_astro_engine import ephemeris
    from pandit_astro_engine.models import Ayanamsa

    ephemeris.set_sidereal_mode(Ayanamsa.LAHIRI)
    jd = swe.julday(2000, 1, 1, 12.0)
    lahiri = swe.get_ayanamsa_ut(jd)
    _chart(service)
    assert swe.get_ayanamsa_ut(jd) == lahiri


def test_kp_modules_do_not_import_swisseph_or_other_systems() -> None:
    forbidden = {
        "swisseph",
        "pandit_astro_engine.western",
        "pandit_astro_engine.jaimini",
        "pandit_astro_engine.ashtakavarga",
        "pandit_astro_engine.aspects",
    }
    for path in KP_SRC.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not any(name == f or name.startswith(f + ".") for f in forbidden), (
                    path.name,
                    name,
                )


# --------------------------------------------------------------------------
# Natal chart contract
# --------------------------------------------------------------------------


def test_natal_chart_contract(service: KpService) -> None:
    facts = _chart(service)
    assert facts.system == KP_SYSTEM_ID  # type: ignore[attr-defined]
    assert facts.standards_version == KP_STANDARDS_VERSION == "1.15.0"  # type: ignore[attr-defined]
    assert facts.cusps.status is KpStatus.SUCCESS  # type: ignore[attr-defined]
    cusps = facts.cusps.cusps  # type: ignore[attr-defined]
    assert len(cusps) == 12
    total = sum((cusps[(i + 1) % 12].longitude - cusps[i].longitude) % 360 for i in range(12))
    assert total == pytest.approx(360.0)
    assert {p.body for p in facts.planets} == set(CelestialBody)  # type: ignore[attr-defined]
    for p in facts.planets:  # type: ignore[attr-defined]
        assert p.lordship is not None and 1 <= (p.house or 0) <= 12
    rahu = next(p for p in facts.planets if p.body is CelestialBody.RAHU)  # type: ignore[attr-defined]
    ketu = next(p for p in facts.planets if p.body is CelestialBody.KETU)  # type: ignore[attr-defined]
    assert (ketu.longitude - rahu.longitude) % 360 == pytest.approx(180.0)
    assert rahu.node_convention is NodeConvention.MEAN
    ids = [e.entry_id for e in facts.provenance]  # type: ignore[attr-defined]
    assert ids == ["prov.ayanamsa", "prov.houses", "prov.subdivision", "prov.significators"]


def test_significator_levels_are_consistent(service: KpService) -> None:
    facts = _chart(service)
    planets = {p.body: p for p in facts.planets}  # type: ignore[attr-defined]
    for house in facts.significators.houses:  # type: ignore[attr-defined]
        occupants = set(house.level_b_occupants)
        assert occupants == {b for b, p in planets.items() if p.house == house.house}
        lord = house.level_d_lord[0]
        assert lord == facts.cusps.cusps[house.house - 1].lordship.sign_lord  # type: ignore[attr-defined]
        assert set(house.level_c_in_star_of_lord) == {
            b for b, p in planets.items() if p.lordship.star_lord == lord
        }
        assert set(house.level_a_in_star_of_occupants) == {
            b for b, p in planets.items() if p.lordship.star_lord in occupants
        }
    assert facts.significators.not_evaluated == (  # type: ignore[attr-defined]
        "level_e_conjunction",
        "level_f_aspect",
        "node_agency",
    )


def test_natal_deterministic(service: KpService) -> None:
    a = _chart(service).model_dump(mode="json")  # type: ignore[attr-defined]
    b = _chart(service).model_dump(mode="json")  # type: ignore[attr-defined]
    assert a == b


def test_unknown_birth_time(service: KpService) -> None:
    facts = _chart(service, precision=KpTimePrecision.UNKNOWN)
    assert facts.cusps.status is KpStatus.NOT_EVALUABLE  # type: ignore[attr-defined]
    assert facts.cusps.reason is KpReason.BIRTH_TIME_UNKNOWN  # type: ignore[attr-defined]
    assert facts.significators.status is KpStatus.NOT_EVALUABLE  # type: ignore[attr-defined]
    assert all(p.lordship is None and p.house is None for p in facts.planets)  # type: ignore[attr-defined]
    assert "birth time unknown" in facts.warnings[0]  # type: ignore[attr-defined]


def test_polar_latitude_not_evaluable(service: KpService) -> None:
    facts = _chart(service, location=Location(latitude=78.2, longitude=15.6))
    assert facts.cusps.status is KpStatus.NOT_EVALUABLE  # type: ignore[attr-defined]
    assert facts.cusps.reason is KpReason.PLACIDUS_POLAR_CIRCLE  # type: ignore[attr-defined]
    assert facts.significators.reason is KpReason.PLACIDUS_POLAR_CIRCLE  # type: ignore[attr-defined]
    assert all(p.house is None and p.lordship is not None for p in facts.planets)  # type: ignore[attr-defined]


def test_true_node_changes_only_the_nodes(service: KpService) -> None:
    mean = {p.body: p.longitude for p in _chart(service).planets}  # type: ignore[attr-defined]
    true = {p.body: p.longitude for p in _chart(service, node=NodeConvention.TRUE).planets}  # type: ignore[attr-defined]
    for body in CelestialBody:
        if body in (CelestialBody.RAHU, CelestialBody.KETU):
            assert mean[body] != true[body]
        else:
            assert mean[body] == true[body]


# --------------------------------------------------------------------------
# Ruling Planets
# --------------------------------------------------------------------------


def _ruling(service: KpService, location: Location, convention: DayLordConvention, h: int):  # type: ignore[no-untyped-def]
    return service.ruling_planets(
        KpRulingPlanetsRequest(
            local_datetime=_ldt(2024, 3, 12, h, 0),
            location=location,
            node_convention=NodeConvention.MEAN,
            day_lord_convention=convention,
        )
    )


def test_ruling_planets_structure(service: KpService) -> None:
    facts = _ruling(service, DELHI, DayLordConvention.LOCAL_CIVIL_DATE, 10)
    rp = facts.ruling_planets
    assert rp.status is KpStatus.SUCCESS
    assert rp.weekday_sunday_zero == 2  # 12 March 2024 was a Tuesday
    roles = [m.role for m in rp.members]
    assert roles[:5] == [
        RulingRole.ASCENDANT_STAR_LORD,
        RulingRole.ASCENDANT_SIGN_LORD,
        RulingRole.MOON_STAR_LORD,
        RulingRole.MOON_SIGN_LORD,
        RulingRole.DAY_LORD,
    ]
    assert rp.members[4].body is CelestialBody.MARS
    for m in rp.members[5:]:
        assert m.role is RulingRole.NODE_AGENT
        assert m.body in (CelestialBody.RAHU, CelestialBody.KETU)
        assert m.represents in {rp.members[1].body, rp.members[3].body, rp.members[4].body}


def test_sunrise_convention_uses_previous_weekday_before_sunrise(service: KpService) -> None:
    civil = _ruling(service, DELHI, DayLordConvention.LOCAL_CIVIL_DATE, 4)
    sunrise = _ruling(service, DELHI, DayLordConvention.SUNRISE_TO_SUNRISE, 4)
    assert civil.ruling_planets.weekday_sunday_zero == 2
    assert sunrise.ruling_planets.weekday_sunday_zero == 1
    after = _ruling(service, DELHI, DayLordConvention.SUNRISE_TO_SUNRISE, 10)
    assert after.ruling_planets.weekday_sunday_zero == 2


def test_sunrise_convention_without_sunrise_is_not_evaluable(service: KpService) -> None:
    facts = service.ruling_planets(
        KpRulingPlanetsRequest(
            local_datetime=_ldt(2024, 12, 21, 12, 0, "Arctic/Longyearbyen"),
            location=Location(latitude=78.2, longitude=15.6),
            node_convention=NodeConvention.MEAN,
            day_lord_convention=DayLordConvention.SUNRISE_TO_SUNRISE,
        )
    )
    assert facts.ruling_planets.status is KpStatus.NOT_EVALUABLE
    assert facts.ruling_planets.reason is KpReason.SUNRISE_UNAVAILABLE


# --------------------------------------------------------------------------
# Horary
# --------------------------------------------------------------------------


@pytest.mark.parametrize("number", [1, 48, 74, 106, 189, 249])
def test_horary_ascendant_is_the_entry_start(service: KpService, number: int) -> None:
    facts = service.calculate_horary(
        KpHoraryRequest(
            horary_number=number,
            local_datetime=_ldt(2021, 6, 1, 9, 15),
            location=DELHI,
            node_convention=NodeConvention.MEAN,
            day_lord_convention=DayLordConvention.LOCAL_CIVIL_DATE,
        )
    )
    assert facts.entry.number == number
    assert facts.cusps.status is KpStatus.SUCCESS
    assert facts.cusps.cusps[0].longitude == pytest.approx(facts.entry.start % 360, abs=1e-9)
    first = facts.cusps.cusps[0].lordship
    assert (first.sign, first.star_lord, first.sub_lord) == (
        facts.entry.sign,
        facts.entry.star_lord,
        facts.entry.sub_lord,
    )


def test_horary_cusps_depend_on_latitude_not_longitude(service: KpService) -> None:
    def cusps(location: Location) -> list[float]:
        facts = service.calculate_horary(
            KpHoraryRequest(
                horary_number=150,
                local_datetime=_ldt(2021, 6, 1, 9, 15, "UTC"),
                location=location,
                node_convention=NodeConvention.MEAN,
                day_lord_convention=DayLordConvention.LOCAL_CIVIL_DATE,
            )
        )
        return [c.longitude for c in facts.cusps.cusps]

    a = cusps(Location(latitude=28.6, longitude=77.2))
    b = cusps(Location(latitude=28.6, longitude=-40.0))
    c = cusps(Location(latitude=12.9, longitude=77.2))
    assert a == pytest.approx(b, abs=1e-9)
    assert a[1] != pytest.approx(c[1], abs=1e-3)


def test_horary_polar_not_evaluable(service: KpService) -> None:
    facts = service.calculate_horary(
        KpHoraryRequest(
            horary_number=10,
            local_datetime=_ldt(2021, 6, 1, 9, 15, "UTC"),
            location=Location(latitude=80.0, longitude=0.0),
            node_convention=NodeConvention.MEAN,
            day_lord_convention=DayLordConvention.LOCAL_CIVIL_DATE,
        )
    )
    assert facts.cusps.reason is KpReason.PLACIDUS_POLAR_CIRCLE
    assert facts.significators.status is KpStatus.NOT_EVALUABLE
    assert all(p.house is None for p in facts.planets)


def test_armc_solver_roundtrip() -> None:
    from pandit_astro_engine import ephemeris

    for target in (0.0, 33.3, 179.99, 270.0, 359.5):
        armc = solve_armc_for_ascendant(target, latitude=40.0, obliquity=23.44)
        assert armc is not None
        asc = ephemeris.placidus_houses_from_armc(armc, latitude=40.0, obliquity=23.44).ascendant
        assert (asc - target + 180) % 360 - 180 == pytest.approx(0.0, abs=1e-8)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def test_unknown_ayanamsa_profile_rejected() -> None:
    with pytest.raises(ValidationError):
        KpChartRequest(
            local_datetime=_ldt(1990, 1, 1, 0, 0),
            location=DELHI,
            time_precision=KpTimePrecision.EXACT,
            node_convention=NodeConvention.MEAN,
            ayanamsa_profile_id="LAHIRI",
        )


def test_node_convention_is_required() -> None:
    with pytest.raises(ValidationError):
        KpChartRequest(  # type: ignore[call-arg]
            local_datetime=_ldt(1990, 1, 1, 0, 0),
            location=DELHI,
            time_precision=KpTimePrecision.EXACT,
        )


def test_day_lord_convention_is_required() -> None:
    with pytest.raises(ValidationError):
        KpRulingPlanetsRequest(  # type: ignore[call-arg]
            local_datetime=_ldt(1990, 1, 1, 0, 0),
            location=DELHI,
            node_convention=NodeConvention.MEAN,
        )


@pytest.mark.parametrize("number", [0, 250])
def test_horary_number_range(number: int) -> None:
    with pytest.raises(ValidationError):
        KpHoraryRequest(
            horary_number=number,
            local_datetime=_ldt(1990, 1, 1, 0, 0),
            location=DELHI,
            node_convention=NodeConvention.MEAN,
            day_lord_convention=DayLordConvention.LOCAL_CIVIL_DATE,
        )


def test_invalid_timezone_raises(service: KpService) -> None:
    from pandit_astro_engine.errors import InvalidTimezoneError

    with pytest.raises(InvalidTimezoneError):
        service.calculate_chart(
            KpChartRequest(
                local_datetime=_ldt(1990, 1, 1, 0, 0, "Mars/Olympus"),
                location=DELHI,
                time_precision=KpTimePrecision.EXACT,
                node_convention=NodeConvention.MEAN,
            )
        )
