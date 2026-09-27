"""Phase 11 compatibility and numerology evidence end to end with real
astro-engine results (skipped when astro-engine/Swiss Ephemeris is not
installed, as in the rule-engine's own CI job)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

pytest.importorskip("swisseph")

from pandit_astro_engine.compatibility import (  # noqa: E402
    CompatibilityProfileId,
    CompatibilityRequest,
    CompatibilityService,
    MatchParticipantInput,
)
from pandit_astro_engine.kundli import KundliCalculationService  # noqa: E402
from pandit_astro_engine.models import (  # noqa: E402
    AstronomicalCalculationRequest,
    LocalDateTimeInput,
    Location,
)
from pandit_astro_engine.numerology import (  # noqa: E402
    NameInput,
    NumerologyRequest,
    calculate_numerology,
)

from pandit_rule_engine.engine import RuleEngine  # noqa: E402

RULES = Path(__file__).parents[2] / "knowledge" / "rules"
DELHI = Location(latitude=28.6139, longitude=77.209)
A = LocalDateTimeInput(year=1990, month=5, day=10, hour=8, timezone="Asia/Kolkata")
B = LocalDateTimeInput(year=1992, month=11, day=3, hour=21, timezone="Asia/Kolkata")


def _kundli(local: LocalDateTimeInput) -> dict[str, object]:
    return (
        KundliCalculationService()
        .calculate(AstronomicalCalculationRequest(local_datetime=local, location=DELHI))
        .model_dump(mode="json")
    )


@pytest.mark.parametrize("profile", list(CompatibilityProfileId))
def test_compatibility_and_numerology_end_to_end(profile: CompatibilityProfileId) -> None:
    engine = RuleEngine.from_directory(RULES)
    bundle_a = engine.evaluate_kundli(_kundli(A))
    bundle_b = engine.evaluate_kundli(_kundli(B))
    kuja = engine.kuja_partner_comparison(bundle_a, bundle_b)
    facts = CompatibilityService().match(
        CompatibilityRequest(
            profile=profile,
            person_a=MatchParticipantInput(local_datetime=A, location=DELHI),
            person_b=MatchParticipantInput(local_datetime=B, location=DELHI),
            as_of_date=dt.date(2026, 9, 27),
            participant_consent_attested=True,
        )
    )
    numbers = calculate_numerology(
        NumerologyRequest(date_of_birth=dt.date(1990, 5, 10), name=NameInput(latin_spelling="Asha"))
    )
    bundle = engine.evaluate_kundli(
        _kundli(A),
        compatibility_facts=facts.model_dump(mode="json"),
        numerology_facts=numbers.model_dump(mode="json"),
        kuja_comparison=kuja,
    )
    assert bundle.compatibility is not None and bundle.compatibility.profile_id == profile.value
    assert bundle.compatibility.kuja_partner_comparison == kuja
    assert bundle.numerology is not None
    assert [r.model_dump() for r in bundle.results] == [r.model_dump() for r in bundle_a.results]
