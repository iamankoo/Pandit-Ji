"""Phase 7 -> Phase 6 contract: Dasha facts recorded in the EvidenceBundle.

The fixtures are the JSON form of astro-engine `DashaFacts` produced once by
the pure Vimshottari calculator (Moon 123.4 degrees, birth 1990-06-15 04:30
UTC, depth 2, 40-year horizon; and an approximate-time result that is
NOT_EVALUABLE). The rule engine reads them without importing astro-engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine._version import __version__
from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.bundle import EvidenceBundle, build_bundle
from pandit_rule_engine.dasha_evidence import DashaEvidence, dasha_evidence_from_facts
from pandit_rule_engine.evaluator import evaluate_ruleset
from pandit_rule_engine.loader import Ruleset, load_ruleset
from pandit_rule_engine.vocab import Body, Reason
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset

_FIXTURES = Path(__file__).parent / "fixtures" / "dasha"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _copy(raw: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(raw))  # type: ignore[no-any-return]


@pytest.fixture()
def ruleset(tmp_path: Path) -> Ruleset:
    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "bphs/a.yaml": rule_doc(rule_id="TEST_A", profile="TEST_A"),
        },
    )
    return load_ruleset(tmp_path)


def _bundle(ruleset: Ruleset, dasha: DashaEvidence | None) -> EvidenceBundle:
    facts = chart("aries", full_placements())
    return build_bundle(
        ruleset=ruleset,
        facts=facts,
        results=evaluate_ruleset(ruleset, facts, StubDerived()),
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
        dasha=dasha,
    )


# ---------------------------------------------------------------- adapter


def test_adapter_preserves_status_profiles_convention_and_versions() -> None:
    evidence = dasha_evidence_from_facts(_load("vimshottari_success_depth2.json"))
    assert evidence.system_id == "vimshottari"
    assert evidence.status == "success" and evidence.reason_code is None
    assert evidence.precision_status == "exact"
    assert evidence.standards_version == "1.5.0"
    assert evidence.balance_profile_id == "DASHA_STANDARD_V1_BALANCE_LONGITUDE"
    assert evidence.year_length_profile_id == "YEAR_365_2425_FIXED_DAY"
    assert evidence.subperiod_profile_id == "DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1"
    assert evidence.boundary_convention == "half_open_start_inclusive_end_exclusive"
    assert evidence.time_base == "utc"


def test_adapter_preserves_the_starting_state_and_every_period_boundary() -> None:
    raw = _load("vimshottari_success_depth2.json")
    evidence = dasha_evidence_from_facts(raw)
    starting = raw["starting"]
    assert evidence.starting_nakshatra == starting["nakshatra"]
    assert evidence.starting_pada == starting["pada"]
    assert evidence.starting_lord is Body(starting["lord"])
    assert evidence.remaining_fraction == (
        f"{starting['remaining_fraction']['numerator']}/"
        f"{starting['remaining_fraction']['denominator']}"
    )
    assert evidence.remaining_duration_microseconds == starting["remaining_duration_microseconds"]
    assert evidence.birth_utc == raw["birth_utc"]
    assert len(evidence.periods) == len(raw["periods"]) == 38
    for record, node in zip(evidence.periods, raw["periods"], strict=True):
        assert record.period_id == node["period_id"]
        assert (record.start_utc, record.end_utc) == (node["start_utc"], node["end_utc"])
        assert record.lord is Body(node["lord"])
        assert record.parent_id == node["parent_id"]
    assert {r.level for r in evidence.periods} == {"mahadasha", "antardasha"}


def test_adapter_keeps_the_provenance_labels_apart() -> None:
    evidence = dasha_evidence_from_facts(_load("vimshottari_success_depth2.json"))
    labels = {entry.evidence_label for entry in evidence.provenance}
    assert {"source_supported", "engineering_convention", "derived_calculation"} <= labels
    balance = next(e for e in evidence.provenance if e.entry_id == "prov.balance")
    assert "does not resolve" in balance.statement  # the source conflict stays visible


def test_a_not_evaluable_result_is_recorded_with_its_reason_and_no_periods() -> None:
    evidence = dasha_evidence_from_facts(_load("vimshottari_not_evaluable.json"))
    assert evidence.status == "not_evaluable"
    assert evidence.reason_code == "starting_lord_ambiguous"
    assert evidence.precision_status == "approximate"
    assert evidence.periods == () and evidence.starting_lord is None


def test_facts_hash_is_stable_and_sensitive_to_content() -> None:
    raw = _load("vimshottari_success_depth2.json")
    first = dasha_evidence_from_facts(raw)
    assert dasha_evidence_from_facts(_copy(raw)).facts_hash == first.facts_hash
    changed = _copy(raw)
    changed["periods"][0]["end_utc"] = "2000-01-01T00:00:00Z"
    assert dasha_evidence_from_facts(changed).facts_hash != first.facts_hash
    assert len(first.facts_hash) == 64


@pytest.mark.parametrize(
    "field", ["profile_ids", "precision", "status", "starting", "periods", "birth_utc"]
)
def test_missing_required_fields_raise_facts_error(field: str) -> None:
    raw = _load("vimshottari_success_depth2.json")
    del raw[field]
    with pytest.raises(FactsError):
        dasha_evidence_from_facts(raw)


def test_malformed_facts_raise_facts_error_not_a_validation_error() -> None:
    raw = _load("vimshottari_success_depth2.json")
    raw["periods"][0]["lord"] = "pluto"
    with pytest.raises(FactsError):
        dasha_evidence_from_facts(raw)
    raw = _load("vimshottari_success_depth2.json")
    raw["depth"] = "three"
    with pytest.raises(FactsError):
        dasha_evidence_from_facts(raw)


def test_a_failure_without_a_reason_and_a_success_without_periods_are_rejected() -> None:
    failed = _load("vimshottari_not_evaluable.json")
    failed["reason_code"] = None
    with pytest.raises(FactsError):
        dasha_evidence_from_facts(failed)
    empty = _load("vimshottari_success_depth2.json")
    empty["periods"] = []
    with pytest.raises(FactsError):
        dasha_evidence_from_facts(empty)


# ---------------------------------------------------------------- bundle


def test_a_bundle_without_dasha_is_serialized_exactly_as_before(ruleset: Ruleset) -> None:
    bundle = _bundle(ruleset, None)
    assert bundle.dasha is None
    assert '"dasha"' not in bundle.canonical_json()
    assert "dasha" not in bundle.model_dump(mode="json")
    assert bundle.bundle_version == "1"  # additive change: schema version unchanged


def test_a_bundle_with_dasha_records_the_facts_and_a_different_hash(ruleset: Ruleset) -> None:
    evidence = dasha_evidence_from_facts(_load("vimshottari_success_depth2.json"))
    plain = _bundle(ruleset, None)
    with_dasha = _bundle(ruleset, evidence)
    assert with_dasha.dasha == evidence
    dumped = with_dasha.model_dump(mode="json")
    assert dumped["dasha"]["starting_lord"] == evidence.starting_lord.value  # type: ignore[union-attr]
    assert with_dasha.bundle_hash != plain.bundle_hash
    assert with_dasha.canonical_json() == _bundle(ruleset, evidence).canonical_json()
    assert with_dasha.bundle_hash == _bundle(ruleset, evidence).bundle_hash


def test_attaching_dasha_never_changes_or_removes_existing_evidence(ruleset: Ruleset) -> None:
    evidence = dasha_evidence_from_facts(_load("vimshottari_success_depth2.json"))
    plain = _bundle(ruleset, None)
    with_dasha = _bundle(ruleset, evidence)
    for field in ("versions", "chart", "derived_facts", "results", "summary", "conflicts"):
        assert getattr(with_dasha, field) == getattr(plain, field)
    assert with_dasha.dependencies == plain.dependencies
    assert with_dasha.source_profiles == plain.source_profiles


def test_the_bundle_hash_reflects_the_dasha_profile_and_periods(ruleset: Ruleset) -> None:
    raw = _load("vimshottari_success_depth2.json")
    base = _bundle(ruleset, dasha_evidence_from_facts(raw)).bundle_hash
    other_profile = _copy(raw)
    other_profile["profile_ids"]["year_length_profile_id"] = "YEAR_360_FIXED_DAY"
    assert _bundle(ruleset, dasha_evidence_from_facts(other_profile)).bundle_hash != base
    other_period = _copy(raw)
    other_period["periods"][1]["start_utc"] = "2000-01-01T00:00:00Z"
    assert _bundle(ruleset, dasha_evidence_from_facts(other_period)).bundle_hash != base


def test_the_bundle_round_trips_through_json_with_dasha(ruleset: Ruleset) -> None:
    evidence = dasha_evidence_from_facts(_load("vimshottari_success_depth2.json"))
    restored = json.loads(_bundle(ruleset, evidence).canonical_json())
    assert restored["dasha"]["periods"][0]["period_id"] == evidence.periods[0].period_id
    assert restored["dasha"]["facts_hash"] == evidence.facts_hash


def test_requires_dasha_stays_reserved_no_phase6_rule_emits_it(ruleset: Ruleset) -> None:
    """Resolving the deferred Dasha status is a later rule phase's job: no
    shipped rule reads Dasha facts, so none returns `requires_dasha`."""
    bundle = _bundle(ruleset, dasha_evidence_from_facts(_load("vimshottari_success_depth2.json")))
    assert all(result.reason is not Reason.REQUIRES_DASHA for result in bundle.results)
