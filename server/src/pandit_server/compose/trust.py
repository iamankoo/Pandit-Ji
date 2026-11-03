"""Trusted-bundle registration with the Phase 16 verifier (Phase 16 itself is unchanged).

The verifier resolves references only against bundles it was given. A ``DomainAnalysisResult`` is
registered here through the verifier's public ``TrustedBundle`` and ``EvidenceItem`` types, and only
after the backend itself checks that the result is exactly what the deterministic layer produced:

* the result's content hash matches its content (no tampering after evaluation);
* the knowledge version and the ruleset hash are the ones this deployment pins (no stale or foreign
  methodology);
* every registered item is derived from the result's own facts and rules (nothing is taken from a
  caller, a model or a request), and a rule the policy withheld is never registered.

An unregistered result stays ``UNVERIFIABLE`` / ``EVIDENCE_UNAVAILABLE``; a gap claim stays
``UNVERIFIABLE`` because no trusted gap evidence is registered. A bundle is built per request, so
evidence can never be shared between users.
"""

from __future__ import annotations

from dataclasses import dataclass

from pandit_contracts.agent import Domain, EvidenceClass
from pandit_contracts.domain import DomainAnalysisResult, DomainStatus, domain_result_hash
from pandit_verification import TrustedEvidence
from pandit_verification.evidence import EvidenceItem, TrustedBundle


class TrustError(Exception):
    """The result cannot be registered as trusted evidence."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PinnedMethodology:
    knowledge_version: str
    ruleset_hash: str


def register_domain_result(
    trusted: TrustedEvidence, result: DomainAnalysisResult, pinned: PinnedMethodology
) -> str:
    """Register ``result`` and return its bundle reference. Raises :class:`TrustError`."""
    if domain_result_hash(result) != result.result_hash:
        raise TrustError("result_hash_mismatch")
    if result.versions.knowledge_version != pinned.knowledge_version:
        raise TrustError("knowledge_version_mismatch")
    if result.versions.ruleset_hash != pinned.ruleset_hash:
        raise TrustError("ruleset_hash_mismatch")
    ref = result.result_hash
    if ref in trusted.bundles:
        raise TrustError("bundle_already_registered")
    version_ref = result.versions.ruleset_ref
    bundle = TrustedBundle(
        bundle_ref=ref,
        domain=Domain.ASTROLOGY,
        version_refs=(version_ref,),
        production_ready=None,
        ruleset_hash=result.versions.ruleset_hash,
        knowledge_version=result.versions.knowledge_version,
    )
    for fact in result.facts:
        bundle.items[fact.fact_id] = EvidenceItem(
            evidence_id=fact.fact_id,
            domain=Domain.ASTROLOGY,
            evidence_class=EvidenceClass.CALCULATED_FACT,
            kind=fact.kind.value,
            bundle_ref=ref,
            version_ref=version_ref,
            source_profile=fact.source_profile,
            source_location=fact.source_location,
        )
    for rule in result.rules:
        if rule.status is DomainStatus.POLICY_BLOCKED:
            continue  # withheld by policy: nothing about it is citable
        bundle.items[rule.rule_id] = EvidenceItem(
            evidence_id=rule.rule_id,
            domain=Domain.ASTROLOGY,
            evidence_class=EvidenceClass.RULE_EVALUATION,
            kind="DOMAIN_RULE",
            bundle_ref=ref,
            status=rule.status.value,
            version_ref=version_ref,
            source_profile=rule.source_profile,
            source_id=rule.source_id,
            source_location=rule.source_location,
            rule_version=rule.rule_version,
            fact_refs=tuple(rule.fact_refs),
            basis_ids=tuple(rule.fact_refs),
            conflict_ids=tuple(rule.conflict_ids),
            tags=rule.interpretation.signification_tags if rule.interpretation else (),
        )
    trusted.bundles[ref] = bundle
    return ref
