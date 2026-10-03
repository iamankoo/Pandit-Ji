"""Structured narration: LLM output -> grounded, verification-ready claims.

This module turns the validated structured output of the model into ``NarrationClaim`` objects. It
does **referential and structural** grounding only; it does not verify meaning (Phase 16):

* every cited evidence id must exist in *this* context (a model cannot invent an id that later
  looks like provenance); the kind and domain of a reference come from the evidence record, never
  from the model;
* the claim type must match the semantic class of what it cites: OBSERVED facts back
  OBSERVED_FEATURE, DERIVED facts back DERIVED_FEATURE (never "observed"), calculated facts back
  CALCULATION_FACT, and a TRADITIONAL_INTERPRETATION needs rule evaluations that are all TRIGGERED
  (a NOT_EVALUABLE or NOT_TRIGGERED rule can only back a LIMITATION) and must not merge
  conflicting source profiles;
* source profiles, locations, versions, confidence and uncertainty flags are copied from the
  evidence deterministically;
* text is screened (restricted categories, claims of verification);
* every claim leaves as ``UNVERIFIED``. Whether the text is *supported by* the evidence is
  Phase 16's question.

Any violation fails the whole narration with a typed error and no partial narrative.
"""

from __future__ import annotations

from typing import Any

from pandit_contracts.agent import (
    AgentContext,
    AgentErrorCode,
    ClaimType,
    Domain,
    EvidenceClass,
    EvidenceRecord,
    EvidenceReference,
    NarrationClaim,
    NarrationSection,
    UncertaintyFlag,
)
from pandit_contracts.llm import LLMLanguage

from pandit_agent.orchestration import i18n
from pandit_agent.orchestration.context import all_records
from pandit_agent.orchestration.errors import AgentFailure
from pandit_agent.orchestration.policy import DomainPolicy, claims_verification, screen_claim_text

_FACT_CLASSES = {
    EvidenceClass.OBSERVED_FACT,
    EvidenceClass.DERIVED_FACT,
    EvidenceClass.CALCULATED_FACT,
}
_BACKING: dict[ClaimType, tuple[Domain, EvidenceClass]] = {
    ClaimType.CALCULATION_FACT: (Domain.ASTROLOGY, EvidenceClass.CALCULATED_FACT),
    ClaimType.OBSERVED_FEATURE: (Domain.PALMISTRY, EvidenceClass.OBSERVED_FACT),
    ClaimType.DERIVED_FEATURE: (Domain.PALMISTRY, EvidenceClass.DERIVED_FACT),
}
_NOT_VISIBLE = {"PARTIAL", "OCCLUDED", "NOT_VISIBLE"}
_FLAG_ORDER = list(UncertaintyFlag)


def _fail(message: str) -> AgentFailure:
    return AgentFailure(AgentErrorCode.NARRATION_GROUNDING_FAILURE, message)


def _flags(records: list[EvidenceRecord], trimmed: bool) -> tuple[UncertaintyFlag, ...]:
    found: set[UncertaintyFlag] = set()
    for r in records:
        status = r.status or ""
        if status == "NOT_EVALUABLE":
            found.add(UncertaintyFlag.NOT_EVALUABLE)
        if status in {"NOT_TRIGGERED", "CANCELLED", "PARTIALLY_CANCELLED"}:
            found.add(UncertaintyFlag.NOT_TRIGGERED)
        if status in _NOT_VISIBLE:
            found.add(UncertaintyFlag.NOT_VISIBLE)
        if r.conflict_ids:
            found.add(UncertaintyFlag.CONFLICTING_PROFILES)
        if r.confidence_bp is not None and not r.confidence_calibrated:
            found.add(UncertaintyFlag.UNCALIBRATED_CONFIDENCE)
        if r.bundle_production_ready is False:
            found.add(UncertaintyFlag.BUNDLE_NOT_PRODUCTION_READY)
    if trimmed:
        found.add(UncertaintyFlag.EVIDENCE_TRIMMED)
    return tuple(f for f in _FLAG_ORDER if f in found)


def _check_text(text: str, policy: DomainPolicy) -> None:
    if screen_claim_text(text, policy):
        raise AgentFailure(
            AgentErrorCode.POLICY_REJECTION, "generated text touches a restricted category"
        )
    if claims_verification(text):
        raise _fail("the narration claims verification, which only Phase 16 may do")


def _check_type(ctype: ClaimType, domain: Domain, records: list[EvidenceRecord]) -> None:
    if ctype is ClaimType.LIMITATION:
        return
    if not records:
        raise _fail("a claim cites no evidence")
    if ctype in _BACKING:
        want_domain, want_class = _BACKING[ctype]
        if domain is not want_domain:
            raise _fail("the claim type does not belong to this domain")
        if any(r.evidence_class is not want_class for r in records):
            raise _fail("a claim's type does not match the semantic class of the evidence it cites")
        return
    # TRADITIONAL_INTERPRETATION
    rules = [r for r in records if r.evidence_class is EvidenceClass.RULE_EVALUATION]
    if not rules:
        raise _fail("an interpretation must rest on at least one rule evaluation")
    if any(r.status != "TRIGGERED" for r in rules):
        raise _fail("only a TRIGGERED rule can back an interpretation")
    profiles = {r.source_profile for r in rules}
    if len(profiles) > 1:
        conflict_sets = [set(r.conflict_ids) for r in rules]
        if set.intersection(*conflict_sets) or any(
            a & b for i, a in enumerate(conflict_sets) for b in conflict_sets[i + 1 :]
        ):
            raise _fail("conflicting source profiles must not be merged into one claim")


def ground_narration(
    structured: Any,
    context: AgentContext,
    policy: DomainPolicy,
) -> tuple[NarrationSection, ...]:
    if not isinstance(structured, dict) or not isinstance(structured.get("sections"), list):
        raise _fail("the structured narration has an unexpected shape")
    records = {r.evidence_id: r for r in all_records(context)}
    sections: list[NarrationSection] = []
    counter = 0
    for raw_section in structured["sections"]:
        heading = str(raw_section["heading"])
        _check_text(heading, policy)
        claims: list[NarrationClaim] = []
        for raw in raw_section["claims"]:
            counter += 1
            text = str(raw["text"])
            _check_text(text, policy)
            ids = tuple(dict.fromkeys(str(i) for i in raw["evidence_ids"]))
            cited: list[EvidenceRecord] = []
            for evidence_id in ids:
                record = records.get(evidence_id)
                if record is None:
                    raise _fail("a claim cites evidence that is not in the context")
                cited.append(record)
            ctype = ClaimType(raw["claim_type"])
            _check_type(ctype, context.domain, cited)
            confidences = [r.confidence_bp for r in cited if r.confidence_bp is not None]
            claims.append(
                NarrationClaim(
                    claim_id=f"C{counter:03d}",
                    text=text,
                    claim_type=ctype,
                    domain=context.domain,
                    references=tuple(
                        EvidenceReference(
                            evidence_id=r.evidence_id,
                            domain=r.domain,
                            kind=r.reference_kind,
                            bundle_ref=r.bundle_ref,
                        )
                        for r in cited
                    ),
                    source_profiles=tuple(
                        sorted({r.source_profile for r in cited if r.source_profile})
                    ),
                    source_locations=tuple(
                        sorted({r.source_location for r in cited if r.source_location})
                    ),
                    version_refs=tuple(sorted({r.version_ref for r in cited if r.version_ref})),
                    uncertainty=_flags(cited, context.trimmed_count > 0),
                    min_confidence_bp=min(confidences) if confidences else None,
                )
            )
        sections.append(NarrationSection(heading=heading, claims=tuple(claims)))
    return tuple(sections)


def limitation_section(
    context: AgentContext, language: LLMLanguage, *, first_index: int
) -> NarrationSection | None:
    """Agent-authored, localized statements of what the evidence does not cover."""
    claims: list[NarrationClaim] = []
    index = first_index
    for missing in context.missing:
        index += 1
        claims.append(
            NarrationClaim(
                claim_id=f"C{index:03d}",
                text=i18n.text(
                    i18n.Message.LIMITATION_MISSING, language, capability=missing.capability.value
                ),
                claim_type=ClaimType.LIMITATION,
                domain=context.domain,
                references=(),
            )
        )
    if context.trimmed_count:
        index += 1
        claims.append(
            NarrationClaim(
                claim_id=f"C{index:03d}",
                text=i18n.text(
                    i18n.Message.LIMITATION_TRIMMED, language, count=context.trimmed_count
                ),
                claim_type=ClaimType.LIMITATION,
                domain=context.domain,
                references=(),
                uncertainty=(UncertaintyFlag.EVIDENCE_TRIMMED,),
            )
        )
    if not claims:
        return None
    return NarrationSection(
        heading=i18n.text(i18n.Message.LIMITATIONS_HEADING, language), claims=tuple(claims)
    )
