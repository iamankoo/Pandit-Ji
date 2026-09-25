"""Chinese Four Pillars (Phase 9 WP-H, CN-01 to CN-14). Independent
references: Hong Kong Observatory solar-term instants 2020-2028 and year
names 1901-2100 (fixture `hko_solar_terms_and_year_names.json`), the stem
rules of 《三命通會》 卷二 論遁月時 transcribed as tables below, and the
almanac reading 1 January 2000 = 己卯年 丙子月 戊午日 (secondary)."""

from __future__ import annotations

import ast
import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pandit_astro_engine import ephemeris
from pandit_astro_engine.chinese import (
    CHINESE_STANDARDS_VERSION,
    PROFILE_ID,
    Branch,
    ChineseChartRequest,
    ChineseChartService,
    ChineseTimePrecision,
    DayBoundary,
    PillarReason,
    PillarStatus,
    Stem,
    TimeBasis,
    solar_term_instant,
)
from pandit_astro_engine.chinese import pillars as calc
from pandit_astro_engine.chinese.constants import BRANCH_ANIMAL, BRANCH_ELEMENT, STEM_ELEMENT
from pandit_astro_engine.models import LocalDateTimeInput, Location

FIXTURE = Path(__file__).parent / "fixtures" / "hko_solar_terms_and_year_names.json"
SRC = Path(__file__).parents[1] / "src" / "pandit_astro_engine" / "chinese"
BEIJING = Location(latitude=39.9, longitude=116.4)
HKT = dt.timezone(dt.timedelta(hours=8))


@pytest.fixture(scope="module")
def service() -> ChineseChartService:
    return ChineseChartService(None)


def _req(
    y: int,
    mo: int,
    d: int,
    h: int,
    mi: int,
    *,
    tz: str = "Asia/Shanghai",
    basis: TimeBasis = TimeBasis.CLOCK_TIME,
    boundary: DayBoundary = DayBoundary.ZI_HOUR_2300,
    precision: ChineseTimePrecision = ChineseTimePrecision.EXACT,
    location: Location = BEIJING,
) -> ChineseChartRequest:
    return ChineseChartRequest(
        local_datetime=LocalDateTimeInput(year=y, month=mo, day=d, hour=h, minute=mi, timezone=tz),
        location=location,
        time_precision=precision,
        time_basis=basis,
        day_boundary=boundary,
    )


def _jd(when: dt.datetime) -> float:
    u = when.astimezone(dt.timezone.utc)
    return ephemeris.utc_to_julian_day(u.year, u.month, u.day, u.hour, u.minute, float(u.second))[1]


# --------------------------------------------------------------------------
# Independent references
# --------------------------------------------------------------------------


def test_all_hko_solar_terms_2020_2028_within_one_minute() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(doc["solar_terms"]) == 216
    worst = 0.0
    for row in doc["solar_terms"]:
        published = dt.datetime.fromisoformat(row["hkt"]).replace(tzinfo=HKT)
        jd = solar_term_instant(float(row["sun_longitude"]), _jd(published), True)
        diff_min = abs(jd - _jd(published)) * 1440.0
        worst = max(worst, diff_min)
        # HKO rounds to the minute; allow the rounding plus a few seconds.
        assert diff_min <= 1.0, row
    assert worst <= 1.0


def test_hko_year_names_1901_2100() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hko_animal = {"mouse": "rat"}  # HKO's English name for 子; the text's 鼠
    for year, name in doc["year_names"].items():
        stem, branch = calc.sexagenary(calc.year_index(int(year)))
        assert (stem.value, branch.value) == (name["stem"], name["branch"]), year
        assert BRANCH_ANIMAL[branch] == hko_animal.get(name["animal"], name["animal"])


def test_almanac_reference_1_january_2000(service: ChineseChartService) -> None:
    f = service.calculate(_req(2000, 1, 1, 12, 0))
    assert (f.year.stem_character, f.year.branch_character) == ("己", "卯")
    assert (f.month.stem_character, f.month.branch_character) == ("丙", "子")
    assert (f.day.stem_character, f.day.branch_character) == ("戊", "午")
    assert f.lichun_year == 1999
    # Noon is the 午 hour; a 戊 day starts its 子 hour at 壬子, so 午 is 戊午.
    assert (f.hour.stem_character, f.hour.branch_character) == ("戊", "午")


# --------------------------------------------------------------------------
# 《三命通會》 stem rules, exhaustively
# --------------------------------------------------------------------------

#: 甲己之年丙作首，乙庚之歲戊為頭，丙辛之歲尋庚上，丁壬壬位順行流，戊癸...甲寅
FIRST_MONTH_STEM = {
    Stem.JIA: Stem.BING,
    Stem.JI: Stem.BING,
    Stem.YI: Stem.WU,
    Stem.GENG: Stem.WU,
    Stem.BING: Stem.GENG,
    Stem.XIN: Stem.GENG,
    Stem.DING: Stem.REN,
    Stem.REN: Stem.REN,
    Stem.WU: Stem.JIA,
    Stem.GUI: Stem.JIA,
}
#: 甲己還加甲，乙庚丙作初，丙辛從戊起，丁壬庚子居，戊癸...壬子
FIRST_HOUR_STEM = {
    Stem.JIA: Stem.JIA,
    Stem.JI: Stem.JIA,
    Stem.YI: Stem.BING,
    Stem.GENG: Stem.BING,
    Stem.BING: Stem.WU,
    Stem.XIN: Stem.WU,
    Stem.DING: Stem.GENG,
    Stem.REN: Stem.GENG,
    Stem.WU: Stem.REN,
    Stem.GUI: Stem.REN,
}


@pytest.mark.parametrize("year_stem", list(Stem))
def test_month_stem_rule(year_stem: Stem) -> None:
    first = calc.sexagenary(calc.month_index(year_stem, 0))
    assert first == (FIRST_MONTH_STEM[year_stem], Branch.YIN)
    stems = list(Stem)
    for sector in range(12):
        stem, branch = calc.sexagenary(calc.month_index(year_stem, sector))
        assert branch == list(Branch)[(2 + sector) % 12]
        assert stem == stems[(stems.index(FIRST_MONTH_STEM[year_stem]) + sector) % 10]


@pytest.mark.parametrize("day_stem", list(Stem))
def test_hour_stem_rule(day_stem: Stem) -> None:
    assert calc.sexagenary(calc.hour_index(day_stem, Branch.ZI)) == (
        FIRST_HOUR_STEM[day_stem],
        Branch.ZI,
    )
    stems = list(Stem)
    for b, branch in enumerate(Branch):
        stem, got = calc.sexagenary(calc.hour_index(day_stem, branch))
        assert got == branch
        assert stem == stems[(stems.index(FIRST_HOUR_STEM[day_stem]) + b) % 10]


def test_sexagenary_round_trip_and_invalid_pairs() -> None:
    for i in range(60):
        assert calc.sexagenary_index(*calc.sexagenary(i)) == i
    assert calc.sexagenary(0) == (Stem.JIA, Branch.ZI)
    assert calc.sexagenary(59) == (Stem.GUI, Branch.HAI)
    with pytest.raises(ValueError):
        calc.sexagenary_index(Stem.JIA, Branch.CHOU)
    with pytest.raises(ValueError):
        calc.sexagenary(60)


def test_days_advance_by_one() -> None:
    start = dt.date(1899, 12, 25)
    for k in range(800):
        a = calc.day_index(start + dt.timedelta(days=k))
        b = calc.day_index(start + dt.timedelta(days=k + 1))
        assert b == (a + 1) % 60


def test_hour_branches() -> None:
    assert calc.hour_branch(23.0) is Branch.ZI
    assert calc.hour_branch(0.5) is Branch.ZI
    assert calc.hour_branch(0.999999) is Branch.ZI
    assert calc.hour_branch(1.0) is Branch.CHOU
    assert calc.hour_branch(12.0) is Branch.WU
    assert calc.hour_branch(22.999) is Branch.HAI


def test_elements() -> None:
    assert STEM_ELEMENT[Stem.JIA].value == "wood" and STEM_ELEMENT[Stem.GUI].value == "water"
    assert (
        BRANCH_ELEMENT[Branch.CHEN].value == "earth" and BRANCH_ELEMENT[Branch.SI].value == "fire"
    )


# --------------------------------------------------------------------------
# Boundaries and conventions
# --------------------------------------------------------------------------


def test_lichun_2024_changes_year_and_month(service: ChineseChartService) -> None:
    # HKO: 立春 2024-02-04 16:27 HKT.
    before = service.calculate(_req(2024, 2, 4, 16, 25, tz="Asia/Hong_Kong"))
    after = service.calculate(_req(2024, 2, 4, 16, 29, tz="Asia/Hong_Kong"))
    assert (before.year.stem_character, before.year.branch_character) == ("癸", "卯")
    assert (after.year.stem_character, after.year.branch_character) == ("甲", "辰")
    assert before.month.branch_character == "丑" and after.month.branch_character == "寅"
    assert after.month.stem_character == "丙"  # 甲 year -> 丙寅


def test_day_boundary_conventions(service: ChineseChartService) -> None:
    zi = service.calculate(_req(2000, 1, 1, 23, 30, boundary=DayBoundary.ZI_HOUR_2300))
    mid = service.calculate(_req(2000, 1, 1, 23, 30, boundary=DayBoundary.MIDNIGHT))
    assert zi.day.sexagenary_index == (mid.day.sexagenary_index or 0) + 1
    assert zi.hour.branch is Branch.ZI and zi.hour.status is PillarStatus.SUCCESS
    assert mid.hour.status is PillarStatus.NOT_EVALUABLE
    assert mid.hour.reason is PillarReason.LATE_ZI_HOUR_STEM_UNRESOLVED
    early = service.calculate(_req(2000, 1, 2, 0, 30, boundary=DayBoundary.MIDNIGHT))
    assert early.day.sexagenary_index == zi.day.sexagenary_index
    assert early.hour.sexagenary_index == zi.hour.sexagenary_index


def test_time_basis_shifts_the_hour(service: ChineseChartService) -> None:
    # 13:05 Beijing clock time is 12:30:41 local mean solar time at 116.4 E: 午 not 未.
    clock = service.calculate(_req(2021, 6, 1, 13, 5, basis=TimeBasis.CLOCK_TIME))
    mean = service.calculate(_req(2021, 6, 1, 13, 5, basis=TimeBasis.LOCAL_MEAN_SOLAR_TIME))
    apparent = service.calculate(_req(2021, 6, 1, 13, 5, basis=TimeBasis.LOCAL_APPARENT_SOLAR_TIME))
    assert clock.hour.branch is Branch.WEI
    assert mean.hour.branch is Branch.WU
    assert apparent.hour.branch is Branch.WU
    assert mean.basis_local_datetime is not None and apparent.basis_local_datetime is not None
    # Equation of time on 1 June is about +2 minutes.
    delta = (apparent.basis_local_datetime - mean.basis_local_datetime).total_seconds()
    assert 60 < delta < 180


def test_unknown_time(service: ChineseChartService) -> None:
    plain = service.calculate(
        _req(
            2021, 6, 1, 12, 0, boundary=DayBoundary.MIDNIGHT, precision=ChineseTimePrecision.UNKNOWN
        )
    )
    assert plain.hour.reason is PillarReason.BIRTH_TIME_UNKNOWN
    assert plain.day.status is PillarStatus.SUCCESS
    assert plain.year.status is PillarStatus.SUCCESS
    zi = service.calculate(_req(2021, 6, 1, 12, 0, precision=ChineseTimePrecision.UNKNOWN))
    assert zi.day.reason is PillarReason.BIRTH_TIME_UNKNOWN
    on_term = service.calculate(
        _req(
            2024,
            2,
            4,
            9,
            0,
            tz="Asia/Hong_Kong",
            precision=ChineseTimePrecision.UNKNOWN,
            boundary=DayBoundary.MIDNIGHT,
        )
    )
    assert on_term.year.reason is PillarReason.SOLAR_TERM_ON_BIRTH_DATE
    assert on_term.month.reason is PillarReason.SOLAR_TERM_ON_BIRTH_DATE


def test_contract_and_determinism(service: ChineseChartService) -> None:
    a = service.calculate(_req(1987, 8, 15, 6, 45, tz="Asia/Kolkata"))
    b = service.calculate(_req(1987, 8, 15, 6, 45, tz="Asia/Kolkata"))
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
    assert a.profile_id == PROFILE_ID
    assert a.standards_version == CHINESE_STANDARDS_VERSION == "1.18.0"
    assert a.system == "chinese_bazi"
    assert "luck_cycles_require_sex_not_collected" in a.not_evaluated
    br = a.solar_term_bracket
    assert br.previous_utc < a.time_resolution.utc_datetime < br.next_utc
    assert {p.entry_id for p in a.provenance} >= {"prov.month", "prov.hour", "prov.day"}


def test_time_basis_and_day_boundary_are_required() -> None:
    with pytest.raises(ValidationError):
        ChineseChartRequest(  # type: ignore[call-arg]
            local_datetime=LocalDateTimeInput(year=2000, month=1, day=1, timezone="UTC"),
            location=BEIJING,
            time_precision=ChineseTimePrecision.EXACT,
        )


def test_module_imports_no_vedic_or_swisseph() -> None:
    forbidden = (
        "swisseph",
        "pandit_astro_engine.kundli",
        "pandit_astro_engine.nakshatra",
        "pandit_astro_engine.rashi",
        "pandit_astro_engine.western",
        "pandit_astro_engine.kp",
        "pandit_astro_engine.jaimini",
    )
    for path in SRC.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not any(name == f or name.startswith(f + ".") for f in forbidden), (
                    path.name,
                    name,
                )
