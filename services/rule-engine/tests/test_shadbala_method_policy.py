"""Shadbala method policy in the rule engine (standards v1.22.0, SM-09 and
SM-10). Fixtures are real `ShadbalaMethodResult` outputs of astro-engine
(Raman's Standard Horoscope instant); these tests always run."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine._version import __version__
from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.bundle import build_bundle
from pandit_rule_engine.evaluator import evaluate_ruleset
from pandit_rule_engine.phase9_evidence import shadbala_evidence_from_facts
from pandit_rule_engine.shadbala_gate import ShadbalaGateReason, shadbala_for_rule
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset

_FIX = Path(__file__).parent / "fixtures" / "phase9"
SEVEN = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn")


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIX / f"{name}.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


# --------------------------------------------------------------------------
# Adapter: the method envelope is recorded and checked
# --------------------------------------------------------------------------


def test_method_identifiers_are_preserved() -> None:
    raman = shadbala_evidence_from_facts(_load("shadbala_method_raman_configured"))
    bphs = shadbala_evidence_from_facts(_load("shadbala_method_bphs"))
    assert raman.method is not None and bphs.method is not None
    assert (raman.method.method, raman.profile_id) == (
        "MODERN_RAMAN",
        "SHADBALA_RAMAN_GRAHA_BHAVA_BALAS",
    )
    assert (bphs.method.method, bphs.profile_id) == (
        "BPHS_VERSE_REFERENCE",
        "SHADBALA_BPHS_SANTHANAM_27_VERSE",
    )
    assert raman.method.method_version == bphs.method.method_version == "1.0.0"
    assert raman.method.is_default_user_facing_method is True
    assert bphs.method.is_default_user_facing_method is False
    assert raman.method.source_ids == ("SRC-RAMAN-GRAHA-BHAVA-BALAS",)
    assert bphs.method.source_ids == ("SRC-BPHS-SANTHANAM-1984",)
    assert raman.readings == {
        "RAMAN_DREKKANA_ORDER": "worked_example_12",
        "RAMAN_MOON_BENEFIC_RULE": "waxing_half",
    }
    assert bphs.readings == {}
    assert raman.method.total_status == "complete"
    assert bphs.method.total_status == "partial" and not bphs.method.method_produces_total


def test_open_choice_is_recorded_with_its_alternatives() -> None:
    ev = shadbala_evidence_from_facts(_load("shadbala_method_raman_open"))
    assert ev.method is not None
    assert ev.method.unresolved_choices == ("RAMAN_DREKKANA_ORDER",)
    assert ev.readings == {}
    assert len(ev.method.alternatives) == 4
    drek = ev.method.choices[0]
    assert drek.selection == "not_selected" and drek.affected == (("venus", "drekkana"),)


def test_a_method_cannot_carry_the_other_methods_profile() -> None:
    raw = _load("shadbala_method_raman_configured")
    raw["profile_id"] = "SHADBALA_BPHS_SANTHANAM_27_VERSE"
    with pytest.raises(FactsError, match="never mixed"):
        shadbala_evidence_from_facts(raw)
    raw = _load("shadbala_method_bphs")
    raw["method"] = "MODERN_RAMAN"
    with pytest.raises(FactsError, match="never mixed"):
        shadbala_evidence_from_facts(raw)


def test_bphs_reference_cannot_claim_a_total() -> None:
    raw = _load("shadbala_method_bphs")
    raw["method_produces_total"] = True
    with pytest.raises(FactsError, match="produces no total"):
        shadbala_evidence_from_facts(raw)


def test_hidden_resolution_of_an_open_choice_is_rejected() -> None:
    raw = _load("shadbala_method_raman_open")
    raw["unresolved_choices"] = []
    with pytest.raises(FactsError, match="open material choices"):
        shadbala_evidence_from_facts(raw)
    raw = _load("shadbala_method_raman_open")
    venus = next(t for t in raw["totals"] if t["body"] == "venus")
    venus.update(status="complete", total_rupas=5.5, missing_components=[])
    with pytest.raises(FactsError):
        shadbala_evidence_from_facts(raw)


def test_total_status_must_agree_with_planet_totals() -> None:
    raw = _load("shadbala_method_raman_open")
    raw["total_status"] = "complete"
    with pytest.raises(FactsError, match="total_status"):
        shadbala_evidence_from_facts(raw)


def test_profile_fact_sections_serialize_as_before() -> None:
    """Sections built from profile facts carry no method key (EV-02 hashes)."""
    ev = shadbala_evidence_from_facts(_load("shadbala_raman"))
    assert ev.method is None
    assert "method" not in ev.model_dump(mode="json")


# --------------------------------------------------------------------------
# Gate: MODERN_RAMAN only when every condition holds
# --------------------------------------------------------------------------


def test_gate_success_for_a_configured_complete_raman_result() -> None:
    ev = shadbala_evidence_from_facts(_load("shadbala_method_raman_configured"))
    for body in SEVEN:
        got = shadbala_for_rule(ev, body)
        assert got.status == "success" and got.reason is None
        assert got.total_rupas is not None and got.total_rupas > 0
        assert (got.method, got.method_version) == ("MODERN_RAMAN", "1.0.0")


@pytest.mark.parametrize(
    ("fixture", "body", "reason"),
    [
        (None, "sun", ShadbalaGateReason.EVIDENCE_ABSENT),
        ("shadbala_raman", "sun", ShadbalaGateReason.METHOD_NOT_RECORDED),
        ("shadbala_bphs", "sun", ShadbalaGateReason.METHOD_NOT_RECORDED),
        ("shadbala_method_bphs", "sun", ShadbalaGateReason.METHOD_NOT_MODERN_RAMAN),
        ("shadbala_method_raman_configured", "rahu", ShadbalaGateReason.BODY_NOT_COVERED),
        ("shadbala_method_raman_unknown_time", "sun", ShadbalaGateReason.BIRTH_TIME_NOT_EXACT),
        ("shadbala_method_raman_open", "venus", ShadbalaGateReason.METHODOLOGY_CHOICE_UNRESOLVED),
    ],
)
def test_gate_not_evaluable_reasons(fixture: str | None, body: str, reason: str) -> None:
    ev = None if fixture is None else shadbala_evidence_from_facts(_load(fixture))
    got = shadbala_for_rule(ev, body)
    assert got.status == "not_evaluable" and got.reason is reason
    assert got.total_rupas is None


def test_gate_open_choice_blocks_only_the_affected_planet() -> None:
    ev = shadbala_evidence_from_facts(_load("shadbala_method_raman_open"))
    venus = shadbala_for_rule(ev, "venus")
    assert venus.detail == "RAMAN_DREKKANA_ORDER changes drekkana"
    sun = shadbala_for_rule(ev, "sun")
    configured = shadbala_for_rule(
        shadbala_evidence_from_facts(_load("shadbala_method_raman_configured")), "sun"
    )
    assert sun.status == "success" and sun.total_rupas == configured.total_rupas


def test_gate_partial_total_for_another_reason() -> None:
    raw = _load("shadbala_method_raman_configured")
    doc = copy.deepcopy(raw)
    sun = next(p for p in doc["planets"] if p["body"] == "sun")
    for c in sun["components"]:
        if c["component"] == "hora":
            c.update(status="not_evaluable", virupas=None, reason="sunrise_unavailable")
        if c["component"] in ("kala_total", "shadbala_total"):
            c.update(status="not_evaluable", virupas=None, reason="component_not_evaluable")
    total = next(t for t in doc["totals"] if t["body"] == "sun")
    total.update(status="partial", total_rupas=None, missing_components=["hora"])
    doc["total_status"] = "partial"
    got = shadbala_for_rule(shadbala_evidence_from_facts(doc), "sun")
    assert got.reason is ShadbalaGateReason.TOTAL_PARTIAL and got.detail == "missing: hora"


# --------------------------------------------------------------------------
# Bundles and existing behaviour
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


def test_method_section_changes_the_bundle_but_not_the_rule_results(ruleset) -> None:  # type: ignore[no-untyped-def]
    plain = _bundle(ruleset)
    with_method = _bundle(
        ruleset,
        shadbala=shadbala_evidence_from_facts(_load("shadbala_method_raman_configured")),
    )
    assert plain.bundle_hash != with_method.bundle_hash
    assert [r.model_dump() for r in plain.results] == [r.model_dump() for r in with_method.results]
    dumped = json.loads(with_method.canonical_json())
    assert dumped["shadbala"]["method"]["method"] == "MODERN_RAMAN"


def test_method_sections_are_deterministic(ruleset) -> None:  # type: ignore[no-untyped-def]
    a = _bundle(ruleset, shadbala=shadbala_evidence_from_facts(_load("shadbala_method_raman_open")))
    b = _bundle(ruleset, shadbala=shadbala_evidence_from_facts(_load("shadbala_method_raman_open")))
    assert a.bundle_hash == b.bundle_hash
