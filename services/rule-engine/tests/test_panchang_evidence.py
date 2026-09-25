"""Phase 10 Panchang evidence section (standards v1.23.0, PC-30). Fixtures
were generated from real astro-engine `DailyPanchang` results; these tests
always run (no astro-engine import)."""

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
from pandit_rule_engine.panchang_evidence import panchang_evidence_from_facts
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset

_FIX = Path(__file__).parent / "fixtures" / "phase10"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIX / f"{name}.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_successful_day_is_recorded_verbatim() -> None:
    ev = panchang_evidence_from_facts(_load("panchang_delhi"))
    assert ev.status == "success" and ev.reason is None
    assert ev.profile_id == "PANCHANG_DRIK_CRC_1955_V1" and ev.standards_version == "1.23.0"
    assert ev.sunrise_convention == "crc_1955_centre_refraction_30"
    assert ev.vara == "thursday"
    kinds = {e.kind for e in ev.elements}
    assert kinds == {"tithi", "nakshatra", "yoga", "karana"}
    assert {m.saura_frame for m in ev.lunar_months} == {"lahiri_variable", "crc_fixed_23_15"}
    assert "choghadiya" in ev.not_implemented
    assert "prov.rahu_kalam" in ev.provenance_ids
    assert len(ev.facts_hash) == 64


def test_polar_day_is_recorded_as_not_evaluable() -> None:
    ev = panchang_evidence_from_facts(_load("panchang_polar"))
    assert ev.status == "not_evaluable" and ev.reason == "sunrise_not_occurring"
    assert ev.elements == () and ev.lunar_months == ()


def test_gap_between_elements_is_rejected() -> None:
    raw = _load("panchang_delhi")
    if len(raw["karanas"]) < 2:  # pragma: no cover - fixture always has two
        pytest.skip("needs two karanas")
    raw["karanas"][1]["start"]["julian_day_ut"] += 0.01
    with pytest.raises(FactsError, match="contiguous"):
        panchang_evidence_from_facts(raw)


def test_list_must_start_at_sunrise_and_end_at_next_sunrise() -> None:
    raw = _load("panchang_delhi")
    raw["tithis"][0]["current_at_sunrise"] = False
    with pytest.raises(FactsError, match="at sunrise"):
        panchang_evidence_from_facts(raw)
    raw = _load("panchang_delhi")
    raw["yogas"][-1]["current_at_next_sunrise"] = False
    with pytest.raises(FactsError, match="next sunrise"):
        panchang_evidence_from_facts(raw)


def test_status_invariants() -> None:
    raw = _load("panchang_polar")
    raw["reason"] = None
    with pytest.raises(FactsError, match="reason"):
        panchang_evidence_from_facts(raw)
    raw = _load("panchang_delhi")
    raw["lunar_months"] = []
    with pytest.raises(FactsError, match="lunar month"):
        panchang_evidence_from_facts(raw)
    raw = _load("panchang_delhi")
    raw["sunset"] = {"status": "circumpolar_no_event"}
    with pytest.raises(FactsError, match="sunset"):
        panchang_evidence_from_facts(raw)
    with pytest.raises(FactsError):
        panchang_evidence_from_facts([])  # type: ignore[arg-type]


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


def test_section_is_omitted_when_absent(ruleset) -> None:  # type: ignore[no-untyped-def]
    plain = _bundle(ruleset)
    explicit_none = _bundle(ruleset, panchang=None)
    assert plain.bundle_hash == explicit_none.bundle_hash
    assert "panchang" not in json.loads(plain.canonical_json())


def test_section_changes_the_hash_but_not_the_rule_results(ruleset) -> None:  # type: ignore[no-untyped-def]
    plain = _bundle(ruleset)
    with_day = _bundle(ruleset, panchang=panchang_evidence_from_facts(_load("panchang_delhi")))
    assert plain.bundle_hash != with_day.bundle_hash
    assert [r.model_dump() for r in plain.results] == [r.model_dump() for r in with_day.results]
    again = _bundle(ruleset, panchang=panchang_evidence_from_facts(_load("panchang_delhi")))
    assert again.bundle_hash == with_day.bundle_hash


def test_facts_hash_tracks_the_input() -> None:
    raw = _load("panchang_delhi")
    a = panchang_evidence_from_facts(raw).facts_hash
    changed = copy.deepcopy(raw)
    changed["warnings"] = ["x"]
    assert panchang_evidence_from_facts(changed).facts_hash != a
