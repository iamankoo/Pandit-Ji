"""EvidenceBundle (Phase 6E): the reproducible, provenance-carrying output of
a rule evaluation.

A bundle keeps *everything* needed to reproduce and audit a result
(`docs/ASTROLOGY_STANDARDS.md` §"Evidence bundle and reproducibility"):

- the chart / calculation snapshot and calculation configuration (ayanamsa,
  node model, house system, timezone, coordinates), with the standards
  version the *chart* was built under (Phase 5 charts stay `1.3.0`);
- the rule-engine, standards (`1.4.0` for rule evaluation), ruleset version
  and ruleset content hash;
- every rule result -- triggered, not triggered, cancelled, partially
  cancelled and `NOT_EVALUABLE` -- with rule IDs, source profiles, reading
  IDs and per-reading outcomes;
- conflicts (conflict/ambiguity groups), unresolved dependencies and
  provenance.

The bundle contains no timestamp and no host-specific data, so the same
chart, configuration, ruleset hash and engine version always produce the
same bundle (and the same `bundle_hash`).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from pandit_rule_engine.facts import CalculationSnapshot, ChartFacts, PlanetFact
from pandit_rule_engine.hashing import HASH_ALGORITHM, canonical_json, sha256_hex
from pandit_rule_engine.loader import Ruleset
from pandit_rule_engine.results import Provenance, RuleResult
from pandit_rule_engine.vocab import ALL_BODIES, Reason, Sign, Status

BUNDLE_VERSION = "1"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VersionInfo(_Model):
    rule_engine_version: str
    rule_standards_version: str
    calculation_engine_version: str
    calculation_standards_version: str
    ruleset_id: str
    ruleset_version: str
    ruleset_schema_version: int
    ruleset_content_hash: str
    hash_algorithm: str = HASH_ALGORITHM


class ChartSnapshot(_Model):
    """The upstream chart exactly as the rules saw it."""

    lagna_sign: Sign
    planets: tuple[PlanetFact, ...]
    sign_lords: dict[str, str]
    calculation: CalculationSnapshot


class ResultSummary(_Model):
    """Rule IDs grouped by runtime status (results remain the source of truth)."""

    triggered: tuple[str, ...]
    not_triggered: tuple[str, ...]
    cancelled: tuple[str, ...]
    partially_cancelled: tuple[str, ...]
    not_evaluable: tuple[str, ...]


class GroupRecord(_Model):
    """Rules sharing a conflict group (different traditions of one topic) or
    an ambiguity group (readings of one topic). Statuses are all retained;
    nothing here resolves a conflict."""

    group_id: str
    kind: str
    rule_ids: tuple[str, ...]
    statuses: dict[str, str]


class DependencyRecord(_Model):
    """An unresolved dependency or reason that blocked at least one rule."""

    reason: Reason
    detail: str | None
    rule_ids: tuple[str, ...]


class SourceProfileRecord(_Model):
    profile: str
    provenance: Provenance
    rule_ids: tuple[str, ...]


class EvidenceBundle(_Model):
    bundle_version: str
    versions: VersionInfo
    chart: ChartSnapshot
    derived_facts: dict[str, Any]
    results: tuple[RuleResult, ...]
    summary: ResultSummary
    conflicts: tuple[GroupRecord, ...]
    dependencies: tuple[DependencyRecord, ...]
    source_profiles: tuple[SourceProfileRecord, ...]
    bundle_hash: str

    def canonical_json(self) -> str:
        return canonical_json(self.model_dump(mode="json"))


def _chart_snapshot(facts: ChartFacts) -> ChartSnapshot:
    ordered = tuple(facts.planets[body] for body in ALL_BODIES if body in facts.planets)
    return ChartSnapshot(
        lagna_sign=facts.lagna_sign,
        planets=ordered,
        sign_lords={sign.value: lord.value for sign, lord in facts.sign_lords.items()},
        calculation=facts.snapshot,
    )


def _summary(results: tuple[RuleResult, ...]) -> ResultSummary:
    def ids(status: Status) -> tuple[str, ...]:
        return tuple(sorted(result.rule_id for result in results if result.status is status))

    return ResultSummary(
        triggered=ids(Status.TRIGGERED),
        not_triggered=ids(Status.NOT_TRIGGERED),
        cancelled=ids(Status.CANCELLED),
        partially_cancelled=ids(Status.PARTIALLY_CANCELLED),
        not_evaluable=ids(Status.NOT_EVALUABLE),
    )


def _groups(results: tuple[RuleResult, ...]) -> tuple[GroupRecord, ...]:
    buckets: dict[tuple[str, str], list[RuleResult]] = {}
    for result in results:
        if result.conflict_group is not None:
            buckets.setdefault(("conflict", result.conflict_group), []).append(result)
        if result.ambiguity_group is not None:
            buckets.setdefault(("ambiguity", result.ambiguity_group), []).append(result)
    records = []
    for (kind, group_id), members in sorted(buckets.items()):
        ordered = sorted(members, key=lambda item: item.rule_id)
        records.append(
            GroupRecord(
                group_id=group_id,
                kind=kind,
                rule_ids=tuple(item.rule_id for item in ordered),
                statuses={item.rule_id: item.status.value for item in ordered},
            )
        )
    return tuple(records)


def _dependencies(results: tuple[RuleResult, ...]) -> tuple[DependencyRecord, ...]:
    buckets: dict[tuple[str, str | None], list[str]] = {}
    for result in results:
        if result.status is Status.NOT_EVALUABLE and result.reason is not None:
            buckets.setdefault((result.reason.value, result.detail), []).append(result.rule_id)
    return tuple(
        DependencyRecord(reason=Reason(reason), detail=detail, rule_ids=tuple(sorted(rule_ids)))
        for (reason, detail), rule_ids in sorted(
            buckets.items(), key=lambda item: (item[0][0], item[0][1] or "")
        )
    )


def _source_profiles(results: tuple[RuleResult, ...]) -> tuple[SourceProfileRecord, ...]:
    buckets: dict[str, list[RuleResult]] = {}
    for result in results:
        buckets.setdefault(result.profile, []).append(result)
    return tuple(
        SourceProfileRecord(
            profile=profile,
            provenance=members[0].provenance,
            rule_ids=tuple(sorted(item.rule_id for item in members)),
        )
        for profile, members in sorted(buckets.items())
    )


def build_bundle(
    *,
    ruleset: Ruleset,
    facts: ChartFacts,
    results: tuple[RuleResult, ...],
    derived_facts: dict[str, Any],
    rule_engine_version: str,
) -> EvidenceBundle:
    """Assemble the bundle and stamp it with its own content hash."""
    versions = VersionInfo(
        rule_engine_version=rule_engine_version,
        rule_standards_version=ruleset.manifest.standards_version,
        calculation_engine_version=facts.snapshot.calculation_engine_version,
        calculation_standards_version=facts.snapshot.standards_version,
        ruleset_id=ruleset.manifest.ruleset_id,
        ruleset_version=ruleset.manifest.ruleset_version,
        ruleset_schema_version=ruleset.manifest.schema_version,
        ruleset_content_hash=ruleset.content_hash,
    )
    body: dict[str, Any] = {
        "bundle_version": BUNDLE_VERSION,
        "versions": versions,
        "chart": _chart_snapshot(facts),
        "derived_facts": derived_facts,
        "results": results,
        "summary": _summary(results),
        "conflicts": _groups(results),
        "dependencies": _dependencies(results),
        "source_profiles": _source_profiles(results),
    }
    unsigned = EvidenceBundle(**body, bundle_hash="")
    digest = sha256_hex(canonical_json(unsigned.model_dump(mode="json", exclude={"bundle_hash"})))
    return unsigned.model_copy(update={"bundle_hash": digest})
