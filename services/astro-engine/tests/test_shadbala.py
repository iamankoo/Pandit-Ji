"""Shadbala (Phase 9 WP-F, SB-01 to SB-20). Component formulas against the
worked figures printed in BPHS Ch. 27 (Santhanam, OCR level) and hand
calculations; drift checks against the locked Phase 6 tables; service-level
contract, NOT_EVALUABLE paths and invariants."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.shadbala import (
    LEAF_COMPONENTS,
    PROFILE_ID,
    SHADBALA_BODIES,
    Component,
    ComponentStatus,
    ShadbalaReason,
    ShadbalaRequest,
    ShadbalaService,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala import components as calc
from pandit_astro_engine.shadbala import constants as k

TABLES = (
    Path(__file__).parents[2] / "knowledge" / "rules" / "bphs" / "tables"
)  # services/knowledge/rules/bphs/tables


def _load(name: str) -> dict:  # type: ignore[type-arg]
    return yaml.safe_load((TABLES / name).read_text(encoding="utf-8"))["data"]  # type: ignore[no-any-return]


# --------------------------------------------------------------------------
# Drift checks against the locked Phase 6 tables
# --------------------------------------------------------------------------


def test_natural_relationships_match_the_locked_table() -> None:
    data = _load("relationships_natural_3_55.yaml")
    for body in SHADBALA_BODIES:
        assert {b.value for b in k.NATURAL_FRIENDS[body]} == set(data["friends"][body.value])
        assert {b.value for b in k.NATURAL_ENEMIES[body]} == set(data["enemies"][body.value])


def test_temporal_and_compound_match_the_locked_tables() -> None:
    assert set(_load("relationship_temporal_3_56.yaml")["friend_houses"]) == set(
        k.TEMPORAL_FRIEND_HOUSES
    )
    matrix = {
        (r["natural"], r["temporal"]): r["compound"]
        for r in _load("relationship_compound_3_57_58.yaml")["matrix"]
    }
    assert matrix == k.COMPOUND


def test_moolatrikona_matches_the_locked_table() -> None:
    data = _load("moolatrikona_3_51_54.yaml")["ranges"]
    for body, (sign, start, end) in k.MOOLATRIKONA.items():
        row = data[body.value]
        assert (row["sign"], row["from_degree"], row["to_degree"]) == (sign.value, start, end)


def test_natural_nature_matches_the_locked_table() -> None:
    data = _load("nature_natural_3_11.yaml")
    assert {b.value for b in k.NATURAL_MALEFICS} == set(data["malefic"])
    assert {b.value for b in k.NATURAL_BENEFICS} == set(data["benefic"])
    conv = data["conventions"]
    assert tuple(conv["moon_waxing_elongation_degrees"]) == k.MOON_WAXING_ELONGATION
    assert conv["moon_boundary_epsilon_degrees"] == k.MOON_BOUNDARY_EPSILON_DEGREES


# --------------------------------------------------------------------------
# Component formulas
# --------------------------------------------------------------------------


def test_uchcha_translator_worked_example() -> None:
    # Ch. 27 v. 1 note: the Sun at Pisces 12 deg 15 min, debilitation Libra 10 deg:
    # (342.25 - 190) / 3 = 50.75 Virupas.
    assert calc.uchcha_bala(B.SUN, 342.25) == pytest.approx(50.75)


@pytest.mark.parametrize("body", SHADBALA_BODIES)
def test_uchcha_extremes(body: B) -> None:
    debil = calc.debilitation_longitude(body)
    assert calc.uchcha_bala(body, debil) == pytest.approx(0.0)
    assert calc.uchcha_bala(body, (debil + 180.0) % 360.0) == pytest.approx(60.0)
    assert calc.uchcha_bala(body, (debil + 90.0) % 360.0) == pytest.approx(30.0)
    assert calc.uchcha_bala(body, (debil - 90.0) % 360.0) == pytest.approx(30.0)


def test_dig_bala_note_example() -> None:
    # Note to v. 7: Saturn exactly on the 7th cusp gets 1 Rupa, on the ascendant zero.
    asc = 123.4
    assert calc.dig_bala((asc + 180.0) % 360.0, asc) == pytest.approx(60.0)
    assert calc.dig_bala(asc, asc) == pytest.approx(0.0)


def test_naisargika_values() -> None:
    # v. 14: 60/7 x 1..7 for Saturn, Mars, Mercury, Jupiter, Venus, Moon, Sun.
    expected = {B.SATURN: 1, B.MARS: 2, B.MERCURY: 3, B.JUPITER: 4, B.VENUS: 5, B.MOON: 6, B.SUN: 7}
    for body, n in expected.items():
        assert calc.naisargika_bala(body) == pytest.approx(60.0 * n / 7.0)
    assert calc.naisargika_bala(B.SUN) == pytest.approx(60.0)


def test_ojayugma() -> None:
    assert calc.ojayugma_bala(B.SUN, Rashi.ARIES, Rashi.LEO) == 30.0
    assert calc.ojayugma_bala(B.SUN, Rashi.TAURUS, Rashi.LEO) == 15.0
    assert calc.ojayugma_bala(B.MOON, Rashi.TAURUS, Rashi.CANCER) == 30.0
    assert calc.ojayugma_bala(B.VENUS, Rashi.ARIES, Rashi.GEMINI) == 0.0
    assert calc.ojayugma_bala(B.MERCURY, Rashi.PISCES, Rashi.AQUARIUS) == 15.0


def test_kendradi() -> None:
    assert calc.kendradi_bala(Rashi.ARIES, Rashi.CANCER) == 60.0  # 4th
    assert calc.kendradi_bala(Rashi.ARIES, Rashi.LEO) == 30.0  # 5th
    assert calc.kendradi_bala(Rashi.ARIES, Rashi.PISCES) == 15.0  # 12th
    assert calc.kendradi_bala(Rashi.PISCES, Rashi.PISCES) == 60.0  # 1st


@pytest.mark.parametrize(
    ("body", "degree", "expected"),
    [
        (B.SUN, 5.0, 15.0),
        (B.SUN, 10.0, 0.0),  # boundary: 10 deg starts the second decanate
        (B.MOON, 15.0, 15.0),
        (B.VENUS, 25.0, 0.0),
        (B.SATURN, 25.0, 15.0),
        (B.MERCURY, 29.9999, 15.0),
        (B.MERCURY, 9.9999, 0.0),
    ],
)
def test_drekkana(body: B, degree: float, expected: float) -> None:
    assert calc.drekkana_bala(body, degree) == expected


def test_nathonnatha() -> None:
    # At apparent midnight the Moon group is full and the Sun group empty; at noon the reverse.
    assert calc.unnata_ghatis(0.0) == 0.0
    assert calc.unnata_ghatis(12.0) == 30.0
    assert calc.unnata_ghatis(18.0) == 15.0
    assert calc.unnata_ghatis(23.0) == pytest.approx(2.5)
    assert calc.nathonnatha_bala(B.MOON, 0.0) == 60.0
    assert calc.nathonnatha_bala(B.SUN, 0.0) == 0.0
    assert calc.nathonnatha_bala(B.SATURN, 30.0) == 0.0
    assert calc.nathonnatha_bala(B.VENUS, 30.0) == 60.0
    assert calc.nathonnatha_bala(B.MERCURY, 13.7) == 60.0
    for u in (0.0, 7.5, 21.0, 30.0):
        assert calc.nathonnatha_bala(B.MARS, u) + calc.nathonnatha_bala(B.JUPITER, u) == 60.0


def test_paksha() -> None:
    # Full Moon: benefics 60, malefics 0. New Moon: the reverse.
    assert calc.paksha_bala("benefic", 180.0, 0.0) == pytest.approx(60.0)
    assert calc.paksha_bala("malefic", 180.0, 0.0) == pytest.approx(0.0)
    assert calc.paksha_bala("benefic", 10.0, 10.0) == pytest.approx(0.0)
    # Waning: elongation 270 folds to 90.
    assert calc.paksha_bala("benefic", 270.0, 0.0) == pytest.approx(30.0)


def test_moon_and_mercury_nature() -> None:
    signs = {b: Rashi.ARIES for b in B}
    lon = {b: 0.0 for b in B}
    lon[B.MOON] = 90.0  # waxing
    assert calc.natural_nature(B.MOON, lon, signs) == "benefic"
    lon[B.MOON] = 270.0
    assert calc.natural_nature(B.MOON, lon, signs) == "malefic"
    lon[B.MOON] = 180.0  # exactly full: boundary
    assert calc.natural_nature(B.MOON, lon, signs) is None
    # Mercury alone: benefic; with Jupiter only: benefic; with Saturn: malefic;
    # with both: not classified.
    spread = {b: Rashi.TAURUS for b in B}
    spread[B.MERCURY] = Rashi.ARIES
    lon[B.MOON] = 90.0
    assert calc.natural_nature(B.MERCURY, lon, spread) == "benefic"
    spread[B.JUPITER] = Rashi.ARIES
    assert calc.natural_nature(B.MERCURY, lon, spread) == "benefic"
    spread[B.SATURN] = Rashi.ARIES
    assert calc.natural_nature(B.MERCURY, lon, spread) is None
    spread[B.JUPITER] = Rashi.TAURUS
    assert calc.natural_nature(B.MERCURY, lon, spread) == "malefic"
    spread[B.SATURN] = Rashi.TAURUS
    spread[B.RAHU] = Rashi.ARIES
    assert calc.natural_nature(B.MERCURY, lon, spread) == "malefic"


def test_tribhaga() -> None:
    assert calc.tribhaga_bala(B.MERCURY, True, 1) == 60.0
    assert calc.tribhaga_bala(B.SUN, True, 2) == 60.0
    assert calc.tribhaga_bala(B.SATURN, True, 3) == 60.0
    assert calc.tribhaga_bala(B.MOON, False, 1) == 60.0
    assert calc.tribhaga_bala(B.VENUS, False, 2) == 60.0
    assert calc.tribhaga_bala(B.MARS, False, 3) == 60.0
    assert calc.tribhaga_bala(B.SUN, False, 2) == 0.0
    for is_day in (True, False):
        for third in (1, 2, 3):
            assert calc.tribhaga_bala(B.JUPITER, is_day, third) == 60.0
            holders = sum(calc.tribhaga_bala(b, is_day, third) > 0 for b in SHADBALA_BODIES)
            assert holders == 2  # Jupiter plus one planet (note to v. 12)


def test_vara() -> None:
    assert calc.vara_bala(B.JUPITER, 4) == 45.0
    assert calc.vara_bala(B.SUN, 0) == 45.0
    assert calc.vara_bala(B.SATURN, 4) == 0.0


def test_saptavarga_categories() -> None:
    d1 = {b: Rashi.ARIES for b in SHADBALA_BODIES}
    # D1 Moolatrikona by degree.
    assert calc.saptavarga_category(B.SUN, 1, Rashi.LEO, 10.0, d1) == "moolatrikona"
    # D1 Moolatrikona sign outside the degree range: not evaluable.
    assert calc.saptavarga_category(B.SUN, 1, Rashi.LEO, 25.0, d1) is None
    assert calc.saptavarga_category(B.MOON, 1, Rashi.TAURUS, 1.0, d1) is None
    # Other vargas: the Moolatrikona sign counts ("Moolatrikona Rasi").
    assert calc.saptavarga_category(B.SUN, 9, Rashi.LEO, 25.0, d1) == "moolatrikona"
    # Own sign.
    assert calc.saptavarga_category(B.MARS, 1, Rashi.SCORPIO, 5.0, d1) == "own"
    assert calc.saptavarga_category(B.SATURN, 12, Rashi.CAPRICORN, 5.0, d1) == "own"


def test_compound_relationship_uses_the_rasi_chart() -> None:
    # Sun and Moon natural friends; Moon in the 2nd from the Sun -> temporal friend -> great
    # friend. Moon in the 7th -> temporal enemy -> equal.
    d1 = {b: Rashi.ARIES for b in SHADBALA_BODIES}
    d1[B.MOON] = Rashi.TAURUS
    assert calc.compound_relationship(B.SUN, B.MOON, d1) == "great_friend"
    d1[B.MOON] = Rashi.LIBRA
    assert calc.compound_relationship(B.SUN, B.MOON, d1) == "equal"
    # Sun and Saturn natural enemies; Saturn in the 7th -> great enemy.
    d1[B.SATURN] = Rashi.LIBRA
    assert calc.compound_relationship(B.SUN, B.SATURN, d1) == "great_enemy"


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

DELHI = Location(latitude=28.61, longitude=77.21)


def _req(
    h: int = 10,
    mi: int = 30,
    *,
    location: Location = DELHI,
    tz: str = "Asia/Kolkata",
    date: tuple[int, int, int] = (1990, 5, 17),
    precision: ShadbalaTimePrecision = ShadbalaTimePrecision.EXACT,
) -> ShadbalaRequest:
    y, m, d = date
    return ShadbalaRequest(
        local_datetime=LocalDateTimeInput(year=y, month=m, day=d, hour=h, minute=mi, timezone=tz),
        location=location,
        time_precision=precision,
    )


@pytest.fixture(scope="module")
def service() -> ShadbalaService:
    return ShadbalaService(None)


def test_service_contract(service: ShadbalaService) -> None:
    facts = service.calculate(_req())
    assert facts.profile_id == PROFILE_ID
    assert facts.standards_version == "1.16.0"
    assert facts.system == "vedic_parashari"
    assert facts.ayanamsa == "lahiri"
    assert [p.body for p in facts.planets] == list(SHADBALA_BODIES)
    assert facts.day_night.status is ComponentStatus.SUCCESS
    assert facts.day_night.is_day is True
    assert facts.day_night.third == 2
    assert facts.day_night.vara_weekday_sunday_zero == 4  # 17 May 1990 was a Thursday
    for planet in facts.planets:
        assert [c.component for c in planet.components[: len(LEAF_COMPONENTS)]] == list(
            LEAF_COMPONENTS
        )
        total = planet.component(Component.SHADBALA_TOTAL)
        assert total.status is ComponentStatus.NOT_EVALUABLE
        assert total.reason is ShadbalaReason.COMPONENT_NOT_EVALUABLE
        assert planet.component(Component.KALA_TOTAL).status is ComponentStatus.NOT_EVALUABLE
        subtotal = sum(c.virupas or 0.0 for c in planet.components[: len(LEAF_COMPONENTS)])
        assert planet.evaluated_subtotal_virupas == pytest.approx(subtotal)
        assert set(planet.evaluated_components).isdisjoint(planet.not_evaluated_components)
        for comp in (
            Component.ABDA,
            Component.MASA,
            Component.HORA,
            Component.AYANA,
            Component.DRIK,
        ):
            assert planet.component(comp).status is ComponentStatus.NOT_EVALUABLE
    by = {p.body: p for p in facts.planets}
    assert by[B.JUPITER].component(Component.VARA).virupas == 45.0
    assert by[B.SUN].component(Component.TRIBHAGA).virupas == 60.0
    assert (
        by[B.MOON].component(Component.CHESHTA).virupas
        == by[B.MOON].component(Component.PAKSHA).virupas
    )
    assert by[B.SUN].component(Component.YUDDHA).status is ComponentStatus.NOT_APPLICABLE
    assert by[B.MARS].component(Component.YUDDHA).reason is ShadbalaReason.PLANETARY_WAR_UNDEFINED


def test_ranges_and_group_invariants(service: ShadbalaService) -> None:
    facts = service.calculate(_req())
    by = {p.body: p for p in facts.planets}
    for planet in facts.planets:
        for c in planet.components:
            if c.virupas is not None and c.component not in (
                Component.STHANA_TOTAL,
                Component.SAPTAVARGAJA,
            ):
                assert 0.0 <= c.virupas <= 60.0 + 1e-9
    n = {b: by[b].component(Component.NATHONNATHA).virupas for b in by}
    assert n[B.MERCURY] == 60.0
    assert n[B.MOON] == n[B.MARS] == n[B.SATURN]
    assert n[B.SUN] == n[B.JUPITER] == n[B.VENUS]
    assert (n[B.MOON] or 0) + (n[B.SUN] or 0) == pytest.approx(60.0)
    sapta = by[B.SATURN]
    assert len(sapta.saptavarga) == 7
    assert [p.varga for p in sapta.saptavarga] == [1, 2, 3, 7, 9, 12, 30]


def test_night_birth_and_polar_night(service: ShadbalaService) -> None:
    night = service.calculate(_req(23, 30))
    assert night.day_night.is_day is False
    polar = service.calculate(
        _req(
            12,
            0,
            location=Location(latitude=78.2, longitude=15.6),
            tz="Arctic/Longyearbyen",
            date=(2020, 12, 21),
        )
    )
    assert polar.day_night.status is ComponentStatus.NOT_EVALUABLE
    for planet in polar.planets:
        assert planet.component(Component.TRIBHAGA).reason is ShadbalaReason.SUNRISE_UNAVAILABLE
        assert planet.component(Component.VARA).reason is ShadbalaReason.SUNRISE_UNAVAILABLE
        assert planet.component(Component.UCHCHA).status is ComponentStatus.SUCCESS


def test_vara_before_sunrise_is_the_previous_weekday(service: ShadbalaService) -> None:
    early = service.calculate(_req(4, 0))  # before sunrise on a Thursday
    assert early.day_night.vara_weekday_sunday_zero == 3  # Wednesday's Vara
    by = {p.body: p for p in early.planets}
    assert by[B.MERCURY].component(Component.VARA).virupas == 45.0


def test_unknown_time(service: ShadbalaService) -> None:
    facts = service.calculate(_req(precision=ShadbalaTimePrecision.UNKNOWN))
    for planet in facts.planets:
        assert planet.evaluated_components == (Component.NAISARGIKA,)
        assert planet.component(Component.UCHCHA).reason is ShadbalaReason.BIRTH_TIME_UNKNOWN
    assert facts.lagna_longitude is None
    assert "birth time unknown" in facts.warnings[0]


def test_deterministic(service: ShadbalaService) -> None:
    a = service.calculate(_req()).model_dump(mode="json")
    b = service.calculate(_req()).model_dump(mode="json")
    assert a == b


def test_provenance_covers_every_leaf_component(service: ShadbalaService) -> None:
    facts = service.calculate(_req())
    covered = {p.component for p in facts.provenance}
    assert set(LEAF_COMPONENTS) <= covered
    for p in facts.provenance:
        assert p.reference.source_id == "SRC-BPHS-SANTHANAM-1984"
