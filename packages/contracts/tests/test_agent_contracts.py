from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from pandit_contracts.agent import (
    AgentError,
    AgentErrorCode,
    AgentRequest,
    AgentStatus,
    AgentTrace,
    ClaimType,
    Domain,
    EvidenceClass,
    EvidenceRecord,
    EvidenceReference,
    Intent,
    NarrationClaim,
    NarrationResponse,
    NarrationSection,
    ReferenceKind,
    VerificationState,
)
from pandit_contracts.llm import (
    GenerationConfig,
    LLMContext,
    LLMLanguage,
    LLMMessage,
    LLMRequest,
    MessageRole,
    TaskInstruction,
)


def _ref(domain: Domain = Domain.PALMISTRY, kind: ReferenceKind = ReferenceKind.FACT):
    return EvidenceReference(evidence_id="F1", domain=domain, kind=kind, bundle_ref="b" * 64)


def _claim(**over: object) -> NarrationClaim:
    base: dict[str, object] = {
        "claim_id": "C1",
        "text": "The hand side was observed.",
        "claim_type": ClaimType.OBSERVED_FEATURE,
        "domain": Domain.PALMISTRY,
        "references": (_ref(),),
    }
    base.update(over)
    return NarrationClaim(**base)  # type: ignore[arg-type]


def _response(**over: object) -> NarrationResponse:
    base: dict[str, object] = {
        "request_id": "r1",
        "language": LLMLanguage.EN,
        "status": AgentStatus.COMPLETED,
        "sections": (NarrationSection(heading="h", claims=(_claim(),)),),
        "trace": AgentTrace(agent_version="t"),
    }
    base.update(over)
    return NarrationResponse(**base)  # type: ignore[arg-type]


def test_a_request_round_trips_and_rejects_blank_or_bad_ids() -> None:
    request = AgentRequest(request_id="r1", language=LLMLanguage.HI, user_text="मेरा करियर?")
    assert AgentRequest.model_validate_json(request.model_dump_json()) == request
    for bad in ({"user_text": "   "}, {"request_id": "bad id"}, {"conversation_id": "no spaces"}):
        data = {"request_id": "r1", "language": LLMLanguage.EN, "user_text": "x", **bad}
        with pytest.raises(ValidationError):
            AgentRequest(**data)  # type: ignore[arg-type]


def test_a_request_cannot_carry_evidence_or_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AgentRequest(  # type: ignore[call-arg]
            request_id="r1", language=LLMLanguage.EN, user_text="x", evidence="smuggled"
        )


def test_the_intent_taxonomy_matches_the_specialist_modes() -> None:
    assert {i.value for i in Intent} >= {
        "GENERAL",
        "CAREER",
        "MARRIAGE",
        "LOVE_RELATIONSHIP",
        "WEALTH",
        "BUSINESS",
        "EDUCATION",
        "TRAVEL",
        "COMPATIBILITY",
        "TRANSIT",
        "DASHA",
        "DAILY_GUIDANCE",
        "LIFE_ANALYSIS",
        "PALM_OVERVIEW",
    }


def test_evidence_classes_are_distinct_and_map_to_reference_kinds() -> None:
    def record(cls: EvidenceClass) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id="E1",
            domain=Domain.PALMISTRY,
            evidence_class=cls,
            kind="K",
            text="t",
            bundle_ref="b" * 64,
        )

    assert record(EvidenceClass.OBSERVED_FACT).reference_kind is ReferenceKind.FACT
    assert record(EvidenceClass.DERIVED_FACT).reference_kind is ReferenceKind.FACT
    assert record(EvidenceClass.CALCULATED_FACT).reference_kind is ReferenceKind.FACT
    assert record(EvidenceClass.RULE_EVALUATION).reference_kind is ReferenceKind.RULE
    assert record(EvidenceClass.CONTEXT_STATUS).reference_kind is ReferenceKind.STATUS
    assert len({c.value for c in EvidenceClass}) == 5


def test_confidence_must_be_basis_points_in_range() -> None:
    for bad in (-1, 10001):
        with pytest.raises(ValidationError):
            EvidenceRecord(
                evidence_id="E1",
                domain=Domain.PALMISTRY,
                evidence_class=EvidenceClass.OBSERVED_FACT,
                kind="K",
                text="t",
                confidence_bp=bad,
                bundle_ref="b" * 64,
            )


def test_a_factual_claim_needs_references_but_a_limitation_does_not() -> None:
    with pytest.raises(ValidationError):
        _claim(references=())
    limitation = _claim(claim_type=ClaimType.LIMITATION, references=())
    assert limitation.references == ()


def test_a_claim_cannot_cite_another_domain() -> None:
    with pytest.raises(ValidationError):
        _claim(references=(_ref(Domain.ASTROLOGY),))


def test_generated_claims_are_unverified_and_verified_needs_a_verifier() -> None:
    assert _claim().verification is VerificationState.UNVERIFIED
    with pytest.raises(ValidationError):
        _claim(verification=VerificationState.VERIFIED)
    assert _claim(verification=VerificationState.VERIFIED, verified_by="phase16").verified_by
    with pytest.raises(ValidationError):
        _response(verification=VerificationState.VERIFIED)


def test_response_status_invariants() -> None:
    err = AgentError(code=AgentErrorCode.LLM_UNAVAILABLE, message="m")
    with pytest.raises(ValidationError):
        _response(status=AgentStatus.COMPLETED, sections=())
    with pytest.raises(ValidationError):
        _response(status=AgentStatus.FAILED, error=None, sections=())
    with pytest.raises(ValidationError):
        _response(status=AgentStatus.FAILED, error=err)  # sections present
    with pytest.raises(ValidationError):
        _response(status=AgentStatus.REFUSED, error=err)  # sections present
    assert _response(status=AgentStatus.FAILED, error=err, sections=()).error == err
    assert _response(status=AgentStatus.REFUSED, error=err, sections=()).sections == ()


def test_claims_property_flattens_in_order() -> None:
    two = NarrationSection(heading="a", claims=(_claim(claim_id="C1"), _claim(claim_id="C2")))
    three = NarrationSection(heading="b", claims=(_claim(claim_id="C3"),))
    assert [c.claim_id for c in _response(sections=(two, three)).claims] == ["C1", "C2", "C3"]


def test_the_error_vocabulary_covers_the_required_failure_modes() -> None:
    required = {
        "INVALID_REQUEST",
        "MISSING_EVIDENCE",
        "UNSUPPORTED_LANGUAGE",
        "UNSAFE_REQUEST",
        "INSUFFICIENT_EVIDENCE",
        "LLM_UNAVAILABLE",
        "LLM_TIMEOUT",
        "LLM_STRUCTURED_OUTPUT_FAILURE",
        "POLICY_REJECTION",
        "ORCHESTRATION_LIMIT",
        "INTERNAL_ERROR",
    }
    assert required <= {c.value for c in AgentErrorCode}


def test_the_trace_is_content_free_by_construction() -> None:
    fields = set(AgentTrace.model_fields)
    for forbidden in ("text", "prompt", "user_text", "narrative", "evidence", "messages"):
        assert forbidden not in fields


def test_the_task_instruction_is_additive_and_keeps_old_request_hashes() -> None:
    gen = GenerationConfig(config_version="g", temperature=0.0, top_p=1.0, max_new_tokens=8)
    messages = (LLMMessage(role=MessageRole.USER, content="hi"),)

    def request(context: LLMContext | None) -> LLMRequest:
        return LLMRequest(
            request_id="r",
            model_id="m",
            language=LLMLanguage.EN,
            messages=messages,
            context=context,
            generation=gen,
        )

    plain = request(LLMContext(context_version="c"))
    # Recompute the hash exactly as Phase 14 did, before the field existed: the dump without the
    # `task` key, canonical JSON, SHA-256. The new code must give the identical value.
    payload = plain.model_dump(mode="json", exclude={"request_id"})
    assert "task" in payload["context"]  # the field is present in a dump...
    del payload["context"]["task"]  # ...and absent from the legacy payload
    legacy = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert plain.request_hash() == legacy
    assert request(None).request_hash() == request(None).request_hash()
    tasked = request(
        LLMContext(context_version="c", task=TaskInstruction(task_id="t1", text="do the thing"))
    )
    assert tasked.request_hash() != plain.request_hash()
