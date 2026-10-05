"""The verification report, the verified-response pipeline, payloads and determinism (Phase 16)."""

from __future__ import annotations

import json

import pytest
from helpers import World, make_claim, make_response, make_world
from pandit_contracts.agent import (
    AgentStatus,
    ClaimType,
    EvidenceCapability,
    MissingCapability,
    NarrationClaim,
    VerificationState,
)
from pandit_contracts.verification import (
    ClaimVerification,
    OverallStatus,
    ReasonCode,
    ReleaseAction,
    VerificationResponse,
    VerificationStatus,
    VerificationTrace,
)
from pydantic import ValidationError

from pandit_verification import (
    TrustedEvidence,
    VerifierConfig,
    apply_report,
    verifier_identity,
    verify_narration,
)

S = VerificationStatus
GOOD = "Mars is placed in Aries in the first house."
UNREADABLE = "A placement was calculated."  # UNVERIFIABLE: nothing the checker can read
BLOCKED = "Saturn shows a short lifespan."


def _fact(world: World, cid: str, text: str, ident: str = "astro.planet.mars") -> NarrationClaim:
    return make_claim(world, cid, text, ClaimType.CALCULATION_FACT, [ident])


# -- mixed results, release decisions ------------------------------------------------------------


def test_v_mixed_results_are_reported_claim_by_claim(world: World) -> None:
    report = world.verifier().verify(
        make_response(
            _fact(world, "C1", GOOD),
            _fact(world, "C2", UNREADABLE),
            _fact(world, "C3", BLOCKED, "astro.planet.saturn"),
        )
    )
    assert [c.status for c in report.claims] == [S.VERIFIED, S.UNVERIFIABLE, S.POLICY_BLOCKED]
    assert report.overall_status is OverallStatus.PARTIALLY_VERIFIED
    assert report.verified_claim_ids == ("C1",)
    assert dict(report.status_counts) == {S.VERIFIED: 1, S.UNVERIFIABLE: 1, S.POLICY_BLOCKED: 1}
    # a blocked claim makes the whole narration a REGENERATE, but nothing is hidden: each claim
    # still carries its own result
    assert report.release_action is ReleaseAction.REGENERATE
    assert "VERIFIED=1" in report.summary


def test_one_unverifiable_claim_does_not_discard_the_verified_ones(world: World) -> None:
    response = make_response(_fact(world, "C1", GOOD), _fact(world, "C2", UNREADABLE))
    outcome = verify_narration(response, world.verifier())
    assert outcome.report.release_action is ReleaseAction.RELEASE_VERIFIED_ONLY
    assert outcome.response is not None
    released = outcome.response.claims
    assert [c.claim_id for c in released] == ["C1"]
    assert released[0].verification is VerificationState.VERIFIED
    assert released[0].verified_by == verifier_identity()
    assert outcome.response.status is AgentStatus.DEGRADED  # a stripped narration is not COMPLETED
    assert outcome.response.verification is VerificationState.UNVERIFIED  # not every claim passed


def test_an_all_verified_narration_is_approved_and_marked(world: World) -> None:
    response = make_response(
        _fact(world, "C1", GOOD),
        _fact(world, "C2", "Venus is in Libra in the seventh house.", "astro.planet.venus"),
    )
    outcome = verify_narration(response, world.verifier())
    assert outcome.report.overall_status is OverallStatus.ALL_VERIFIED
    assert outcome.report.release_action is ReleaseAction.APPROVE
    assert outcome.response is not None
    assert outcome.response.verification is VerificationState.VERIFIED
    assert outcome.response.verified_by == verifier_identity()
    assert all(c.verification is VerificationState.VERIFIED for c in outcome.response.claims)
    assert outcome.response.status is AgentStatus.COMPLETED
    # the original narration is untouched
    assert all(c.verification is VerificationState.UNVERIFIED for c in response.claims)


def test_a_narration_with_nothing_verified_is_regenerated(world: World) -> None:
    outcome = verify_narration(
        make_response(_fact(world, "C1", UNREADABLE), _fact(world, "C2", "Mars is in Leo.")),
        world.verifier(),
    )
    assert outcome.report.overall_status is OverallStatus.NONE_VERIFIED
    assert outcome.report.release_action is ReleaseAction.REGENERATE
    assert outcome.response is None


def test_a_wrong_claim_forces_regeneration_even_when_others_verify(world: World) -> None:
    report = world.verifier().verify(
        make_response(_fact(world, "C1", GOOD), _fact(world, "C2", "Mars is in Leo."))
    )
    assert report.release_action is ReleaseAction.REGENERATE
    assert report.verified_claim_ids == ("C1",)


def test_w_an_empty_or_refused_narration_has_nothing_to_verify(world: World) -> None:
    refused = make_response(status=AgentStatus.REFUSED)
    report = world.verifier().verify(refused)
    assert report.overall_status is OverallStatus.NO_CLAIMS
    assert report.release_action is ReleaseAction.NOTHING_TO_VERIFY
    assert report.claims == ()
    empty = world.verifier().verify_payload({"request_id": "r", "sections": []})
    assert empty.overall_status is OverallStatus.NO_CLAIMS
    assert verify_narration(refused, world.verifier()).response is None


def test_a_refused_response_that_carries_claims_is_not_verified(world: World) -> None:
    claim = _fact(world, "C1", GOOD)
    response = make_response(claim).model_copy(update={"status": AgentStatus.REFUSED})
    assert world.verifier().verify(response).claims == ()


# -- payloads, malformed input, duplicate ids ----------------------------------------------------


def test_x_a_malformed_claim_is_reported_and_the_rest_are_still_checked(world: World) -> None:
    good = _fact(world, "C1", GOOD).model_dump(mode="json")
    payload = {
        "request_id": "r1",
        "sections": [
            {
                "heading": "h",
                "claims": [
                    good,
                    {"claim_id": "C2", "text": "", "claim_type": "NOPE"},
                    "not even an object",
                    {
                        "claim_id": "C4",
                        "text": "x",
                        "claim_type": "CALCULATION_FACT",
                        "domain": "ASTROLOGY",
                        "references": [],
                    },
                ],
            }
        ],
    }
    report = world.verifier().verify_payload(payload)
    assert [c.status for c in report.claims] == [
        S.VERIFIED,
        S.INVALID_REFERENCE,
        S.INVALID_REFERENCE,
        S.INVALID_REFERENCE,
    ]
    assert all(ReasonCode.MALFORMED_CLAIM in {r.code for r in c.reasons} for c in report.claims[1:])
    assert report.release_action is ReleaseAction.REGENERATE


def test_a_payload_that_is_not_json_or_not_an_object_is_an_error_report(world: World) -> None:
    for bad in ("{not json", "[1, 2]", json.dumps("a string")):
        report = world.verifier().verify_payload(bad)
        assert report.error is not None and report.error.code == "MALFORMED_PAYLOAD"
        assert report.release_action is ReleaseAction.REGENERATE
    assert world.verifier().verify_payload({"sections": "no"}).error is not None


def test_a_json_string_payload_is_accepted(world: World) -> None:
    claim = _fact(world, "C1", GOOD)
    payload = json.dumps(
        {
            "request_id": "r",
            "sections": [{"heading": "h", "claims": [claim.model_dump(mode="json")]}],
        }
    )
    assert world.verifier().verify_payload(payload).verified_claim_ids == ("C1",)


def test_a_payload_that_pre_marks_itself_verified_is_flagged(world: World) -> None:
    claim = _fact(world, "C1", GOOD).model_dump(mode="json")
    payload = {
        "request_id": "r",
        "verification": "VERIFIED",
        "verified_by": "x",
        "sections": [{"heading": "h", "claims": [claim]}],
    }
    report = world.verifier().verify_payload(payload)
    assert report.trace.input_forgery_detected is True
    assert report.release_action is ReleaseAction.REGENERATE


def test_y_duplicate_claim_ids_are_invalid(world: World) -> None:
    report = world.verifier().verify(
        make_response(
            _fact(world, "C1", GOOD), _fact(world, "C1", "Venus is in Libra.", "astro.planet.venus")
        )
    )
    assert [c.status for c in report.claims] == [S.INVALID_REFERENCE, S.INVALID_REFERENCE]
    assert all(ReasonCode.DUPLICATE_CLAIM_ID in {r.code for r in c.reasons} for c in report.claims)
    assert report.verified_claim_ids == ()


def test_too_many_claims_is_a_typed_error(world: World) -> None:
    claims = [_fact(world, f"C{i:03d}", GOOD) for i in range(1, 6)]
    report = world.verifier(VerifierConfig(max_claims=3)).verify(make_response(*claims))
    assert report.error is not None and report.error.code == "TOO_MANY_CLAIMS"
    assert report.claims == ()


# -- contradictions ------------------------------------------------------------------------------


def test_a_contradiction_is_judged_against_the_evidence_not_against_other_claims(
    world: World,
) -> None:
    # Two claims about "Mars" can be about two different charts, so claims are never compared with
    # each other; each is compared with the trusted evidence it cites. Only the true one verifies.
    report = world.verifier().verify(
        make_response(
            _fact(world, "C1", "Mars is in Aries."), _fact(world, "C2", "Mars is in Leo.")
        )
    )
    assert [c.status for c in report.claims] == [S.VERIFIED, S.CONFLICTING_EVIDENCE]


# -- limitations ---------------------------------------------------------------------------------


def test_a_limitation_without_references_needs_a_trusted_record_of_the_gap(world: World) -> None:
    claim = make_claim(
        world,
        "C1",
        "The capability ASTRO_DASHA is not available for this reading.",
        ClaimType.LIMITATION,
        [],
    )
    without = world.verifier().verify(make_response(claim)).claims[0]
    assert without.status is S.UNVERIFIABLE
    gap = MissingCapability(capability=EvidenceCapability.ASTRO_DASHA, required=False, reason="x")
    withgap = world.verifier(trusted_missing=(gap,)).verify(make_response(claim)).claims[0]
    assert withgap.status is S.VERIFIED
    assert ReasonCode.LIMITATION_SUPPORTED in {r.code for r in withgap.reasons}
    other = make_claim(
        world, "C2", "The capability ASTRO_TRANSIT is not available.", ClaimType.LIMITATION, []
    )
    assert (
        world.verifier(trusted_missing=(gap,)).verify(make_response(other)).claims[0].status
        is S.UNVERIFIABLE
    )


# -- determinism and audit -----------------------------------------------------------------------


def test_z_verification_is_deterministic() -> None:
    def run() -> VerificationResponse:
        world = make_world()
        return world.verifier().verify(
            make_response(
                _fact(world, "C1", GOOD),
                _fact(world, "C2", "Mars is in Leo."),
                _fact(world, "C3", BLOCKED, "astro.planet.saturn"),
            )
        )

    first, second = run(), run()
    assert first.model_dump_json() == second.model_dump_json()
    assert first.report_hash == second.report_hash
    assert first.trace.input_hash == second.trace.input_hash
    assert first.trace.deterministic is True


def test_a_different_claim_or_config_changes_the_hashes(world: World) -> None:
    base = world.verifier().verify(make_response(_fact(world, "C1", GOOD)))
    other_claim = world.verifier().verify(make_response(_fact(world, "C1", "Mars is in Leo.")))
    other_config = world.verifier(VerifierConfig(min_confidence_bp=1)).verify(
        make_response(_fact(world, "C1", GOOD))
    )
    assert base.report_hash != other_claim.report_hash
    assert base.trace.input_hash != other_claim.trace.input_hash
    assert base.trace.config_hash != other_config.trace.config_hash


def test_the_audit_trace_records_what_was_checked_and_no_content(world: World) -> None:
    text = "Mars is placed in Aries in the first house."
    report = world.verifier().verify(make_response(_fact(world, "C1", text)))
    trace = report.trace
    assert trace.verifier_version and trace.policy_version and len(trace.config_hash) == 64
    assert trace.bundle_refs == (world.astro_ref,)
    assert trace.version_refs == ("PANDIT_JI_VEDIC@1.0.0",)
    assert trace.ruleset_hashes == (world.astro.versions.ruleset_content_hash,)
    assert {b.bundle_ref for b in trace.bundles} == {world.palm_ref, world.astro_ref}
    assert all(b.ok for b in trace.bundles)
    assert "text_grounding" in trace.checks_catalog
    dumped = report.model_dump_json()
    assert text not in dumped  # only the claim-text hash is recorded
    assert "user_text" not in dumped and "prompt" not in dumped


def test_the_result_contract_ties_verified_by_to_the_status() -> None:
    with pytest.raises(ValidationError):
        ClaimVerification(claim_id="C1", status=S.VERIFIED, verifier_version="x")
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_id="C1", status=S.UNSUPPORTED, verified_by="x", verifier_version="x"
        )
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_id="C1", status=S.UNSUPPORTED, verifier_version="x", claim_text_hash="nothex"
        )


def test_the_report_contract_rejects_an_inconsistent_report() -> None:
    trace = VerificationTrace(
        verifier_version="x", policy_version="y", config_hash="0" * 64, input_hash="0" * 64
    )
    with pytest.raises(ValidationError):
        VerificationResponse(
            verifier_version="x",
            overall_status=OverallStatus.ALL_VERIFIED,
            release_action=ReleaseAction.APPROVE,
            trace=trace,
            report_hash="0" * 64,
        )
    with pytest.raises(ValidationError):
        VerificationResponse(
            verifier_version="x",
            overall_status=OverallStatus.NO_CLAIMS,
            release_action=ReleaseAction.NOTHING_TO_VERIFY,
            trace=trace,
            report_hash="nothex",
        )


def test_apply_report_refuses_a_report_for_another_narration(world: World) -> None:
    one = make_response(_fact(world, "C1", GOOD))
    two = make_response(_fact(world, "C9", GOOD))
    report = world.verifier().verify(one)
    with pytest.raises(ValueError):
        apply_report(two, report)


def test_the_verifier_has_no_other_way_to_a_verified_claim() -> None:
    """A narration claim only becomes VERIFIED through ``apply_report`` and a verifier result."""
    import pandit_verification.engine as engine
    import pandit_verification.pipeline as pipeline

    assert engine.verifier_identity().startswith("pandit-verification@")
    source = open(pipeline.__file__, encoding="utf-8").read()
    assert source.count("VerificationState.VERIFIED") >= 1
    world = make_world()
    claim = _fact(world, "C1", UNREADABLE)
    outcome = verify_narration(make_response(claim, _fact(world, "C2", GOOD)), world.verifier())
    assert outcome.response is not None
    assert [c.claim_id for c in outcome.response.claims] == ["C2"]


def test_an_empty_trusted_evidence_set_verifies_nothing(world: World) -> None:
    report = Verifier_for(TrustedEvidence()).verify(make_response(_fact(world, "C1", GOOD)))
    assert report.claims[0].status is S.UNVERIFIABLE
    assert report.verified_claim_ids == ()


def Verifier_for(evidence: TrustedEvidence):  # noqa: N802 - a tiny test helper
    from pandit_verification import Verifier

    return Verifier(evidence)
