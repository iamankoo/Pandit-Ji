"""Adapters from upstream evidence to ``EvidenceItem``s, through public contracts only.

The LLM layer consumes evidence; it never reaches into the component that produced it. This module
reads the public ``PalmEvidenceBundle`` contract (``pandit_contracts.palm``), not ``palm-vision``.
Only identifiers, enumerated values, confidences, rule statuses and source locations are passed:
no geometry, no image reference, no hashes of pixels. Phase 15 owns the full evidence assembly;
this is the minimal bridge that proves the interface works for the Phase 13 bundle.
"""

from __future__ import annotations

from pandit_contracts.llm import EvidenceItem
from pandit_contracts.palm import PalmEvidenceBundle, PalmFact


def _fact_text(fact: PalmFact) -> str:
    value = fact.value
    shown = (
        "none" if value.kind == "NONE" else f"{value.v}{(' ' + value.unit) if value.unit else ''}"
    )
    return (
        f"fact_type={fact.fact_type.value}; class={fact.fact_class.value}; "
        f"hand={fact.hand_side.value}; value={shown}; "
        f"confidence_bp={fact.confidence.score_bp}; calibrated={fact.confidence.calibrated}; "
        f"visibility={fact.visibility.state.value}"
    )


def palm_bundle_to_evidence(bundle: PalmEvidenceBundle) -> tuple[EvidenceItem, ...]:
    """One item per fact and per rule evaluation, plus one for the bundle's readiness."""
    items: list[EvidenceItem] = [
        EvidenceItem(
            evidence_id=f"bundle.{bundle.analysis_id}"[:128],
            kind="PALM_BUNDLE_STATUS",
            content=(
                f"production_ready={bundle.production_ready}; "
                f"readiness_blockers={'; '.join(bundle.readiness_blockers) or 'none'}; "
                f"knowledge_version={bundle.knowledge_version}"
            ),
        )
    ]
    items.extend(
        EvidenceItem(evidence_id=f.fact_id, kind="PALM_FACT", content=_fact_text(f))
        for f in bundle.fact_set.facts
    )
    for rule in bundle.rule_evaluations:
        items.append(
            EvidenceItem(
                evidence_id=rule.rule_id,
                kind="PALM_RULE",
                source_ref=f"{rule.source_profile}:{rule.source_location}",
                content=(
                    f"status={rule.status.value}; "
                    f"tags={','.join(rule.interpretation_tags) or 'none'}; "
                    f"fact_refs={','.join(rule.fact_refs) or 'none'}; "
                    f"rule_version={rule.rule_version}"
                ),
            )
        )
    return tuple(items)
