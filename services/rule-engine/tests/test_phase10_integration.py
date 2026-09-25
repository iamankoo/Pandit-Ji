"""Phase 10 Panchang evidence and the Shadbala method policy, end to end
with real astro-engine results (skipped when astro-engine/Swiss Ephemeris is
not installed, as in the rule-engine's own CI job)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

pytest.importorskip("swisseph")

from pandit_astro_engine.kundli import KundliCalculationService  # noqa: E402
from pandit_astro_engine.models import (  # noqa: E402
    AstronomicalCalculationRequest,
    LocalDateTimeInput,
    Location,
)
from pandit_astro_engine.panchang import PanchangRequest, PanchangService  # noqa: E402
from pandit_astro_engine.shadbala import (  # noqa: E402
    DrekkanaReading,
    MoonPakshaReading,
    ShadbalaMethod,
    ShadbalaMethodRequest,
    ShadbalaMethodService,
    ShadbalaTimePrecision,
)

from pandit_rule_engine.engine import RuleEngine  # noqa: E402
from pandit_rule_engine.shadbala_gate import shadbala_for_rule  # noqa: E402

RULES = Path(__file__).parents[2] / "knowledge" / "rules"
LDT = LocalDateTimeInput(year=2001, month=3, day=9, hour=18, minute=45, timezone="Asia/Kolkata")
MUMBAI = Location(latitude=19.076, longitude=72.8777)


def test_panchang_and_shadbala_method_end_to_end() -> None:
    engine = RuleEngine.from_directory(RULES)
    kundli = (
        KundliCalculationService()
        .calculate(AstronomicalCalculationRequest(local_datetime=LDT, location=MUMBAI))
        .model_dump(mode="json")
    )
    panchang = PanchangService(None).daily(
        PanchangRequest(date=dt.date(2001, 3, 9), location=MUMBAI, timezone="Asia/Kolkata")
    )
    method = ShadbalaMethodService(None).calculate(
        ShadbalaMethodRequest(
            method=ShadbalaMethod.MODERN_RAMAN,
            local_datetime=LDT,
            location=MUMBAI,
            time_precision=ShadbalaTimePrecision.EXACT,
            drekkana_reading=DrekkanaReading.TEXT_ARTICLE_36,
            moon_paksha_reading=MoonPakshaReading.EIGHTH_DAY_WINDOW,
        )
    )
    plain = engine.evaluate_kundli(kundli)
    bundle = engine.evaluate_kundli(
        kundli,
        shadbala_facts=method.model_dump(mode="json"),
        panchang_facts=panchang.model_dump(mode="json"),
    )
    assert bundle.panchang is not None and bundle.panchang.status == "success"
    assert bundle.shadbala is not None and bundle.shadbala.method is not None
    assert bundle.shadbala.method.method == "MODERN_RAMAN"
    assert [r.model_dump() for r in plain.results] == [r.model_dump() for r in bundle.results]
    gate = shadbala_for_rule(bundle.shadbala, "jupiter")
    assert gate.status == "success" and gate.total_rupas is not None
