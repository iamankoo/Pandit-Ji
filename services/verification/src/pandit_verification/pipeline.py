"""The verified-response pipeline: narration + trusted evidence -> verified response.

``verify_narration`` runs the verifier and applies its report to the narration. It is the only
place a ``NarrationClaim`` or ``NarrationResponse`` is given ``VerificationState.VERIFIED``, and
only for claims the verifier itself marked ``VERIFIED``. ``verified_by`` is a label, not a
signature: downstream code must trust the ``VerificationResponse`` (its ``report_hash`` and trace),
not a string on a claim, and an input claim that already carries ``VERIFIED`` is treated as forged.
"""

from __future__ import annotations

from dataclasses import dataclass

from pandit_contracts.agent import (
    AgentStatus,
    NarrationClaim,
    NarrationResponse,
    NarrationSection,
    VerificationState,
)
from pandit_contracts.verification import (
    ReleaseAction,
    VerificationResponse,
    VerificationStatus,
)

from pandit_verification.engine import Verifier, verifier_identity


@dataclass(frozen=True)
class VerifiedOutcome:
    report: VerificationResponse
    # The narration to release: verified claims marked VERIFIED, everything else stripped. ``None``
    # when the action is REGENERATE or there is nothing to verify (the original is not released).
    response: NarrationResponse | None


def apply_report(response: NarrationResponse, report: VerificationResponse) -> NarrationResponse:
    """Return ``response`` with only the verifier-verified claims kept and marked VERIFIED.

    Raises ``ValueError`` if the report does not describe this response's claims.
    """
    by_id = {r.claim_id: r for r in report.claims}
    if len(by_id) != len(report.claims) or {c.claim_id for c in response.claims} != set(by_id):
        raise ValueError("the verification report does not match the narration")
    sections: list[NarrationSection] = []
    for section in response.sections:
        kept: list[NarrationClaim] = []
        for claim in section.claims:
            result = by_id[claim.claim_id]
            if result.status is VerificationStatus.VERIFIED:
                kept.append(
                    claim.model_copy(
                        update={
                            "verification": VerificationState.VERIFIED,
                            "verified_by": result.verified_by,
                        }
                    )
                )
        if kept:
            sections.append(section.model_copy(update={"claims": tuple(kept)}))
    all_verified = report.verified_claim_ids and len(report.verified_claim_ids) == len(by_id)
    stripped = len(report.verified_claim_ids) < len(by_id)
    update: dict[str, object] = {"sections": tuple(sections)}
    if all_verified:
        update["verification"] = VerificationState.VERIFIED
        update["verified_by"] = verifier_identity()
    if stripped and response.status is AgentStatus.COMPLETED:
        update["status"] = AgentStatus.DEGRADED
    return response.model_copy(update=update)


def verify_narration(response: NarrationResponse, verifier: Verifier) -> VerifiedOutcome:
    report = verifier.verify(response)
    if report.release_action in {ReleaseAction.APPROVE, ReleaseAction.RELEASE_VERIFIED_ONLY}:
        return VerifiedOutcome(report, apply_report(response, report))
    return VerifiedOutcome(report, None)
