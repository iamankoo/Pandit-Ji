"""Verification contracts (Phase 16): statuses, reasons, the verified_by rule, additive change."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pandit_contracts import agent
from pandit_contracts.agent import VerificationState
from pandit_contracts.verification import (
    VERIFIER_ID,
    ClaimVerification,
    OverallStatus,
    ReasonCode,
    ReleaseAction,
    VerificationResponse,
    VerificationStatus,
    VerificationTrace,
)

SHA = "a" * 64


def _trace() -> VerificationTrace:
    return VerificationTrace(
        verifier_version="1", policy_version="p", config_hash=SHA, input_hash=SHA
    )


def test_the_seven_statuses_exist_and_are_exact() -> None:
    assert {s.value for s in VerificationStatus} == {
        "VERIFIED",
        "UNSUPPORTED",
        "UNVERIFIABLE",
        "INVALID_REFERENCE",
        "CONFLICTING_EVIDENCE",
        "POLICY_BLOCKED",
        "INSUFFICIENT_EVIDENCE",
    }


def test_verified_by_is_set_exactly_when_the_status_is_verified() -> None:
    ok = ClaimVerification(
        claim_id="C1",
        status=VerificationStatus.VERIFIED,
        verified_by=f"{VERIFIER_ID}@1",
        verifier_version="1",
    )
    assert ok.verified_by == "pandit-verification@1"
    for bad in (
        {"status": VerificationStatus.VERIFIED},
        {"status": VerificationStatus.POLICY_BLOCKED, "verified_by": "x"},
    ):
        with pytest.raises(ValidationError):
            ClaimVerification(claim_id="C1", verifier_version="1", **bad)


def test_a_result_holds_no_claim_text_field() -> None:
    fields = set(ClaimVerification.model_fields)
    assert "text" not in fields and "prompt" not in fields
    assert {"claim_id", "status", "verified_by", "reasons", "provenance", "uncertainty"} <= fields
    assert "claim_text_hash" in fields


def test_a_report_must_list_exactly_the_verified_claims() -> None:
    verified = ClaimVerification(
        claim_id="C1", status=VerificationStatus.VERIFIED, verified_by="v", verifier_version="1"
    )
    VerificationResponse(
        verifier_version="1",
        overall_status=OverallStatus.ALL_VERIFIED,
        release_action=ReleaseAction.APPROVE,
        claims=(verified,),
        verified_claim_ids=("C1",),
        trace=_trace(),
        report_hash=SHA,
    )
    with pytest.raises(ValidationError):
        VerificationResponse(
            verifier_version="1",
            overall_status=OverallStatus.NONE_VERIFIED,
            release_action=ReleaseAction.REGENERATE,
            claims=(verified,),
            verified_claim_ids=(),
            trace=_trace(),
            report_hash=SHA,
        )


def test_reason_codes_are_unique_strings() -> None:
    values = [r.value for r in ReasonCode]
    assert len(values) == len(set(values)) and all(v == v.upper() for v in values)


def test_the_phase_15_contract_is_unchanged_and_still_requires_a_verifier() -> None:
    assert agent.AGENT_CONTRACT_VERSION == "1.0.0"
    assert {v.value for v in VerificationState} == {"UNVERIFIED", "VERIFIED"}
    with pytest.raises(ValidationError):
        agent.NarrationResponse(
            request_id="r",
            language="EN",
            status=agent.AgentStatus.REFUSED,
            trace=agent.AgentTrace(agent_version="x"),
            verification=VerificationState.VERIFIED,
        )
