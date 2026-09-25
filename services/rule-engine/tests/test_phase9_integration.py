"""Phase 9 closure evidence, end to end with real astro-engine results
(skipped when astro-engine/Swiss Ephemeris is not installed, as in the
rule-engine's own CI job, following test_ashtakavarga_integration.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("swisseph")

from pandit_astro_engine.chinese import (  # noqa: E402
    ChineseChartRequest,
    ChineseChartService,
    ChineseTimePrecision,
    DayBoundary,
    TimeBasis,
)
from pandit_astro_engine.jaimini.facts import JaiminiFactsRequest, JaiminiFactsService  # noqa: E402
from pandit_astro_engine.jaimini.profiles import CHARA_KARAKA_SEVEN_BODY_ID  # noqa: E402
from pandit_astro_engine.kp import KpChartRequest, KpService, KpTimePrecision  # noqa: E402
from pandit_astro_engine.kundli import KundliCalculationService  # noqa: E402
from pandit_astro_engine.models import (  # noqa: E402
    AstronomicalCalculationRequest,
    LocalDateTimeInput,
    Location,
    NodeConvention,
)
from pandit_astro_engine.shadbala import (  # noqa: E402
    DrekkanaReading,
    MoonPakshaReading,
    RamanShadbalaRequest,
    RamanShadbalaService,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.tarot import SINGLE_CARD_ID, TarotDrawRequest, TarotService  # noqa: E402

from pandit_rule_engine.engine import RuleEngine  # noqa: E402

RULES = Path(__file__).parents[2] / "knowledge" / "rules"
LDT = LocalDateTimeInput(year=2001, month=3, day=9, hour=18, minute=45, timezone="Asia/Kolkata")
MUMBAI = Location(latitude=19.076, longitude=72.8777)


@pytest.fixture(scope="module")
def engine() -> RuleEngine:
    return RuleEngine.from_directory(RULES)


def _kundli() -> dict:  # type: ignore[type-arg]
    return (
        KundliCalculationService()
        .calculate(AstronomicalCalculationRequest(local_datetime=LDT, location=MUMBAI))
        .model_dump(mode="json")
    )


def test_all_phase9_sections_end_to_end(engine: RuleEngine) -> None:
    kp = KpService(None).calculate_chart(
        KpChartRequest(
            local_datetime=LDT,
            location=MUMBAI,
            time_precision=KpTimePrecision.EXACT,
            node_convention=NodeConvention.MEAN,
        )
    )
    shadbala = RamanShadbalaService(None).calculate(
        RamanShadbalaRequest(
            local_datetime=LDT,
            location=MUMBAI,
            time_precision=ShadbalaTimePrecision.EXACT,
            drekkana_reading=DrekkanaReading.TEXT_ARTICLE_36,
            moon_paksha_reading=MoonPakshaReading.EIGHTH_DAY_WINDOW,
        )
    )
    jaimini = JaiminiFactsService().calculate(
        JaiminiFactsRequest(
            local_datetime=LDT,
            location=MUMBAI,
            chara_karaka_profile_id=CHARA_KARAKA_SEVEN_BODY_ID,
            include_nodes_in_rashi_drishti=True,
        )
    )
    chinese = ChineseChartService(None).calculate(
        ChineseChartRequest(
            local_datetime=LDT,
            location=MUMBAI,
            time_precision=ChineseTimePrecision.EXACT,
            time_basis=TimeBasis.LOCAL_APPARENT_SOLAR_TIME,
            day_boundary=DayBoundary.MIDNIGHT,
        )
    )
    tarot = TarotService().draw(
        TarotDrawRequest(spread_id=SINGLE_CARD_ID, seed="integration", allow_reversals=False)
    )
    kundli = _kundli()
    bundle = engine.evaluate_kundli(
        kundli,
        kp_facts=kp.model_dump(mode="json"),
        shadbala_facts=shadbala.model_dump(mode="json"),
        jaimini_facts=jaimini.model_dump(mode="json"),
        chinese_facts=chinese.model_dump(mode="json"),
        tarot_layout=tarot.model_dump(mode="json"),
    )
    assert bundle.kp is not None and bundle.kp.kind == "natal"
    assert bundle.shadbala is not None
    assert bundle.shadbala.profile_id == "SHADBALA_RAMAN_GRAHA_BHAVA_BALAS"
    assert bundle.jaimini is not None and bundle.chinese is not None and bundle.tarot is not None
    plain = engine.evaluate_kundli(kundli)
    assert plain.bundle_hash != bundle.bundle_hash
    assert plain.results == bundle.results  # the new sections change no rule result
    again = engine.evaluate_kundli(
        kundli,
        kp_facts=kp.model_dump(mode="json"),
        shadbala_facts=shadbala.model_dump(mode="json"),
        jaimini_facts=jaimini.model_dump(mode="json"),
        chinese_facts=chinese.model_dump(mode="json"),
        tarot_layout=tarot.model_dump(mode="json"),
    )
    assert again.bundle_hash == bundle.bundle_hash
