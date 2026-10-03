"""Evidence adapters: turn deterministic bundles into typed ``EvidenceRecord`` objects.

* ``PalmBundleTool`` reads the public Phase 13 ``PalmEvidenceBundle`` contract. It passes
  identifiers, enumerated values, confidences (as the producer defined them), visibility and rule
  statuses. It never passes pixels, geometry, image references or image hashes, and it preserves
  OBSERVED versus DERIVED exactly.
* ``AstrologyBundleTool`` reads the Phase 6 ``EvidenceBundle`` structurally (a ``Protocol``), so the
  agent package does not depend on the calculation packages. Birth date, time and coordinates are
  not passed: only placements, rule results, conflicts and the calculation configuration.

The adapters hold an already-computed bundle. They compute nothing. Adapters for dasha, transit,
compatibility and knowledge retrieval evidence are not built in Phase 15 (`FUTURE_PHASE`): the
planner reports those capabilities as missing instead of inventing them.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from pandit_contracts.agent import (
    Domain,
    EvidenceCapability,
    EvidenceClass,
    EvidenceRecord,
)
from pandit_contracts.palm import FactClass, PalmEvidenceBundle, PalmFact

from pandit_agent.orchestration.tools import ToolResult, ToolSpec

_TEXT_CAP = 2000


def _cap(text: str) -> str:
    return text if len(text) <= _TEXT_CAP else text[: _TEXT_CAP - 1] + "…"


# -- palmistry -------------------------------------------------------------------------------


def _palm_fact_text(fact: PalmFact) -> str:
    value = fact.value
    shown = (
        "none" if value.kind == "NONE" else f"{value.v}{(' ' + value.unit) if value.unit else ''}"
    )
    parts = [
        f"fact_type={fact.fact_type.value}",
        f"hand={fact.hand_side.value}",
        f"value={shown}",
        f"visibility={fact.visibility.state.value}",
    ]
    if fact.derived_from:
        parts.append(f"derived_from={','.join(fact.derived_from)}")
    return "; ".join(parts)


class PalmBundleTool:
    """Serves one PalmEvidenceBundle that the caller already produced (Phase 13)."""

    def __init__(self, bundle: PalmEvidenceBundle, *, name: str = "palm.bundle") -> None:
        self._bundle = bundle
        self._spec = ToolSpec(
            name=name,
            domain=Domain.PALMISTRY,
            capabilities=frozenset({EvidenceCapability.PALM_FACTS, EvidenceCapability.PALM_RULES}),
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def invoke(self, capabilities: frozenset[EvidenceCapability]) -> ToolResult:
        bundle = self._bundle
        ref = bundle.bundle_hash
        ready = bundle.production_ready
        records: list[EvidenceRecord] = [
            EvidenceRecord(
                evidence_id=f"bundle.{bundle.analysis_id}"[:128],
                domain=Domain.PALMISTRY,
                evidence_class=EvidenceClass.CONTEXT_STATUS,
                kind="PALM_BUNDLE_STATUS",
                text=_cap(
                    f"production_ready={ready}; "
                    f"quality_outcome={bundle.quality_result.outcome.value}; "
                    f"readiness_blockers={'; '.join(bundle.readiness_blockers) or 'none'}"
                ),
                status="PRODUCTION_READY" if ready else "NOT_PRODUCTION_READY",
                version_ref=bundle.knowledge_version,
                bundle_ref=ref,
                bundle_production_ready=ready,
            )
        ]
        if EvidenceCapability.PALM_FACTS in capabilities:
            for fact in bundle.fact_set.facts:
                cls = (
                    EvidenceClass.OBSERVED_FACT
                    if fact.fact_class is FactClass.OBSERVED
                    else EvidenceClass.DERIVED_FACT
                )
                records.append(
                    EvidenceRecord(
                        evidence_id=fact.fact_id,
                        domain=Domain.PALMISTRY,
                        evidence_class=cls,
                        kind=fact.fact_type.value,
                        text=_cap(_palm_fact_text(fact)),
                        status=fact.visibility.state.value,
                        confidence_bp=fact.confidence.score_bp,
                        confidence_calibrated=fact.confidence.calibrated,
                        version_ref=bundle.knowledge_version,
                        fact_refs=tuple(fact.derived_from),
                        bundle_ref=ref,
                        bundle_production_ready=ready,
                    )
                )
        if EvidenceCapability.PALM_RULES in capabilities:
            for rule in bundle.rule_evaluations:
                records.append(
                    EvidenceRecord(
                        evidence_id=rule.rule_id,
                        domain=Domain.PALMISTRY,
                        evidence_class=EvidenceClass.RULE_EVALUATION,
                        kind="PALM_RULE",
                        text=_cap(
                            f"rule_version={rule.rule_version}; "
                            f"tags={','.join(rule.interpretation_tags) or 'none'}; "
                            f"reason={rule.reason or 'none'}"
                        ),
                        status=rule.status.value,
                        source_profile=rule.source_profile,
                        source_location=rule.source_location,
                        version_ref=rule.knowledge_version,
                        fact_refs=tuple(rule.fact_refs),
                        conflict_ids=tuple(rule.conflict_ids),
                        bundle_ref=ref,
                        bundle_production_ready=ready,
                    )
                )
        return ToolResult(tuple(records))


# -- astrology -------------------------------------------------------------------------------


class AstrologyBundleLike(Protocol):
    """The fields of the Phase 6 ``EvidenceBundle`` this adapter reads (structural typing)."""

    bundle_hash: str
    versions: Any
    chart: Any
    results: Sequence[Any]
    conflicts: Sequence[Any]


def _enum(value: Any) -> str:
    return str(getattr(value, "value", value))


class AstrologyBundleTool:
    """Serves one Phase 6 EvidenceBundle (chart placements, rule results, conflicts)."""

    def __init__(self, bundle: AstrologyBundleLike, *, name: str = "astrology.bundle") -> None:
        self._bundle = bundle
        self._spec = ToolSpec(
            name=name,
            domain=Domain.ASTROLOGY,
            capabilities=frozenset(
                {EvidenceCapability.ASTRO_CHART, EvidenceCapability.ASTRO_RULES}
            ),
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def invoke(self, capabilities: frozenset[EvidenceCapability]) -> ToolResult:
        bundle = self._bundle
        ref = str(bundle.bundle_hash)
        versions = bundle.versions
        ruleset_ref = f"{versions.ruleset_id}@{versions.ruleset_version}"
        records: list[EvidenceRecord] = []
        snap = bundle.chart.calculation
        records.append(
            EvidenceRecord(
                evidence_id="astro.config",
                domain=Domain.ASTROLOGY,
                evidence_class=EvidenceClass.CONTEXT_STATUS,
                kind="CALCULATION_CONFIGURATION",
                text=_cap(
                    f"zodiac={snap.zodiac}; ayanamsa={snap.ayanamsa}; "
                    f"house_system={snap.house_system}; "
                    f"node_convention={snap.node_convention}; "
                    f"calculation_engine={snap.calculation_engine_version}"
                ),
                status="CONFIGURED",
                version_ref=ruleset_ref,
                bundle_ref=ref,
            )
        )
        if EvidenceCapability.ASTRO_CHART in capabilities:
            records.append(
                EvidenceRecord(
                    evidence_id="astro.lagna",
                    domain=Domain.ASTROLOGY,
                    evidence_class=EvidenceClass.CALCULATED_FACT,
                    kind="LAGNA",
                    text=f"lagna_sign={_enum(bundle.chart.lagna_sign)}",
                    version_ref=ruleset_ref,
                    bundle_ref=ref,
                )
            )
            for planet in bundle.chart.planets:
                body = _enum(planet.body)
                dignity = _enum(planet.dignity) if planet.dignity is not None else "none"
                records.append(
                    EvidenceRecord(
                        evidence_id=f"astro.planet.{body}".lower(),
                        domain=Domain.ASTROLOGY,
                        evidence_class=EvidenceClass.CALCULATED_FACT,
                        kind="PLANET_PLACEMENT",
                        text=_cap(
                            f"body={body}; sign={_enum(planet.sign)}; house={planet.house}; "
                            f"dignity={dignity}; retrograde={planet.retrograde}"
                        ),
                        version_ref=ruleset_ref,
                        bundle_ref=ref,
                    )
                )
        if EvidenceCapability.ASTRO_RULES in capabilities:
            grouped: dict[str, list[str]] = {}
            for group in bundle.conflicts:
                for rule_id in group.rule_ids:
                    grouped.setdefault(rule_id, []).append(str(group.group_id))
            for result in bundle.results:
                prov = result.provenance
                records.append(
                    EvidenceRecord(
                        evidence_id=str(result.rule_id),
                        domain=Domain.ASTROLOGY,
                        evidence_class=EvidenceClass.RULE_EVALUATION,
                        kind="ASTRO_RULE",
                        text=_cap(
                            f"rule_version={result.rule_version}; profile={result.profile}; "
                            f"readings_agree={result.readings_agree}; "
                            f"reason={_enum(result.reason) if result.reason else 'none'}"
                        ),
                        status=_enum(result.status),
                        source_profile=str(result.profile),
                        source_location=str(prov.source_location),
                        version_ref=ruleset_ref,
                        conflict_ids=tuple(grouped.get(str(result.rule_id), ())),
                        bundle_ref=ref,
                    )
                )
        return ToolResult(tuple(records))
