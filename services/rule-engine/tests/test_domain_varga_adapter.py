"""The Phase 17 Varga adapter reads the eight approved divisional charts and nothing else.

The Phase 5 Kundli carries sixteen divisional charts; the owner approved only the eight of
the locked BPHS mappings (D2, D3, D7, D9, D10, D12, D20, D24) for the evaluation container.
D4 and every other chart are never read, parsed, hashed or offered to a rule. The adapter is
read-only; Phase 5 and Phase 6 are untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pandit_contracts.domain import LifeDomain

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.domain import evaluate_domain, load_domain_ruleset, varga_from_kundli
from pandit_rule_engine.domain.schema import LOCKED_VARGAS
from pandit_rule_engine.facts import ChartFacts
from pandit_rule_engine.loader import load_ruleset
from tests.domain_helpers import (
    BASE,
    DOMAIN_RULES_DIR,
    VEDIC_RULES_DIR,
    evaluate,
    kundli,
    varga_of,
)

APPROVED = {2, 3, 7, 9, 10, 12, 20, 24}
ALL_SIXTEEN = (1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60)
PHASE6_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"


def _signs(sign: str = "taurus") -> dict[str, str]:
    return {b: sign for b in BASE}


def test_the_approved_set_is_exactly_the_eight_locked_charts() -> None:
    assert set(LOCKED_VARGAS) == APPROVED


def test_only_the_eight_approved_charts_are_materialized_from_a_full_kundli() -> None:
    chart = kundli("aries", BASE, {n: _signs() for n in ALL_SIXTEEN})
    assert len(chart["charts"]) == 16
    got = varga_from_kundli(chart)
    assert got is not None
    assert set(got.charts) == APPROVED
    for unapproved in (1, 4, 16, 27, 30, 40, 45, 60):
        assert got.chart(unapproved) is None


def test_d4_is_never_consumed_even_when_it_is_the_only_chart() -> None:
    only_d4 = varga_from_kundli(kundli("aries", BASE, {4: _signs()}))
    assert only_d4 is not None and only_d4.charts == {}
    result = evaluate(LifeDomain.CHILDREN, varga=only_d4)
    d7 = next(r for r in result.rules if r.rule_id == "DOM_CHILDREN_VARGA_D7_B7")
    assert d7.status.value == "INSUFFICIENT_EVIDENCE"
    assert d7.reason is not None and d7.reason.value == "MISSING_VARGA_EVIDENCE"


def test_an_unapproved_chart_is_not_parsed_and_cannot_change_the_result() -> None:
    base = kundli("aries", BASE, {n: _signs() for n in APPROVED})
    with_d4 = kundli("aries", BASE, {**{n: _signs() for n in APPROVED}, 4: _signs("leo")})
    garbage = kundli("aries", BASE, {n: _signs() for n in APPROVED})
    garbage["charts"]["4"] = {"varga": 4, "ascendant_rashi": "not-a-sign", "planets": "x"}
    reference = varga_from_kundli(base)
    assert reference is not None
    for other in (with_d4, garbage):  # a malformed D4 does not even raise: it is never read
        got = varga_from_kundli(other)
        assert got is not None and got.facts_hash == reference.facts_hash
    broken_approved = kundli("aries", BASE, {n: _signs() for n in APPROVED})
    broken_approved["charts"]["9"]["ascendant_rashi"] = "not-a-sign"
    with pytest.raises(FactsError):
        varga_from_kundli(broken_approved)


def test_no_fact_ever_references_an_unapproved_chart() -> None:
    chart = kundli("aries", BASE, {n: _signs() for n in ALL_SIXTEEN})
    container = varga_from_kundli(chart)
    ruleset = load_domain_ruleset(DOMAIN_RULES_DIR)
    seen: set[int] = set()
    for domain in LifeDomain:
        result = evaluate(domain, varga=container, rs=ruleset)
        for fact in result.facts:
            seen.update(fact.varga_refs)
    assert seen and seen <= APPROVED


def test_a_kundli_without_charts_gives_no_container() -> None:
    assert varga_from_kundli(kundli()) is None
    assert varga_of().chart(9) is not None


def test_a_real_phase_5_kundli_yields_exactly_the_eight_with_the_engines_own_values() -> None:
    astro = pytest.importorskip("pandit_astro_engine")
    from pandit_astro_engine.models import (
        AstronomicalCalculationRequest,
        LocalDateTimeInput,
        Location,
    )

    from pandit_rule_engine.vocab import Body

    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1990, month=6, day=15, hour=10, minute=0, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090),
    )
    model = astro.KundliCalculationService().calculate(request)
    assert set(model.charts) >= APPROVED | {1, 4}  # the engine itself computes more
    got = varga_from_kundli(model.model_dump(mode="json"))
    assert got is not None and set(got.charts) == APPROVED
    for number in APPROVED:
        engine_chart = model.charts[number]
        mine = got.charts[number]
        assert mine.ascendant.value == engine_chart.ascendant_rashi.value
        for planet in engine_chart.planets:
            assert mine.planets[Body(planet.body.value)].value == planet.rashi.value


def test_phase_6_chart_facts_stay_d1_only_and_the_phase_6_hash_is_unchanged() -> None:
    assert set(ChartFacts.model_fields) == {"lagna_sign", "planets", "sign_lords", "snapshot"}
    assert not any("varga" in f or "divisional" in f for f in ChartFacts.model_fields)
    ruleset = load_ruleset(VEDIC_RULES_DIR)
    assert ruleset.content_hash == PHASE6_HASH and len(ruleset.rules) == 51


def test_the_adapter_source_has_no_calculation_or_io() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "src" / "pandit_rule_engine" / "domain" / "inputs.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("swisseph", "pandit_astro_engine", "open(", "requests", "datetime", "random"):
        assert forbidden not in source


def test_evaluate_domain_signature_still_takes_the_container_only() -> None:
    import inspect

    assert "varga" in inspect.signature(evaluate_domain).parameters
