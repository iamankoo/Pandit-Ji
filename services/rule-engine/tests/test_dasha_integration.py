"""Rule engine + real astro-engine Dasha facts.

Skipped when `astro-engine` (and Swiss Ephemeris) is not installed, as in the
rule-engine's own CI job; it runs wherever both services are installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from pandit_rule_engine.engine import RuleEngine
from pandit_rule_engine.vocab import Body, Reason
from tests.helpers import rules_dir

pytest.importorskip("swisseph")
astro = pytest.importorskip("pandit_astro_engine")


def _request() -> Any:
    from pandit_astro_engine.models import (
        AstronomicalCalculationRequest,
        LocalDateTimeInput,
        Location,
    )

    return AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1990, month=6, day=15, hour=10, minute=0, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090),
    )


def _kundli_and_dasha() -> tuple[dict[str, Any], dict[str, Any]]:
    from pandit_astro_engine.dashas import DashaCalculationService

    request = _request()
    kundli = astro.KundliCalculationService().calculate(request).model_dump(mode="json")
    facts = DashaCalculationService().calculate(request).model_dump(mode="json")
    return kundli, facts


def test_real_dasha_facts_are_recorded_in_the_bundle_beside_the_kundli() -> None:
    kundli, facts = _kundli_and_dasha()
    bundle = RuleEngine.from_directory(rules_dir()).evaluate_kundli(kundli, facts)
    moon = next(p for p in kundli["planets"] if p["body"] == "moon")

    assert bundle.dasha is not None
    assert bundle.dasha.status == "success"
    assert bundle.dasha.starting_nakshatra == moon["nakshatra"]["nakshatra"]
    assert bundle.dasha.starting_pada == moon["nakshatra"]["pada"]
    assert bundle.dasha.starting_lord is Body(moon["nakshatra"]["lord"])
    assert len(bundle.dasha.periods) == len(facts["periods"]) > 800
    assert bundle.dasha.standards_version == "1.5.0"
    # Phase 5/6 evidence is untouched by the Phase 7 section.
    assert bundle.versions.calculation_standards_version == kundli["metadata"]["standards_version"]
    assert len(bundle.results) == 51
    assert all(result.reason is not Reason.REQUIRES_DASHA for result in bundle.results)


def test_bundle_with_real_dasha_facts_is_reproducible() -> None:
    kundli, facts = _kundli_and_dasha()
    engine = RuleEngine.from_directory(rules_dir())
    first = engine.evaluate_kundli(kundli, facts)
    second = engine.evaluate_kundli(kundli, facts)
    assert first.bundle_hash == second.bundle_hash
    assert first.canonical_json() == second.canonical_json()
    assert first.bundle_hash != engine.evaluate_kundli(kundli).bundle_hash
