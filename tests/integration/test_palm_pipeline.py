"""Phase 13 end to end: IMAGE -> QUALITY -> HAND -> SIDE -> REGION -> LANDMARKS -> FEATURES ->
FACTS -> RULES -> EVIDENCE, on synthetic images only (no model, no GPU, no user data)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pandit_contracts.palm import (
    FactClass,
    FactType,
    HandSide,
    LineAnalysisStatus,
    QualityOutcome,
    RuleStatus,
    build_palm_evidence_bundle,
)
from pandit_contracts.palm_coverage import CoverageRecord, PalmSourceCoverage
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.palm_content import load_palm_content
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_palm_vision.hand import StaticHandDetector
from pandit_palm_vision.image_input import CaptureContext
from pandit_palm_vision.pipeline import PalmPipeline
from pandit_palm_vision.quality import DEFAULT_QUALITY_CONFIG, fixture_quality_config
from pandit_palm_vision.synthetic import make_synthetic_palm
from pandit_rule_engine.palm import evaluate_palm_rules, load_palm_ruleset

REPO = Path(__file__).resolve().parents[2]
PALM_RULES = REPO / "services" / "rule-engine" / "palm_rules"
FACING = CaptureContext(mirrored=False, palm_facing=True)


@pytest.fixture(scope="module")
def knowledge() -> tuple[str, PalmSourceCoverage]:
    palm = load_palm_content()
    result = KnowledgeBuilder(
        InMemoryKnowledgeStore(), HashingEmbeddingProvider(), "1.28.0"
    ).build(palm.knowledge)
    return result.version_id, palm.coverage


def _run(side: HandSide, quality: object = None):  # type: ignore[no-untyped-def]
    palm = make_synthetic_palm(side, seed=3)
    detector = StaticHandDetector((palm.candidate(False),), False)
    pipeline = PalmPipeline(
        detector, quality_config=quality or fixture_quality_config()
    )  # type: ignore[arg-type]
    return pipeline.run(palm.image, FACING)


@pytest.mark.parametrize("side", [HandSide.LEFT, HandSide.RIGHT])
def test_the_whole_pipeline_yields_a_sealed_evidence_bundle(
    side: HandSide, knowledge: tuple[str, PalmSourceCoverage]
) -> None:
    version, coverage = knowledge
    outcome = _run(side)
    assert outcome.quality.outcome is QualityOutcome.ACCEPT
    ruleset = load_palm_ruleset(PALM_RULES, coverage)
    evaluations = evaluate_palm_rules(ruleset, outcome.fact_set, version)
    bundle = build_palm_evidence_bundle(
        fact_set=outcome.fact_set,
        rule_evaluations=list(evaluations),
        knowledge_version=version,
    )
    assert bundle.production_ready is False and bundle.readiness_blockers
    assert {f.fact_class for f in bundle.fact_set.facts} <= {
        FactClass.OBSERVED,
        FactClass.DERIVED,
    }
    status = {e.rule_id: e.status for e in evaluations}
    # the hand rules trigger from the observed side; the line rules cannot, because role
    # assignment is not validated: they are NOT_EVALUABLE, never guessed
    own = "LEFT" if side is HandSide.LEFT else "RIGHT"
    assert (
        status[
            f"PALMR_BE_{own}_HAND_"
            + ("NATURAL_MAP" if own == "LEFT" else "ALTERED_MAP")
        ]
        is RuleStatus.TRIGGERED
    )
    assert status["PALMR_HA_LIFE_LINE_ORIGIN_UNDER_JUPITER"] is RuleStatus.NOT_EVALUABLE
    assert (
        status["PALMR_HA_FATE_LINE_ORIGIN_FROM_LIFE_LINE"] is RuleStatus.NOT_EVALUABLE
    )
    for e in evaluations:
        assert e.knowledge_version == version
        if e.status is RuleStatus.TRIGGERED:
            assert e.fact_refs and set(e.fact_refs) <= {
                f.fact_id for f in bundle.fact_set.facts
            }


def test_the_bundle_is_reproducible(knowledge: tuple[str, PalmSourceCoverage]) -> None:
    version, coverage = knowledge
    ruleset = load_palm_ruleset(PALM_RULES, coverage)
    hashes = set()
    for _ in range(2):
        outcome = _run(HandSide.RIGHT)
        bundle = build_palm_evidence_bundle(
            fact_set=outcome.fact_set,
            rule_evaluations=list(
                evaluate_palm_rules(ruleset, outcome.fact_set, version)
            ),
            knowledge_version=version,
        )
        hashes.add(bundle.bundle_hash)
    assert len(hashes) == 1


def test_a_rejected_image_has_no_facts_and_so_no_triggered_rule(
    knowledge: tuple[str, PalmSourceCoverage],
) -> None:
    version, coverage = knowledge
    outcome = _run(
        HandSide.RIGHT, DEFAULT_QUALITY_CONFIG
    )  # uncalibrated config never accepts
    assert (
        outcome.quality.outcome is QualityOutcome.RETRY and outcome.fact_set.facts == ()
    )
    evaluations = evaluate_palm_rules(
        load_palm_ruleset(PALM_RULES, coverage), outcome.fact_set, version
    )
    assert {e.status for e in evaluations} == {RuleStatus.NOT_EVALUABLE}


def test_without_a_line_model_the_line_status_is_honest() -> None:
    outcome = _run(HandSide.LEFT)
    assert outcome.line_status is LineAnalysisStatus.MODEL_UNAVAILABLE
    tracks = [f for f in outcome.fact_set.facts if f.fact_type is FactType.LINE_TRACK]
    assert [t.visibility.state.value for t in tracks] == [
        "NOT_EVALUABLE"
    ]  # one honest placeholder
    assert tracks[0].visibility.reason == "PALM_LINE_MODEL_UNAVAILABLE"


def test_knowledge_rule_references_resolve_and_are_source_backed(
    knowledge: tuple[str, PalmSourceCoverage],
) -> None:
    _, coverage = knowledge
    ruleset = load_palm_ruleset(PALM_RULES, coverage)
    refs = {r.rule_id: r for r in load_palm_content().knowledge.rule_references}
    assert set(refs) == set(
        ruleset.rules
    )  # every reference exists; no rule is unreferenced
    for rule_id, ref in refs.items():
        rule = ruleset.rules[rule_id]
        assert (ref.profile_id, ref.source_location) == (
            rule.source_profile,
            rule.source_location,
        )
        assert ref.concept_id in rule.concepts
        assert (
            coverage.problems_for_rule(
                rule.source_profile, rule.source_location, rule.concepts
            )
            == ()
        )


def test_the_manifest_file_is_the_one_both_packages_read() -> None:
    path = REPO / "services" / "knowledge" / "content" / "palm" / "source_coverage.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    loaded = [CoverageRecord(**r) for r in data["records"]]
    assert tuple(loaded) == load_palm_content().coverage.records
