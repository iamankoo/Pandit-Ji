"""Phase 8 -> Phase 6 contract: transit facts recorded in the EvidenceBundle.

The fixtures are the JSON form of astro-engine `TransitFacts` produced once by
the transit service (a window with a snapshot, a Sade Sati timeline, a
NOT_EVALUABLE result and an ambiguous-natal-Moon result). The rule engine reads
them without importing astro-engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine._version import __version__
from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.bundle import EvidenceBundle, build_bundle
from pandit_rule_engine.dasha_evidence import dasha_evidence_from_facts
from pandit_rule_engine.evaluator import evaluate_ruleset
from pandit_rule_engine.loader import Ruleset, load_ruleset
from pandit_rule_engine.transit_evidence import TransitEvidence, transit_evidence_from_facts
from pandit_rule_engine.vocab import Body, Reason
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset

_FIXTURES = Path(__file__).parent / "fixtures" / "transit"
_DASHA_FIXTURES = Path(__file__).parent / "fixtures" / "dasha"


def _load(name: str, folder: Path = _FIXTURES) -> dict[str, Any]:
    return json.loads((folder / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


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


def _bundle(
    ruleset: Ruleset,
    transit: TransitEvidence | None,
    dasha: Any = None,
) -> EvidenceBundle:
    facts = chart("aries", full_placements())
    return build_bundle(
        ruleset=ruleset,
        facts=facts,
        results=evaluate_ruleset(ruleset, facts, StubDerived()),
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
        dasha=dasha,
        transit=transit,
    )


# ---------------------------------------------------------------- adapter


def test_adapter_preserves_status_profiles_convention_and_versions() -> None:
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    assert evidence.system_id == "transit_gochara"
    assert evidence.status == "success" and evidence.reason_code is None
    assert evidence.standards_version == "1.6.0"
    assert evidence.boundary_convention == "half_open_start_inclusive_end_exclusive"
    assert evidence.time_base == "utc"
    ids = evidence.profile_ids
    assert ids.reference_profile_id == "TRANSIT_REF_MOON_SIGN"
    assert ids.vedha_profile_id == "GOCHARA_VEDHA_PHALADEEPIKA_SASTRI_XXVI_3_8"
    assert ids.sade_sati_profile_id == "SADE_SATI_SIGN_BASED_MODERN_V1"
    assert ids.lagna_profile_id == "TRANSIT_REF_LAGNA_SIGN"
    assert len(ids.favourable_reading_ids) == 4


def test_adapter_preserves_the_accuracy_disclosure() -> None:
    accuracy = transit_evidence_from_facts(_load("transit_success_window_snapshot.json")).accuracy
    assert accuracy is not None
    assert accuracy.instants_are_exact is False
    assert accuracy.ephemeris_modes and accuracy.zodiac == "sidereal"
    assert accuracy.ayanamsa == "lahiri" and accuracy.node_convention == "mean"
    assert accuracy.evidence_label == "engineering_evidence"
    assert "ayanamsa" in accuracy.ayanamsa_sensitivity_note


def test_adapter_preserves_every_event_and_the_snapshot_states() -> None:
    raw = _load("transit_success_window_snapshot.json")
    evidence = transit_evidence_from_facts(raw)
    assert evidence.window is not None and evidence.snapshot is not None
    assert (
        evidence.window.event_count == len(evidence.window.events) == len(raw["window"]["events"])
    )
    for record, event in zip(evidence.window.events, raw["window"]["events"], strict=True):
        assert (record.event_id, record.kind, record.instant_utc) == (
            event["event_id"],
            event["kind"],
            event["instant_utc"],
        )
        assert record.body is Body(event["body"])
        assert record.evidence_label == "engineering_convention"
    assert [s.body for s in evidence.snapshot.states] == [
        Body(s["body"]) for s in raw["snapshot"]["states"]
    ]


def test_the_moon_from_moon_conflict_is_carried_with_every_reading() -> None:
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    assert evidence.snapshot is not None
    moon = next(f for f in evidence.snapshot.favourable if f.body is Body.MOON)
    assert moon.house_from_moon == 6  # the fixture instant puts the Moon in a conflict house
    assert moon.status == "not_evaluable" and moon.reason_code == "reading_ambiguous"
    assert len(moon.readings) == 4
    assert {r.in_favourable_set for r in moon.readings} == {True, False}
    assert {r.label for r in moon.readings} == {"source_supported", "derived_calculation"}


def test_the_node_reading_stays_single_source() -> None:
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    assert evidence.snapshot is not None
    rahu = next(f for f in evidence.snapshot.favourable if f.body is Body.RAHU)
    assert rahu.status == "not_evaluable" and rahu.reason_code == "node_reading_single_source"
    assert [r.single_source for r in rahu.readings] == [True]


def test_vedha_facts_are_kept_structural_with_their_warnings() -> None:
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    assert evidence.snapshot is not None
    assert evidence.snapshot.vedha
    for fact in evidence.snapshot.vedha:
        assert fact.profile_id == "GOCHARA_VEDHA_PHALADEEPIKA_SASTRI_XXVI_3_8"
        assert fact.status in ("available", "not_evaluable")


def test_sade_sati_is_labelled_modern_tradition_and_never_classical() -> None:
    evidence = transit_evidence_from_facts(_load("transit_sade_sati_2020_2032.json"))
    sade = evidence.sade_sati
    assert sade is not None and sade.evidence_label == "modern_tradition"
    assert "not found as a combined unit" in sade.classical_status
    assert sade.natal_moon_sign == "pisces" and sade.band_signs == ("aquarius", "pisces", "aries")
    assert len(sade.segments) == 7 and len(sade.episodes) == 3
    assert [e.retrograde_reentry_of_previous_episode for e in sade.episodes] == [
        False,
        True,
        True,
    ]
    entry = next(e for e in evidence.provenance if e.entry_id == "sade_sati")
    assert entry.evidence_label == "modern_tradition"


def test_adapter_keeps_the_provenance_labels_apart() -> None:
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    label = {e.entry_id: e.evidence_label for e in evidence.provenance}
    assert label["favourable_conflict"] == "unresolved_conflict"
    assert label["favourable:GOCHARA_FAVOURABLE_BPHS_KAPOOR_66_DERIVED"] == "derived_calculation"
    assert label["vedha"] == "source_supported"
    assert label["events"] == "engineering_convention"
    assert label["accuracy"] == "engineering_evidence"


def test_a_not_evaluable_result_is_recorded_with_its_reason_and_no_facts() -> None:
    evidence = transit_evidence_from_facts(_load("transit_not_evaluable_window_too_large.json"))
    assert evidence.status == "not_evaluable" and evidence.reason_code == "window_too_large"
    assert evidence.snapshot is None and evidence.window is None and evidence.sade_sati is None
    assert evidence.natal is None and evidence.accuracy is None


def test_an_ambiguous_natal_moon_is_recorded_not_guessed() -> None:
    evidence = transit_evidence_from_facts(_load("transit_natal_moon_ambiguous.json"))
    assert evidence.status == "success"
    assert evidence.natal is not None
    assert evidence.natal.moon_sign is None
    assert evidence.natal.moon_sign_reason == "natal_moon_sign_ambiguous"
    assert evidence.snapshot is not None
    assert evidence.snapshot.moon_relative_status == "not_evaluable"
    assert evidence.snapshot.favourable == () and evidence.snapshot.vedha == ()
    assert evidence.sade_sati is not None and evidence.sade_sati.status == "not_evaluable"
    assert evidence.sade_sati.reason_code == "natal_moon_sign_ambiguous"


def test_facts_hash_is_stable_and_sensitive_to_content() -> None:
    raw = _load("transit_success_window_snapshot.json")
    first = transit_evidence_from_facts(raw)
    assert transit_evidence_from_facts(_copy(raw)).facts_hash == first.facts_hash
    changed = _copy(raw)
    changed["window"]["events"][0]["instant_utc"] = "2000-01-01T00:00:00Z"
    assert transit_evidence_from_facts(changed).facts_hash != first.facts_hash
    assert len(first.facts_hash) == 64


@pytest.mark.parametrize(
    "field", ["profile_ids", "status", "system_id", "boundary_convention", "time_base"]
)
def test_missing_required_fields_raise_facts_error(field: str) -> None:
    raw = _load("transit_success_window_snapshot.json")
    del raw[field]
    with pytest.raises(FactsError):
        transit_evidence_from_facts(raw)


@pytest.mark.parametrize("field", ["natal", "accuracy"])
def test_a_success_without_its_sections_is_rejected(field: str) -> None:
    raw = _load("transit_success_window_snapshot.json")
    raw[field] = None
    with pytest.raises(FactsError):
        transit_evidence_from_facts(raw)


def test_a_success_without_any_fact_section_is_rejected() -> None:
    raw = _load("transit_success_window_snapshot.json")
    raw["snapshot"] = None
    raw["window"] = None
    with pytest.raises(FactsError):
        transit_evidence_from_facts(raw)


def test_a_failure_without_a_reason_code_is_rejected() -> None:
    raw = _load("transit_not_evaluable_window_too_large.json")
    raw["reason_code"] = None
    with pytest.raises(FactsError):
        transit_evidence_from_facts(raw)


def test_a_success_with_a_reason_code_is_rejected() -> None:
    raw = _load("transit_success_window_snapshot.json")
    raw["reason_code"] = "no_query"
    with pytest.raises(FactsError):
        transit_evidence_from_facts(raw)


def test_malformed_facts_raise_facts_error_not_a_validation_error() -> None:
    raw = _load("transit_success_window_snapshot.json")
    raw["window"]["events"][0]["body"] = "pluto"
    with pytest.raises(FactsError):
        transit_evidence_from_facts(raw)


def test_a_non_object_is_rejected() -> None:
    with pytest.raises(FactsError):
        transit_evidence_from_facts([])  # type: ignore[arg-type]


# ---------------------------------------------------------------- bundle


def test_a_bundle_without_transit_facts_is_unchanged(ruleset: Ruleset) -> None:
    bundle = _bundle(ruleset, None)
    assert bundle.transit is None
    dumped = bundle.model_dump(mode="json")
    assert "transit" not in dumped and "dasha" not in dumped
    assert "transit" not in bundle.canonical_json()
    again = _bundle(ruleset, None)
    assert again.bundle_hash == bundle.bundle_hash
    assert again.canonical_json() == bundle.canonical_json()


def test_the_bundle_records_transit_facts_and_changes_its_hash(ruleset: Ruleset) -> None:
    plain = _bundle(ruleset, None)
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    with_transit = _bundle(ruleset, evidence)
    assert with_transit.transit == evidence
    assert with_transit.bundle_hash != plain.bundle_hash
    dumped = with_transit.model_dump(mode="json")
    assert dumped["transit"]["facts_hash"] == evidence.facts_hash
    # Everything else in the bundle is identical.
    for key in ("results", "summary", "chart", "versions", "conflicts", "dependencies"):
        assert dumped[key] == plain.model_dump(mode="json")[key]


def test_the_transit_bundle_is_reproducible(ruleset: Ruleset) -> None:
    raw = _load("transit_success_window_snapshot.json")
    first = _bundle(ruleset, transit_evidence_from_facts(raw))
    second = _bundle(ruleset, transit_evidence_from_facts(_copy(raw)))
    assert first.bundle_hash == second.bundle_hash
    assert first.canonical_json() == second.canonical_json()


def test_dasha_and_transit_sections_coexist(ruleset: Ruleset) -> None:
    dasha = dasha_evidence_from_facts(_load("vimshottari_success_depth2.json", _DASHA_FIXTURES))
    transit = transit_evidence_from_facts(_load("transit_sade_sati_2020_2032.json"))
    both = _bundle(ruleset, transit, dasha)
    dasha_only = _bundle(ruleset, None, dasha)
    transit_only = _bundle(ruleset, transit)
    assert both.dasha == dasha and both.transit == transit
    assert len({both.bundle_hash, dasha_only.bundle_hash, transit_only.bundle_hash}) == 3
    dumped = both.model_dump(mode="json")
    assert "dasha" in dumped and "transit" in dumped


def test_no_rule_reads_transit_facts_and_no_dependency_reason_is_emitted(
    ruleset: Ruleset,
) -> None:
    evidence = transit_evidence_from_facts(_load("transit_success_window_snapshot.json"))
    bundle = _bundle(ruleset, evidence)
    assert all(result.reason is not Reason.REQUIRES_DASHA for result in bundle.results)
    plain = _bundle(ruleset, None)
    assert [r.model_dump(mode="json") for r in bundle.results] == [
        r.model_dump(mode="json") for r in plain.results
    ]
