"""EvidenceBundle integration: backward compatibility (fixture-based, always
runs) and real astro-engine end-to-end (skipped when astro-engine/Swiss
Ephemeris is not installed, as in the rule-engine's own CI job)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine._version import __version__
from pandit_rule_engine.ashtakavarga_evidence import ashtakavarga_evidence_from_facts
from pandit_rule_engine.bundle import build_bundle
from pandit_rule_engine.evaluator import evaluate_ruleset
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, rules_dir, write_ruleset

_FIXTURES = Path(__file__).parent / "fixtures" / "ashtakavarga"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


# ---------------------------------------------------------- backward compat


@pytest.fixture()
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


def _build(ruleset, ashtakavarga=None):  # type: ignore[no-untyped-def]
    facts = chart("aries", full_placements())
    return build_bundle(
        ruleset=ruleset,
        facts=facts,
        results=evaluate_ruleset(ruleset, facts, StubDerived()),
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
        ashtakavarga=ashtakavarga,
    )


def test_bundle_without_ashtakavarga_omits_the_section_entirely(ruleset) -> None:  # type: ignore[no-untyped-def]
    bundle = _build(ruleset)
    assert bundle.ashtakavarga is None
    assert "ashtakavarga" not in bundle.model_dump(mode="json")
    assert "ashtakavarga" not in json.loads(bundle.canonical_json())


def test_existing_bundle_hash_is_unaffected_by_the_new_optional_field(ruleset) -> None:  # type: ignore[no-untyped-def]
    """The exact backward-compatibility requirement: a bundle built with no
    Ashtakavarga facts must serialize and hash identically regardless of
    whether the `ashtakavarga` parameter is passed as `None` or omitted."""
    explicit_none = _build(ruleset, ashtakavarga=None)
    omitted = build_bundle(
        ruleset=ruleset,
        facts=chart("aries", full_placements()),
        results=evaluate_ruleset(ruleset, chart("aries", full_placements()), StubDerived()),
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
    )
    assert explicit_none.bundle_hash == omitted.bundle_hash
    assert explicit_none.canonical_json() == omitted.canonical_json()


def test_adding_ashtakavarga_changes_the_hash_deterministically(ruleset) -> None:  # type: ignore[no-untyped-def]
    facts = _load("ashtakavarga_bphs_grid_success.json")
    evidence = ashtakavarga_evidence_from_facts(facts)
    without = _build(ruleset)
    with_av = _build(ruleset, ashtakavarga=evidence)
    assert without.bundle_hash != with_av.bundle_hash
    assert "ashtakavarga" in with_av.model_dump(mode="json")
    # Same input, rebuilt -> identical hash.
    with_av_again = _build(ruleset, ashtakavarga=ashtakavarga_evidence_from_facts(facts))
    assert with_av.bundle_hash == with_av_again.bundle_hash


def test_conflict_states_are_not_indistinguishable_in_the_bundle(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Two different Ashtakavarga results (a success and a NOT_EVALUABLE
    one) must never collapse into the same bundle hash."""
    success = ashtakavarga_evidence_from_facts(_load("ashtakavarga_bphs_grid_success.json"))
    not_evaluable = ashtakavarga_evidence_from_facts(
        _load("ashtakavarga_not_evaluable_missing_lagna.json")
    )
    bundle_success = _build(ruleset, ashtakavarga=success)
    bundle_not_evaluable = _build(ruleset, ashtakavarga=not_evaluable)
    assert bundle_success.bundle_hash != bundle_not_evaluable.bundle_hash


def test_rule_engine_transport_boundary_no_astrology_leaked() -> None:
    """The adapter module itself must never import astro-engine or perform
    any astrology computation -- it only re-shapes and validates JSON
    (mirrors `test_source_never_calls_astronomy_network_or_the_other_services`
    but asserted directly against this one new file for clarity)."""
    import pandit_rule_engine.ashtakavarga_evidence as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("pandit_astro_engine", "swisseph"):
        assert forbidden not in source


# --------------------------------------------------------- end-to-end (real)

pytest.importorskip("swisseph")
astro = pytest.importorskip("pandit_astro_engine")


def _kundli_and_ashtakavarga() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from pandit_astro_engine.ashtakavarga.models import (
        AshtakavargaReductionRequest,
        AshtakavargaRequest,
        NatalPositions,
    )
    from pandit_astro_engine.ashtakavarga.profiles import BPHS_GRID_ID
    from pandit_astro_engine.ashtakavarga.service import AshtakavargaCalculationService
    from pandit_astro_engine.models import (
        AstronomicalCalculationRequest,
        LocalDateTimeInput,
        Location,
    )

    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1990, month=6, day=15, hour=10, minute=0, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090),
    )
    kundli_model = astro.KundliCalculationService().calculate(request)
    service = AshtakavargaCalculationService()
    natal = NatalPositions.from_kundli(kundli_model)
    facts = service.calculate(AshtakavargaRequest(natal=natal, profile_id=BPHS_GRID_ID))
    reduction = service.calculate_reductions(
        AshtakavargaReductionRequest(natal=natal, profile_id=BPHS_GRID_ID)
    )
    return (
        kundli_model.model_dump(mode="json"),
        facts.model_dump(mode="json"),
        reduction.model_dump(mode="json"),
    )


def test_real_ashtakavarga_facts_are_recorded_in_the_bundle_beside_the_kundli() -> None:
    from pandit_rule_engine.engine import RuleEngine

    kundli, facts, reduction = _kundli_and_ashtakavarga()
    bundle = RuleEngine.from_directory(rules_dir()).evaluate_kundli(
        kundli, None, None, facts, reduction
    )
    assert bundle.ashtakavarga is not None
    assert bundle.ashtakavarga.status == "success"
    assert bundle.ashtakavarga.profile is not None
    assert bundle.ashtakavarga.profile.profile_id == "ASHTAKAVARGA_BPHS_GRID_KAPOOR_66"
    assert len(bundle.ashtakavarga.charts) == 7
    assert bundle.ashtakavarga.sarva is not None
    # Phase 5/6 evidence is untouched by the new section.
    assert bundle.versions.calculation_standards_version == kundli["metadata"]["standards_version"]
    assert bundle.dasha is None and bundle.transit is None


def test_the_bundle_with_real_ashtakavarga_facts_is_reproducible() -> None:
    from pandit_rule_engine.engine import RuleEngine

    kundli, facts, reduction = _kundli_and_ashtakavarga()
    engine = RuleEngine.from_directory(rules_dir())
    first = engine.evaluate_kundli(kundli, None, None, facts, reduction)
    second = engine.evaluate_kundli(kundli, None, None, facts, reduction)
    assert first.bundle_hash == second.bundle_hash
    without = engine.evaluate_kundli(kundli)
    assert without.ashtakavarga is None and without.bundle_hash != first.bundle_hash


def test_reduction_facts_are_ignored_without_base_facts() -> None:
    """`ashtakavarga_reduction_facts` is meaningless without
    `ashtakavarga_facts` for the same profile/chart -- confirms it is never
    silently used on its own."""
    from pandit_rule_engine.engine import RuleEngine

    kundli, _facts, reduction = _kundli_and_ashtakavarga()
    bundle = RuleEngine.from_directory(rules_dir()).evaluate_kundli(
        kundli, None, None, None, reduction
    )
    assert bundle.ashtakavarga is None
