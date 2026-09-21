"""Rule engine + real astro-engine transit facts.

Skipped when `astro-engine` (and Swiss Ephemeris) is not installed, as in the
rule-engine's own CI job; it runs wherever both services are installed.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from pandit_rule_engine.engine import RuleEngine
from pandit_rule_engine.vocab import Body, Reason
from tests.helpers import rules_dir

pytest.importorskip("swisseph")
astro = pytest.importorskip("pandit_astro_engine")

UTC = dt.timezone.utc


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


def _kundli_and_transit() -> tuple[dict[str, Any], dict[str, Any]]:
    from pandit_astro_engine.transits import (
        NatalReference,
        TransitCalculationService,
        TransitConfiguration,
    )

    request = _request()
    kundli_model = astro.KundliCalculationService().calculate(request)
    facts = TransitCalculationService().calculate(
        __import__("pandit_astro_engine.transits", fromlist=["TransitRequest"]).TransitRequest(
            natal=NatalReference.from_kundli(kundli_model),
            config=TransitConfiguration(include_sade_sati=True),
            at_utc=dt.datetime(2026, 9, 21, 12, tzinfo=UTC),
            window_start_utc=dt.datetime(2026, 1, 1, tzinfo=UTC),
            window_end_utc=dt.datetime(2027, 1, 1, tzinfo=UTC),
        )
    )
    return kundli_model.model_dump(mode="json"), facts.model_dump(mode="json")


def test_real_transit_facts_are_recorded_in_the_bundle_beside_the_kundli() -> None:
    kundli, facts = _kundli_and_transit()
    bundle = RuleEngine.from_directory(rules_dir()).evaluate_kundli(kundli, None, facts)
    moon = next(p for p in kundli["planets"] if p["body"] == "moon")

    assert bundle.transit is not None and bundle.dasha is None
    assert bundle.transit.status == "success"
    assert bundle.transit.natal is not None
    assert bundle.transit.natal.moon_sign == moon["rashi"]
    assert bundle.transit.standards_version == "1.6.0"
    assert bundle.transit.window is not None
    assert bundle.transit.window.event_count == len(facts["window"]["events"]) > 20
    assert bundle.transit.sade_sati is not None
    # Phase 5/6 evidence is untouched by the Phase 8 section.
    assert bundle.versions.calculation_standards_version == kundli["metadata"]["standards_version"]
    assert len(bundle.results) == 51
    assert all(result.reason is not Reason.REQUIRES_DASHA for result in bundle.results)


def test_the_bundle_with_real_transit_facts_is_reproducible() -> None:
    kundli, facts = _kundli_and_transit()
    engine = RuleEngine.from_directory(rules_dir())
    first = engine.evaluate_kundli(kundli, None, facts)
    second = engine.evaluate_kundli(kundli, None, facts)
    assert first.bundle_hash == second.bundle_hash
    without = engine.evaluate_kundli(kundli)
    assert without.transit is None and without.bundle_hash != first.bundle_hash
    assert Body.MOON in {state.body for state in first.transit.snapshot.states}  # type: ignore[union-attr]
