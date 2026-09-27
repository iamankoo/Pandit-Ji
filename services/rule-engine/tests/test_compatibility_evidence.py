"""Phase 11 compatibility and numerology evidence (`docs/ASTROLOGY_STANDARDS.md`
v1.25.0, EV-11 to EV-16). Fixtures are real astro-engine outputs
(`tests/fixtures/phase11`); the adapters only record and validate them."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine._version import __version__
from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.bundle import build_bundle
from pandit_rule_engine.compatibility_evidence import (
    compatibility_evidence_from_facts,
    kuja_partner_comparison,
    numerology_evidence_from_facts,
)
from pandit_rule_engine.engine import RuleEngine
from pandit_rule_engine.evaluator import evaluate_ruleset
from tests.chart_builder import chart, full_placements, kundli_dict
from tests.golden_cases import MARS_FREE_OF_BENEFIC_LINK_LIBRA, SAMPLE_A
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset

FIXTURES = Path(__file__).parent / "fixtures" / "phase11"
RULES = Path(__file__).parents[2] / "knowledge" / "rules"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text("utf-8"))


# --------------------------------------------------------------------------
# Compatibility
# --------------------------------------------------------------------------


def test_ashtakoot_is_recorded_verbatim() -> None:
    raw = _load("ashtakoot_partial")
    evidence = compatibility_evidence_from_facts(raw)
    assert evidence.system == "NORTH_INDIAN_ASHTAKOOT"
    assert [f.factor_id for f in evidence.factors] == [f["factor_id"] for f in raw["factors"]]
    assert evidence.ashtakoot_total is not None and evidence.ashtakoot_total.points is None
    assert evidence.provenance_ids and evidence.not_implemented
    assert evidence.kuja_partner_comparison is None


def test_porutham_and_blocked_results_are_recorded() -> None:
    porutham = compatibility_evidence_from_facts(_load("porutham_partial"))
    assert porutham.system == "SOUTH_INDIAN_TEN_PORUTHAM"
    assert porutham.porutham_summary is not None
    blocked = compatibility_evidence_from_facts(_load("ashtakoot_blocked_minor"))
    assert blocked.status == "blocked_by_policy" and not blocked.factors


def _reject(raw: dict[str, Any], match: str) -> None:
    with pytest.raises(FactsError, match=match):
        compatibility_evidence_from_facts(raw)


def test_a_partial_ashtakoot_cannot_carry_a_36_point_total() -> None:
    raw = _load("ashtakoot_partial")
    raw["ashtakoot_total"].update(status="evaluated", points=30.0, reason=None)
    _reject(raw, "partial set")


def test_a_complete_ashtakoot_total_must_equal_the_sum() -> None:
    raw = _load("ashtakoot_partial")
    for factor in raw["factors"]:
        if factor["status"] != "evaluated":
            factor.update(status="evaluated", reason=None, points=0.0, role_invariant=None)
            factor["role_dependent"] = False
    total = sum(f["points"] for f in raw["factors"])
    raw["ashtakoot_total"].update(status="evaluated", points=total + 1, reason=None)
    _reject(raw, "sum")
    raw["ashtakoot_total"]["points"] = total
    assert compatibility_evidence_from_facts(raw).ashtakoot_total.points == total  # type: ignore[union-attr]


def test_the_two_systems_cannot_be_mixed() -> None:
    raw = _load("ashtakoot_partial")
    raw["system"] = "SOUTH_INDIAN_TEN_PORUTHAM"
    _reject(raw, "mismatch")
    raw = _load("porutham_partial")
    raw["factors"][4]["points"] = 1.0
    _reject(raw, "points")
    raw = _load("ashtakoot_partial")
    raw["factors"] = raw["factors"][:-1]
    _reject(raw, "eight kutas")


def test_a_blocked_result_cannot_carry_facts() -> None:
    raw = _load("ashtakoot_blocked_minor")
    raw["placements"] = _load("ashtakoot_partial")["placements"]
    _reject(raw, "carries no facts")


def test_factor_invariants() -> None:
    raw = _load("ashtakoot_partial")
    vashya = next(f for f in raw["factors"] if f["factor_id"] == "vashya")
    vashya["points"] = 2.0
    _reject(raw, "no outcome")
    raw = _load("ashtakoot_partial")
    varna = next(f for f in raw["factors"] if f["factor_id"] == "varna")
    varna["role_invariant"] = False
    _reject(raw, "role-invariant")


# --------------------------------------------------------------------------
# Numerology
# --------------------------------------------------------------------------


def test_numerology_keeps_numbers_not_name_or_date() -> None:
    raw = _load("numerology_chaldean")
    evidence = numerology_evidence_from_facts(raw)
    dumped = evidence.model_dump_json()
    assert "Lloyd" not in dumped and "LLOYD" not in dumped and "1990" not in dumped
    assert evidence.date_supplied and evidence.name_number.word_count == 2
    assert evidence.name_number.reduction is not None
    assert evidence.name_number.reduction.value == 7
    changed = copy.deepcopy(raw)
    changed["name_number"]["input_spelling"] = "Other"
    assert numerology_evidence_from_facts(changed).facts_hash != evidence.facts_hash


def test_numerology_master_number_invariants() -> None:
    kept = numerology_evidence_from_facts(_load("numerology_pythagorean_retain"))
    assert kept.moolank.reduction is not None and kept.moolank.reduction.value == 11
    raw = _load("numerology_pythagorean_retain")
    raw["master_number_policy"] = "none"
    with pytest.raises(FactsError, match="master"):
        numerology_evidence_from_facts(raw)
    raw = _load("numerology_chaldean")
    raw["master_number_policy"] = "retain_11_22"
    with pytest.raises(FactsError, match="Chaldean"):
        numerology_evidence_from_facts(raw)
    raw = _load("numerology_chaldean")
    raw["system"] = "pythagorean"
    with pytest.raises(FactsError, match="mismatch"):
        numerology_evidence_from_facts(raw)


# --------------------------------------------------------------------------
# Bundle
# --------------------------------------------------------------------------


@pytest.fixture
def ruleset(tmp_path: Path):  # type: ignore[no-untyped-def]
    from pandit_rule_engine.loader import load_ruleset

    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "bphs/a.yaml": rule_doc(rule_id="TEST_A", profile="TEST_A"),
        },
    )
    return load_ruleset(tmp_path)


def _bundle(ruleset, **sections):  # type: ignore[no-untyped-def]
    facts = chart("aries", full_placements())
    return build_bundle(
        ruleset=ruleset,
        facts=facts,
        results=evaluate_ruleset(ruleset, facts, StubDerived()),
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
        **sections,
    )


def test_sections_are_omitted_when_absent(ruleset) -> None:  # type: ignore[no-untyped-def]
    plain = _bundle(ruleset)
    explicit = _bundle(ruleset, compatibility=None, numerology=None)
    assert plain.bundle_hash == explicit.bundle_hash
    body = json.loads(plain.canonical_json())
    assert "compatibility" not in body and "numerology" not in body


def test_sections_change_the_hash_but_not_the_rule_results(ruleset) -> None:  # type: ignore[no-untyped-def]
    plain = _bundle(ruleset)
    full = _bundle(
        ruleset,
        compatibility=compatibility_evidence_from_facts(_load("ashtakoot_partial")),
        numerology=numerology_evidence_from_facts(_load("numerology_chaldean")),
    )
    assert plain.bundle_hash != full.bundle_hash
    assert [r.model_dump() for r in plain.results] == [r.model_dump() for r in full.results]
    again = _bundle(
        ruleset,
        compatibility=compatibility_evidence_from_facts(_load("ashtakoot_partial")),
        numerology=numerology_evidence_from_facts(_load("numerology_chaldean")),
    )
    assert again.bundle_hash == full.bundle_hash


# --------------------------------------------------------------------------
# Kuja (Mangal) partner comparison from the locked Phase 6 rules
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine() -> RuleEngine:
    return RuleEngine.from_directory(RULES)


def _kundli_bundle(engine: RuleEngine, placements: dict[str, Any]):  # type: ignore[no-untyped-def]
    return engine.evaluate_kundli(kundli_dict("aries", placements))


def test_both_partners_detected_meets_the_bphs_v49_condition(engine: RuleEngine) -> None:
    a = _kundli_bundle(engine, MARS_FREE_OF_BENEFIC_LINK_LIBRA)
    b = _kundli_bundle(engine, MARS_FREE_OF_BENEFIC_LINK_LIBRA)
    comparison = engine.kuja_partner_comparison(a, b)
    bphs = [r for r in comparison.readings if r.rule_id.startswith("BPHS")]
    assert bphs and all(r.partner_condition == "source_condition_met" for r in bphs)
    jp = [r for r in comparison.readings if r.rule_id == "JP_KUJA_DOSHA"]
    assert jp and all(r.partner_condition == "not_specified_by_source" for r in jp)


def test_one_partner_only_does_not_meet_it(engine: RuleEngine) -> None:
    a = _kundli_bundle(engine, MARS_FREE_OF_BENEFIC_LINK_LIBRA)
    b = _kundli_bundle(engine, SAMPLE_A | {"mars": ("gemini", 5.0), "mercury": ("virgo", 3.0)})
    comparison = engine.kuja_partner_comparison(a, b)
    bphs = [r for r in comparison.readings if r.rule_id.startswith("BPHS")]
    assert {r.partner_condition for r in bphs} == {"source_condition_not_met"}


def test_comparison_needs_the_same_ruleset(engine: RuleEngine) -> None:
    a = _kundli_bundle(engine, MARS_FREE_OF_BENEFIC_LINK_LIBRA)
    with pytest.raises(FactsError, match="different rulesets"):
        kuja_partner_comparison(a.results, a.results, "x", "y")
    with pytest.raises(FactsError, match="missing"):
        kuja_partner_comparison((), a.results, "x", "x")


def test_comparison_is_recorded_in_the_compatibility_section(engine: RuleEngine) -> None:
    a = _kundli_bundle(engine, MARS_FREE_OF_BENEFIC_LINK_LIBRA)
    comparison = engine.kuja_partner_comparison(a, a)
    bundle = engine.evaluate_kundli(
        kundli_dict("aries", MARS_FREE_OF_BENEFIC_LINK_LIBRA),
        compatibility_facts=_load("ashtakoot_partial"),
        numerology_facts=_load("numerology_chaldean"),
        kuja_comparison=comparison,
    )
    assert bundle.compatibility is not None
    assert bundle.compatibility.kuja_partner_comparison == comparison
    assert bundle.numerology is not None
    phase6 = {r.rule_id: r.status for r in a.results}
    assert {r.rule_id: r.status for r in bundle.results} == phase6  # Phase 6 unchanged
