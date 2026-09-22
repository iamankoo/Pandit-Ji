"""Phase 9 WP-EB -> Phase 6 contract: Ashtakavarga facts recorded in the
EvidenceBundle.

Fixtures are the JSON form of real astro-engine `AshtakavargaFacts` /
`AshtakavargaReductionFacts` results, generated once by the WP-A1/A2/A3
service (see the fixture files' own generation script, not committed). The
rule engine reads them without importing astro-engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.ashtakavarga_evidence import (
    AshtakavargaChart,
    ashtakavarga_evidence_from_facts,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "ashtakavarga"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


# ---------------------------------------------------------------- WP-A1


def test_wp_a1_success_export_bphs_grid_profile() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    evidence = ashtakavarga_evidence_from_facts(facts)
    assert evidence.system_id == "ashtakavarga"
    assert evidence.status == "success" and evidence.reason_code is None
    assert evidence.profile is not None
    assert evidence.profile.profile_id == "ASHTAKAVARGA_BPHS_GRID_KAPOOR_66"
    assert evidence.profile.reference.source_id == "SRC-BPHS-SANTHANAM-1984"
    assert evidence.profile.has_lagna_chart is True
    assert len(evidence.charts) == 7
    assert evidence.sarva is not None and evidence.sarva.total_benefic == 337
    assert evidence.lagna_chart is not None
    assert evidence.lagna_chart.chart == AshtakavargaChart.LAGNA
    # WP-A2/A3 not requested -> empty, not merely absent.
    assert evidence.reductions == () and evidence.pinda == ()
    assert evidence.lagna_reduction is None and evidence.lagna_pinda is None


def test_wp_a1_bhinna_chart_carries_per_sign_and_per_contributor_detail() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    evidence = ashtakavarga_evidence_from_facts(facts)
    sun_chart = next(c for c in evidence.charts if c.chart == AshtakavargaChart.SUN)
    assert len(sun_chart.sign_counts) == 12
    # 12 signs x 8 contributors.
    assert len(sun_chart.contributor_marks) == 96
    assert sun_chart.total_benefic == sum(s.benefic_count for s in sun_chart.sign_counts)


def test_wp_a1_sarva_states_it_is_unreduced() -> None:
    evidence = ashtakavarga_evidence_from_facts(_load("ashtakavarga_bphs_grid_success.json"))
    assert evidence.sarva is not None
    assert "unreduced" in evidence.sarva.reduction_note
    assert len(evidence.sarva.per_sign_benefic_count) == 12


def test_wp_a1_not_evaluable_missing_lagna_carries_no_facts() -> None:
    evidence = ashtakavarga_evidence_from_facts(
        _load("ashtakavarga_not_evaluable_missing_lagna.json")
    )
    assert evidence.status == "not_evaluable"
    assert evidence.reason_code == "lagna_unavailable"
    assert evidence.profile is None
    assert evidence.charts == () and evidence.sarva is None


def test_wp_a1_brihat_jataka_profile_has_no_lagna_chart() -> None:
    """A second, distinct profile: exercises that profile selection is
    preserved verbatim and that a profile without a Lagna chart never has
    one synthesized."""
    evidence = ashtakavarga_evidence_from_facts(_load("ashtakavarga_brihat_jataka_success.json"))
    assert evidence.profile is not None
    assert evidence.profile.profile_id == "ASHTAKAVARGA_BRIHAT_JATAKA_SASTRI_IX_1_7"
    assert evidence.profile.has_lagna_chart is False
    assert evidence.lagna_chart is None


# ---------------------------------------------------------------- WP-A2/A3


def test_wp_a2_reduction_export_and_ekadhipatya_equal_value_conflict() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    evidence = ashtakavarga_evidence_from_facts(facts, reduction)
    assert len(evidence.reductions) == 7
    moon = next(r for r in evidence.reductions if r.chart == AshtakavargaChart.MOON)
    assert moon.status == "not_evaluable"
    assert moon.reason_code == "ekadhipatya_equal_value_conflict"
    assert moon.ekadhipatya_corrected is None  # withheld entirely, never partial
    assert len(moon.ekadhipatya_conflicts) == 1
    conflict = moon.ekadhipatya_conflicts[0]
    # Both readings preserved verbatim, with provenance.
    assert conflict.reading_a_occupied_value == conflict.shared_value
    assert conflict.reading_b_occupied_value == 0
    assert "Ch. 68" in conflict.source_note and "876" in conflict.source_note

    resolved = next(r for r in evidence.reductions if r.status == "success")
    assert resolved.ekadhipatya_corrected is not None
    assert len(resolved.ekadhipatya_corrected) == 12
    assert resolved.ekadhipatya_conflicts == ()


def test_wp_a3_pinda_export_success() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    evidence = ashtakavarga_evidence_from_facts(facts, reduction)
    assert len(evidence.pinda) == 7
    resolved = next(p for p in evidence.pinda if p.status == "success")
    assert resolved.rasi_pinda is not None
    assert resolved.graha_pinda_status == "available"
    assert resolved.yoga_pinda == resolved.rasi_pinda + (resolved.graha_pinda or 0)
    assert resolved.graha_contributions


def test_wp_a3_pinda_withheld_when_chart_reduction_is_unresolved() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    evidence = ashtakavarga_evidence_from_facts(facts, reduction)
    moon_pinda = next(p for p in evidence.pinda if p.chart == AshtakavargaChart.MOON)
    assert moon_pinda.status == "not_evaluable"
    assert moon_pinda.reason_code == "ekadhipatya_equal_value_conflict"
    assert moon_pinda.rasi_pinda is None
    assert moon_pinda.graha_pinda is None and moon_pinda.yoga_pinda is None


def test_mercury_multiplier_conflict_is_carried_via_a_single_chart_pinda_record() -> None:
    raw = _load("pinda_mercury_conflict.json")["pinda_result"]
    from pandit_rule_engine.ashtakavarga_evidence import _pinda

    record = _pinda(raw)
    assert record.status == "success"  # the chart-level reduction itself was fine
    assert record.rasi_pinda is not None  # Rasi Pinda is unaffected by a Graha-only conflict
    assert record.graha_pinda_status == "not_evaluable"
    assert record.graha_pinda_reason == "mercury_multiplier_conflict"
    assert record.graha_pinda is None and record.yoga_pinda is None
    gemini = next(c for c in record.graha_contributions if c.sign.value == "gemini")
    assert (
        gemini.occupying_contributor is not None and gemini.occupying_contributor.value == "mercury"
    )
    assert gemini.product is None and gemini.multiplier is None


def test_multi_occupant_sign_conflict_is_carried() -> None:
    raw = _load("pinda_multi_occupant_conflict.json")["pinda_result"]
    from pandit_rule_engine.ashtakavarga_evidence import _pinda

    record = _pinda(raw)
    assert record.graha_pinda_status == "not_evaluable"
    assert record.graha_pinda_reason == "multiple_occupants_unsupported"
    taurus = next(c for c in record.graha_contributions if c.sign.value == "taurus")
    assert taurus.occupying_contributor is None  # ambiguous among >1 occupant, not guessed
    assert taurus.status == "not_evaluable"


# ---------------------------------------------------------------- validation


def test_missing_system_id_is_rejected() -> None:
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts({"status": "success"})


def test_missing_status_is_rejected() -> None:
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts({"system_id": "ashtakavarga"})


def test_non_success_without_reason_code_is_rejected() -> None:
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts({"system_id": "ashtakavarga", "status": "not_evaluable"})


def test_success_with_a_reason_code_is_rejected() -> None:
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts(
            {"system_id": "ashtakavarga", "status": "success", "reason_code": "lagna_unavailable"}
        )


def test_success_without_profile_or_sarva_is_rejected() -> None:
    """A successful result missing provenance-bearing sections (profile,
    sarva) must never silently produce a thin, contradictory evidence
    record."""
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts({"system_id": "ashtakavarga", "status": "success"})


def test_reduction_facts_missing_required_keys_is_rejected() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts(facts, {"status": "success"})


def test_not_a_mapping_is_rejected() -> None:
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts("not a dict")  # type: ignore[arg-type]


def test_reduction_facts_not_a_mapping_is_rejected() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts(facts, "not a dict")  # type: ignore[arg-type]


def test_a_chart_reduction_claiming_success_with_conflicts_is_rejected() -> None:
    """A result cannot claim `status: success` while also carrying
    conflicts, or vice versa -- the astro-engine contract is enforced here
    too, not assumed to always hold upstream."""
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    tampered = json.loads(json.dumps(reduction))
    moon = next(c for c in tampered["charts"] if c["chart"] == "moon")
    moon["status"] = "success"  # contradicts its own withheld ekadhipatya_corrected (None)
    with pytest.raises(FactsError):
        ashtakavarga_evidence_from_facts(facts, tampered)


# ---------------------------------------------------------------- determinism


def test_deterministic_hash_and_json_for_equivalent_input() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    first = ashtakavarga_evidence_from_facts(
        json.loads(json.dumps(facts)), json.loads(json.dumps(reduction))
    )
    second = ashtakavarga_evidence_from_facts(
        json.loads(json.dumps(facts)), json.loads(json.dumps(reduction))
    )
    assert first.facts_hash == second.facts_hash
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_different_profiles_produce_different_hashes() -> None:
    a = ashtakavarga_evidence_from_facts(_load("ashtakavarga_bphs_grid_success.json"))
    b = ashtakavarga_evidence_from_facts(_load("ashtakavarga_brihat_jataka_success.json"))
    assert a.facts_hash != b.facts_hash


def test_wp_a1_only_vs_with_reduction_produce_different_hashes() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    without = ashtakavarga_evidence_from_facts(facts)
    with_reduction = ashtakavarga_evidence_from_facts(facts, reduction)
    assert without.facts_hash != with_reduction.facts_hash


def test_json_round_trip() -> None:
    facts = _load("ashtakavarga_bphs_grid_success.json")
    reduction = _load("ashtakavarga_bphs_grid_reduction_with_conflict.json")
    evidence = ashtakavarga_evidence_from_facts(facts, reduction)
    dumped = evidence.model_dump(mode="json")
    restored = type(evidence).model_validate(dumped)
    assert restored == evidence
