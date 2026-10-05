"""Trusted evidence resolution.

The verifier never trusts evidence that arrives with a claim, and it does not reuse the agent's
``EvidenceRecord`` objects. It is handed the **bundles themselves** (the Phase 13
``PalmEvidenceBundle`` and the Phase 6 ``EvidenceBundle``) and resolves every reference against
them. A bundle is first checked for integrity (its own content hash is recomputed; an optional
independent recomputation hook can re-run the deterministic rules), and anything inconsistent is
recorded as an integrity problem that makes every claim on that bundle ``INVALID_REFERENCE``.

The astrology bundle is read structurally (a ``Protocol``) so this package does not import the
calculation packages. Birth date, time and coordinates are not read: only placements, rule results,
conflicts and versions.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pandit_contracts.agent import Domain, EvidenceClass, ReferenceKind
from pandit_contracts.palm import (
    FactClass,
    PalmEvidenceBundle,
    PalmFact,
    PalmRuleEvaluation,
    bundle_hash_of,
)

from pandit_verification.text import PALM_LINES, PALM_MOUNTS

_SPLIT = re.compile(r"[._:\-\s/]+")
_STOP_SOURCE_WORDS = frozenset(
    {
        "src",
        "hand",
        "reading",
        "scientific",
        "palmistry",
        "for",
        "all",
        "the",
        "of",
        "part",
        "line",
        "lines",
        "palm",
    }
)


def _enum(value: Any) -> str:
    return str(value.value if isinstance(value, Enum) else value)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def attribution_tokens(*names: str | None) -> frozenset[str]:
    """Distinctive lower-case tokens a claim must contain to name a source (author, work)."""
    out: set[str] = set()
    for name in names:
        if not name:
            continue
        for part in _SPLIT.split(name.lower()):
            if part.isalpha() and len(part) >= 4 and part not in _STOP_SOURCE_WORDS:
                out.add(part)
    return frozenset(out)


@dataclass(eq=False)
class EvidenceItem:
    """One piece of trusted evidence, as resolved by the verifier from a bundle."""

    evidence_id: str
    domain: Domain
    evidence_class: EvidenceClass
    kind: str
    bundle_ref: str
    status: str | None = None
    version_ref: str | None = None
    source_profile: str | None = None
    source_id: str | None = None
    source_name: str | None = None
    source_location: str | None = None
    rule_version: str | None = None
    confidence_bp: int | None = None
    confidence_calibrated: bool | None = None
    fact_refs: tuple[str, ...] = ()
    conflict_ids: tuple[str, ...] = ()
    basis_ids: tuple[str, ...] = ()  # transitive fact basis (rule fact_refs, derived_from chain)
    missing_basis: tuple[str, ...] = ()  # basis ids the bundle does not contain
    tags: tuple[str, ...] = ()
    effect_class: str | None = None
    bundle_production_ready: bool | None = None
    unresolved_dependencies: tuple[str, ...] = ()
    # semantic attributes (verifier-derived, never taken from claim text)
    hands: frozenset[str] = frozenset()
    lines: frozenset[str] = frozenset()
    mounts: frozenset[str] = frozenset()
    planet: str | None = None
    sign: str | None = None
    house: int | None = None
    dignity: str | None = None
    retrograde: bool | None = None
    numbers: frozenset[str] = frozenset()

    @property
    def reference_kind(self) -> ReferenceKind:
        if self.evidence_class is EvidenceClass.RULE_EVALUATION:
            return ReferenceKind.RULE
        if self.evidence_class is EvidenceClass.CONTEXT_STATUS:
            return ReferenceKind.STATUS
        return ReferenceKind.FACT

    @property
    def attribution(self) -> frozenset[str]:
        return attribution_tokens(self.source_id, self.source_name)


@dataclass(eq=False)
class TrustedBundle:
    bundle_ref: str
    domain: Domain
    version_refs: tuple[str, ...]
    production_ready: bool | None
    items: dict[str, EvidenceItem] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    ruleset_hash: str | None = None
    knowledge_version: str | None = None
    planets: dict[str, EvidenceItem] = field(default_factory=dict)
    lagna: EvidenceItem | None = None

    @property
    def ok(self) -> bool:
        return not self.problems


class TrustedEvidence:
    """The set of bundles a verification run may resolve references against."""

    def __init__(self) -> None:
        self._bundles: dict[str, TrustedBundle] = {}

    @property
    def bundles(self) -> dict[str, TrustedBundle]:
        return self._bundles

    def domains(self) -> set[Domain]:
        return {b.domain for b in self._bundles.values()}

    def bundle(self, bundle_ref: str) -> TrustedBundle | None:
        return self._bundles.get(bundle_ref)

    # -- palmistry ---------------------------------------------------------------------------

    def add_palm(
        self,
        bundle: PalmEvidenceBundle,
        *,
        recompute: Callable[[Any, str], Sequence[PalmRuleEvaluation]] | None = None,
    ) -> TrustedEvidence:
        """Register a Phase 13 bundle.

        ``recompute(fact_set, knowledge_version)`` is an optional independent re-run of the
        deterministic palm rules (for example ``evaluate_palm_rules`` bound to the ruleset). When
        given, the recomputed evaluations must equal the bundle's; otherwise the bundle is
        untrusted.
        """
        ref = bundle.bundle_hash
        trusted = TrustedBundle(
            bundle_ref=ref,
            domain=Domain.PALMISTRY,
            version_refs=(bundle.knowledge_version,),
            production_ready=bundle.production_ready,
            knowledge_version=bundle.knowledge_version,
        )
        if bundle_hash_of(bundle) != bundle.bundle_hash:
            trusted.problems.append("bundle_hash does not match the bundle content")
        facts = {f.fact_id: f for f in bundle.fact_set.facts}
        for fact in bundle.fact_set.facts:
            if fact.analysis_id != bundle.analysis_id:
                trusted.problems.append("a fact belongs to a different analysis")
                break
        for rule in bundle.rule_evaluations:
            if rule.knowledge_version != bundle.knowledge_version:
                trusted.problems.append("a rule evaluation carries a different knowledge version")
                break
        if recompute is not None:
            try:
                again = recompute(bundle.fact_set, bundle.knowledge_version)
            except Exception as exc:  # the hook is untrusted code: contain it
                trusted.problems.append(f"independent recomputation failed: {type(exc).__name__}")
            else:
                if _rule_signature(again) != _rule_signature(bundle.rule_evaluations):
                    trusted.problems.append("rule evaluations are not reproducible from the facts")

        status_id = f"bundle.{bundle.analysis_id}"[:128]
        trusted.items[status_id] = EvidenceItem(
            evidence_id=status_id,
            domain=Domain.PALMISTRY,
            evidence_class=EvidenceClass.CONTEXT_STATUS,
            kind="PALM_BUNDLE_STATUS",
            bundle_ref=ref,
            status="PRODUCTION_READY" if bundle.production_ready else "NOT_PRODUCTION_READY",
            version_ref=bundle.knowledge_version,
            bundle_production_ready=bundle.production_ready,
        )
        for fact in bundle.fact_set.facts:
            trusted.items[fact.fact_id] = _palm_fact_item(fact, bundle, facts)
        for rule in bundle.rule_evaluations:
            trusted.items[rule.rule_id] = _palm_rule_item(rule, bundle, facts)
        self._bundles[ref] = trusted
        return self

    # -- astrology ---------------------------------------------------------------------------

    def add_astrology(
        self, bundle: Any, *, recompute: Callable[[], Any] | None = None
    ) -> TrustedEvidence:
        """Register a Phase 6 ``EvidenceBundle`` (read structurally).

        ``recompute()`` is an optional independent re-evaluation that returns a bundle; its
        ``bundle_hash`` must equal the supplied bundle's, otherwise the bundle is untrusted.
        """
        ref = str(bundle.bundle_hash)
        versions = bundle.versions
        ruleset_ref = f"{versions.ruleset_id}@{versions.ruleset_version}"
        trusted = TrustedBundle(
            bundle_ref=ref,
            domain=Domain.ASTROLOGY,
            version_refs=(ruleset_ref,),
            production_ready=None,
            ruleset_hash=str(versions.ruleset_content_hash),
        )
        dump = getattr(bundle, "model_dump", None)
        if dump is None:
            trusted.problems.append("the bundle cannot be re-hashed")
        else:
            body = dump(mode="json", exclude={"bundle_hash"})
            digest = hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
            if digest != ref:
                trusted.problems.append("bundle_hash does not match the bundle content")
        if recompute is not None:
            try:
                other = recompute()
                if str(other.bundle_hash) != ref:
                    trusted.problems.append(
                        "the bundle is not reproduced by independent evaluation"
                    )
            except Exception as exc:
                trusted.problems.append(f"independent recomputation failed: {type(exc).__name__}")

        trusted.items["astro.config"] = EvidenceItem(
            evidence_id="astro.config",
            domain=Domain.ASTROLOGY,
            evidence_class=EvidenceClass.CONTEXT_STATUS,
            kind="CALCULATION_CONFIGURATION",
            bundle_ref=ref,
            status="CONFIGURED",
            version_ref=ruleset_ref,
        )
        lagna = EvidenceItem(
            evidence_id="astro.lagna",
            domain=Domain.ASTROLOGY,
            evidence_class=EvidenceClass.CALCULATED_FACT,
            kind="LAGNA",
            bundle_ref=ref,
            version_ref=ruleset_ref,
            planet="lagna",
            sign=_enum(bundle.chart.lagna_sign),
        )
        trusted.items[lagna.evidence_id] = lagna
        trusted.lagna = lagna
        for planet in bundle.chart.planets:
            body_name = _enum(planet.body)
            item = EvidenceItem(
                evidence_id=f"astro.planet.{body_name}".lower(),
                domain=Domain.ASTROLOGY,
                evidence_class=EvidenceClass.CALCULATED_FACT,
                kind="PLANET_PLACEMENT",
                bundle_ref=ref,
                version_ref=ruleset_ref,
                planet=body_name.lower(),
                sign=_enum(planet.sign),
                house=int(planet.house),
                dignity=_enum(planet.dignity) if planet.dignity is not None else None,
                retrograde=bool(planet.retrograde),
            )
            trusted.items[item.evidence_id] = item
            trusted.planets[item.planet or ""] = item
        grouped: dict[str, list[str]] = {}
        for group in bundle.conflicts:
            if len(set(group.rule_ids)) < 2:
                continue  # a single-rule group is an ambiguity of one rule, not a source conflict
            for rule_id in group.rule_ids:
                grouped.setdefault(str(rule_id), []).append(str(group.group_id))
        for result in bundle.results:
            prov = result.provenance
            tags = result.interpretation_tags
            deps: list[str] = []
            for reading in result.readings:
                deps.extend(str(d) for d in reading.unresolved_dependencies)
            item = EvidenceItem(
                evidence_id=str(result.rule_id),
                domain=Domain.ASTROLOGY,
                evidence_class=EvidenceClass.RULE_EVALUATION,
                kind="ASTRO_RULE",
                bundle_ref=ref,
                status=_enum(result.status),
                version_ref=ruleset_ref,
                source_profile=str(result.profile),
                source_id=str(prov.source_id),
                source_name=str(prov.source),
                source_location=str(prov.source_location),
                rule_version=str(result.rule_version),
                conflict_ids=tuple(sorted(grouped.get(str(result.rule_id), ()))),
                tags=tuple(
                    sorted({*(tags.domain if tags else ()), *(tags.signification if tags else ())})
                ),
                effect_class=str(tags.effect_class) if tags else None,
                unresolved_dependencies=tuple(sorted(set(deps))),
            )
            trusted.items[item.evidence_id] = item
        self._bundles[ref] = trusted
        return self


def _rule_signature(rules: Sequence[PalmRuleEvaluation]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            r.rule_id,
            r.rule_version,
            r.status.value,
            r.knowledge_version,
            tuple(r.fact_refs),
            tuple(r.conflict_ids),
            tuple(r.interpretation_tags),
        )
        for r in rules
    )


def _closure(
    seed: Sequence[str], facts: dict[str, PalmFact]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Transitive fact basis and the ids the bundle does not contain."""
    seen: list[str] = []
    missing: list[str] = []
    stack = list(seed)
    visited: set[str] = set()
    while stack:
        fid = stack.pop()
        if fid in visited:
            continue
        visited.add(fid)
        fact = facts.get(fid)
        if fact is None:
            missing.append(fid)
            continue
        seen.append(fid)
        stack.extend(fact.derived_from)
    return tuple(sorted(seen)), tuple(sorted(missing))


def _palm_semantics(fact: PalmFact) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    hands = (
        frozenset({fact.hand_side.value})
        if fact.hand_side.value in {"LEFT", "RIGHT"}
        else frozenset()
    )
    pieces: list[str] = []
    if fact.region_id:
        pieces.append(fact.region_id)
    if fact.value.kind == "ENUM" and isinstance(fact.value.v, str):
        pieces.append(fact.value.v)
    lines: set[str] = set()
    mounts: set[str] = set()
    for piece in pieces:
        parts = [p for p in _SPLIT.split(piece.lower()) if p]
        for i, part in enumerate(parts):
            if part == "role" and i + 1 < len(parts) and parts[i + 1] in PALM_LINES:
                lines.add(PALM_LINES[parts[i + 1]])
            if part == "mount" and i + 1 < len(parts) and parts[i + 1] in PALM_MOUNTS:
                mounts.add(PALM_MOUNTS[parts[i + 1]])
    return hands, frozenset(lines), frozenset(mounts)


def _palm_fact_item(
    fact: PalmFact, bundle: PalmEvidenceBundle, facts: dict[str, PalmFact]
) -> EvidenceItem:
    hands, lines, mounts = _palm_semantics(fact)
    basis, missing = _closure(fact.derived_from, facts)
    numbers: set[str] = set()
    if fact.value.kind in {"INT", "RATIO_FIXED"} and fact.value.v is not None:
        numbers.add(str(fact.value.v))
    return EvidenceItem(
        evidence_id=fact.fact_id,
        domain=Domain.PALMISTRY,
        evidence_class=(
            EvidenceClass.OBSERVED_FACT
            if fact.fact_class is FactClass.OBSERVED
            else EvidenceClass.DERIVED_FACT
        ),
        kind=fact.fact_type.value,
        bundle_ref=bundle.bundle_hash,
        status=fact.visibility.state.value,
        version_ref=bundle.knowledge_version,
        confidence_bp=fact.confidence.score_bp,
        confidence_calibrated=fact.confidence.calibrated,
        fact_refs=tuple(fact.derived_from),
        basis_ids=basis,
        missing_basis=missing,
        bundle_production_ready=bundle.production_ready,
        hands=hands,
        lines=lines,
        mounts=mounts,
        numbers=frozenset(numbers),
    )


def _palm_rule_item(
    rule: PalmRuleEvaluation, bundle: PalmEvidenceBundle, facts: dict[str, PalmFact]
) -> EvidenceItem:
    basis, missing = _closure(rule.fact_refs, facts)
    hands: set[str] = set()
    lines: set[str] = set()
    mounts: set[str] = set()
    for fid in basis:
        h, ln, mt = _palm_semantics(facts[fid])
        hands |= h
        lines |= ln
        mounts |= mt
    tags = tuple(sorted(t.lower() for t in rule.interpretation_tags))
    for tag in tags:
        parts = tag.split("_")
        if "left" in parts:
            hands.add("LEFT")
        if "right" in parts:
            hands.add("RIGHT")
    return EvidenceItem(
        evidence_id=rule.rule_id,
        domain=Domain.PALMISTRY,
        evidence_class=EvidenceClass.RULE_EVALUATION,
        kind="PALM_RULE",
        bundle_ref=bundle.bundle_hash,
        status=rule.status.value,
        version_ref=rule.knowledge_version,
        source_profile=rule.source_profile,
        source_id=rule.source_id,
        source_location=rule.source_location,
        rule_version=rule.rule_version,
        fact_refs=tuple(rule.fact_refs),
        conflict_ids=tuple(sorted(rule.conflict_ids)),
        basis_ids=basis,
        missing_basis=missing,
        tags=tags,
        bundle_production_ready=bundle.production_ready,
        hands=frozenset(hands),
        lines=frozenset(lines),
        mounts=frozenset(mounts),
    )
