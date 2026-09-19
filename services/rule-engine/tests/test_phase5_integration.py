"""The rule engine consumes a real Phase 5 Kundli.

Skipped when `astro-engine` (and its Swiss Ephemeris dependency) is not
installed, as in the rule-engine's own CI job; it runs wherever both
services are installed. It proves the adapter matches Phase 5's actual JSON
shape and that Phase 5 standards versions are carried through unchanged.
"""

from __future__ import annotations

import pytest

from pandit_rule_engine.engine import RuleEngine
from tests.helpers import rules_dir

pytest.importorskip("swisseph")
astro = pytest.importorskip("pandit_astro_engine")


def _kundli() -> dict[str, object]:
    from pandit_astro_engine.models import (
        AstronomicalCalculationRequest,
        LocalDateTimeInput,
        Location,
    )

    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=1, day=1, hour=6, minute=30, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090),
    )
    kundli = astro.KundliCalculationService().calculate(request)
    return kundli.model_dump(mode="json")


def test_real_kundli_is_evaluated_and_keeps_phase5_standards_version() -> None:
    kundli = _kundli()
    bundle = RuleEngine.from_directory(rules_dir()).evaluate_kundli(kundli)
    assert bundle.versions.calculation_standards_version == kundli["metadata"]["standards_version"]  # type: ignore[index]
    assert bundle.versions.rule_standards_version == "1.4.0"
    assert len(bundle.results) == 51
    assert bundle.chart.calculation.ayanamsa == "lahiri"
    assert bundle.chart.calculation.house_system == "vedic_whole_sign"
    assert bundle.chart.calculation.timezone == "Asia/Kolkata"
    assert {planet.body.value for planet in bundle.chart.planets} >= {
        "sun",
        "moon",
        "saturn",
        "ketu",
    }


def test_real_kundli_evaluation_is_reproducible() -> None:
    kundli = _kundli()
    engine = RuleEngine.from_directory(rules_dir())
    assert engine.evaluate_kundli(kundli).bundle_hash == engine.evaluate_kundli(kundli).bundle_hash
