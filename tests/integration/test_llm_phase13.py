"""Phase 14 over Phase 13: FACTS -> RULES -> EVIDENCE -> LLM, through public contracts only.

The runtime is the scripted ``MockRuntime`` (a test double, not a model). What is asserted is the
interface and the boundary: the LLM layer reads the ``PalmEvidenceBundle`` it is given, passes only
identifiers and enumerated values into the prompt, can cite fact and rule ids, and cannot change
the bundle. Nothing here says anything about real model quality.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pandit_agent.llm.evidence import palm_bundle_to_evidence
from pandit_agent.llm.mock_runtime import MockRuntime
from pandit_agent.llm.safety import palm_restrictions
from pandit_agent.llm.service import LLMService, create_service
from pandit_agent.llm.settings import LLMSettings, generation_profile
from pandit_agent.llm.structured import ANSWER_WITH_EVIDENCE_REFS_V1
from pandit_contracts.llm import (
    LLMContext,
    LLMErrorCode,
    LLMLanguage,
    LLMMessage,
    LLMRequest,
    LLMStatus,
    MessageRole,
    OutputMode,
    OutputSpec,
)
from pandit_contracts.palm import (
    HandSide,
    PalmEvidenceBundle,
    build_palm_evidence_bundle,
)
from pandit_contracts.palm_coverage import PalmSourceCoverage
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.palm_content import load_palm_content
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_palm_vision.hand import StaticHandDetector
from pandit_palm_vision.image_input import CaptureContext
from pandit_palm_vision.pipeline import PalmPipeline
from pandit_palm_vision.quality import fixture_quality_config
from pandit_palm_vision.synthetic import make_synthetic_palm
from pandit_rule_engine.palm import evaluate_palm_rules, load_palm_ruleset
from pydantic import ValidationError

REPO = Path(__file__).resolve().parents[2]
PALM_RULES = REPO / "services" / "rule-engine" / "palm_rules"
MOCK_ID = "pandit-mock-deterministic"


@pytest.fixture(scope="module")
def bundle() -> PalmEvidenceBundle:
    palm = load_palm_content()
    built = KnowledgeBuilder(
        InMemoryKnowledgeStore(), HashingEmbeddingProvider(), "1.28.0"
    ).build(palm.knowledge)
    coverage: PalmSourceCoverage = palm.coverage
    sample = make_synthetic_palm(HandSide.RIGHT, seed=3)
    pipeline = PalmPipeline(
        StaticHandDetector((sample.candidate(False),), False),
        quality_config=fixture_quality_config(),
    )
    outcome = pipeline.run(
        sample.image, CaptureContext(mirrored=False, palm_facing=True)
    )
    ruleset = load_palm_ruleset(PALM_RULES, coverage)
    return build_palm_evidence_bundle(
        fact_set=outcome.fact_set,
        rule_evaluations=list(
            evaluate_palm_rules(ruleset, outcome.fact_set, built.version_id)
        ),
        knowledge_version=built.version_id,
    )


def _service(script: list[str] | None = None) -> tuple[LLMService, MockRuntime]:
    runtime = MockRuntime(script or [])
    settings = LLMSettings(
        manifest_name="mock-deterministic-test.json", allow_test_fixture=True
    )
    service = create_service(settings, runtime)
    service.start()
    return service, runtime  # type: ignore[return-value]


def _request(
    bundle: PalmEvidenceBundle, *, schema: bool, language: LLMLanguage
) -> LLMRequest:
    return LLMRequest(
        request_id="palm-1",
        model_id=MOCK_ID,
        language=language,
        messages=(
            LLMMessage(
                role=MessageRole.USER, content="Summarise the observed hand facts."
            ),
        ),
        context=LLMContext(
            context_version="palm-evidence-1",
            items=palm_bundle_to_evidence(bundle),
            restrictions=palm_restrictions(),
        ),
        generation=generation_profile("deterministic"),
        output=OutputSpec(mode=OutputMode.JSON, schema_id=ANSWER_WITH_EVIDENCE_REFS_V1)
        if schema
        else OutputSpec(),
    )


def test_every_fact_and_rule_becomes_a_traceable_evidence_item(
    bundle: PalmEvidenceBundle,
) -> None:
    items = palm_bundle_to_evidence(bundle)
    ids = {i.evidence_id for i in items}
    assert {f.fact_id for f in bundle.fact_set.facts} <= ids
    assert {r.rule_id for r in bundle.rule_evaluations} <= ids
    assert len(items) == 1 + len(bundle.fact_set.facts) + len(bundle.rule_evaluations)
    assert len(ids) == len(items)  # unique, as the context contract requires
    rule_items = [i for i in items if i.kind == "PALM_RULE"]
    assert rule_items and all(i.source_ref and ":" in i.source_ref for i in rule_items)


def test_the_evidence_carries_no_pixels_geometry_or_image_identity(
    bundle: PalmEvidenceBundle,
) -> None:
    text = "\n".join(i.content for i in palm_bundle_to_evidence(bundle))
    assert bundle.image_ref.image_id not in text
    assert bundle.image_ref.content_sha256 not in text
    assert "coords" not in text and "PCF-1" not in text


def test_the_bundle_readiness_is_passed_on_honestly(bundle: PalmEvidenceBundle) -> None:
    status = next(
        i for i in palm_bundle_to_evidence(bundle) if i.kind == "PALM_BUNDLE_STATUS"
    )
    assert "production_ready=False" in status.content
    assert bundle.knowledge_version in status.content


def test_the_whole_chain_runs_and_cites_real_ids(bundle: PalmEvidenceBundle) -> None:
    fact_id = bundle.fact_set.facts[0].fact_id
    answer = json.dumps(
        {"answer": "The hand side was observed.", "evidence_refs": [fact_id]}
    )
    service, runtime = _service([answer])
    response = service.generate(_request(bundle, schema=True, language=LLMLanguage.EN))
    assert response.status is LLMStatus.OK and response.structured is not None
    cited = response.structured["evidence_refs"]
    assert set(cited) <= {i.evidence_id for i in palm_bundle_to_evidence(bundle)}
    prompt = runtime.calls[0].prompt
    assert fact_id in prompt and "PALM_BUNDLE_STATUS" in prompt
    assert "lifespan" in prompt  # the Phase 13 restrictions travel as typed context
    assert (
        response.provenance is not None and response.provenance.is_real_model is False
    )


def test_the_llm_layer_cannot_change_the_bundle(bundle: PalmEvidenceBundle) -> None:
    before = bundle.model_dump_json()
    hash_before = bundle.bundle_hash
    service, _ = _service(["The hand side was observed."])
    assert service.generate(
        _request(bundle, schema=False, language=LLMLanguage.EN)
    ).status is (LLMStatus.OK)
    assert bundle.model_dump_json() == before and bundle.bundle_hash == hash_before
    with pytest.raises(ValidationError):  # frozen contract: nothing can edit a fact
        bundle.fact_set.facts[0].confidence = None  # type: ignore[misc,assignment]


def test_prohibited_palm_interpretations_are_blocked_even_over_real_evidence(
    bundle: PalmEvidenceBundle,
) -> None:
    service, _ = _service(["The life line shows a short life and a risk of disease."])
    response = service.generate(_request(bundle, schema=False, language=LLMLanguage.EN))
    assert response.status is LLMStatus.FAILED and response.error is not None
    assert response.error.code is LLMErrorCode.POLICY_VIOLATION


def test_the_same_bundle_yields_the_same_request_hash_and_prompt(
    bundle: PalmEvidenceBundle,
) -> None:
    a_service, a_runtime = _service()
    b_service, b_runtime = _service()
    a = a_service.generate(
        _request(bundle, schema=False, language=LLMLanguage.HINGLISH)
    )
    b = b_service.generate(
        _request(bundle, schema=False, language=LLMLanguage.HINGLISH)
    )
    assert a.request_hash == b.request_hash
    assert a_runtime.calls[0].prompt == b_runtime.calls[0].prompt
