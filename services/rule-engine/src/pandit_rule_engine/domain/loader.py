"""Load and validate the Phase 17 domain ruleset (isolated from the Phase 6 Vedic ruleset).

``load_domain_ruleset(rules_dir)`` reads only domain documents (``domain_ruleset``,
``domain_taxonomy``, ``domain_rule``, ``domain_conflict``). A document of any other type is an
error, so this loader cannot absorb the Vedic ruleset; the Vedic loader in turn rejects the
domain document types, so neither can load the other. Every violation is collected and raised
together (:class:`DomainRulesetLoadError`):

* exactly one manifest and one taxonomy; the taxonomy covers every ``LifeDomain`` exactly once,
  its parent links are acyclic and the 27 ``Phases.md`` domains are exactly the roadmap ones;
* **no invented support**: a rule may exist only for a domain whose research status is not
  ``NOT_EVALUABLE`` and that has no static policy block; a conflicting mapping names a recorded
  conflict; a sub-domain's rule is its own (nothing is inherited);
* only the owner-locked divisional-chart mappings (D2, D3, D7, D9, D10, D12, D20, D24, each only
  for its approved domains; D4 never);
* the marriage dasha method serves Marriage only; the bhava transit method only a house the
  domain itself maps; the subject method only Subjects; a withheld rule never exposes tags;
* tags and notes contain no prohibited category (fertility outcomes, lifespan, death, disease...);
* identifiers are unique and in the ``DOM_`` namespace.

The ruleset hash is the SHA-256 of the canonical content of the validated documents, so a changed
rule changes it, and it is independent of the Phase 6 and Phase 13 ruleset hashes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pandit_contracts.domain import (
    DomainReason,
    DomainRuleKind,
    DomainSupport,
    LifeDomain,
    PolicyClass,
)
from pandit_contracts.palm_policy import ProhibitedCategory, find_prohibited
from pydantic import BaseModel, ValidationError

from pandit_rule_engine.domain.schema import (
    DomainConflict,
    DomainRuleDocument,
    DomainRulesetManifest,
    HouseParams,
    TaxonomyDocument,
    TaxonomyEntry,
    VargaParams,
    WithheldParams,
)

_DOCUMENT_TYPES: dict[str, type[BaseModel]] = {
    "domain_ruleset": DomainRulesetManifest,
    "domain_taxonomy": TaxonomyDocument,
    "domain_rule": DomainRuleDocument,
    "domain_conflict": DomainConflict,
}

#: Owner decision 3 (standards LD-09): the only divisional chart -> domain mappings.
ALLOWED_VARGA_DOMAINS: dict[int, frozenset[LifeDomain]] = {
    2: frozenset({LifeDomain.WEALTH, LifeDomain.FINANCE}),
    3: frozenset({LifeDomain.SIBLINGS}),
    7: frozenset({LifeDomain.CHILDREN}),
    9: frozenset({LifeDomain.MARRIAGE, LifeDomain.SPOUSE}),
    10: frozenset({LifeDomain.CAREER}),
    12: frozenset({LifeDomain.PARENTS}),
    20: frozenset({LifeDomain.SPIRITUALITY}),
    24: frozenset({LifeDomain.EDUCATION}),
}

#: Policy classes that an analysis may carry as a static gate.
_ADULT_GATED = frozenset({PolicyClass.ADULT_CONFIRMATION_REQUIRED})


#: Fertility is the name of a domain concept here (Children), so the palm lexicon's FERTILITY
#: category is replaced by the outcome words below; every other palm category applies to tags.
_TAG_OUTCOME_WORDS = (
    "infertil",
    "sterile",
    "barren",
    "pregnan",
    "conceiv",
    "miscarr",
    "abort",
    "childless",
    "illegitim",
)


def _tag_prohibited(tag: str) -> bool:
    text = tag.replace("_", " ").replace(".", " ")
    if any(w in text for w in _TAG_OUTCOME_WORDS):
        return True
    return any(hit.category is not ProhibitedCategory.FERTILITY for hit in find_prohibited(text))


class DomainRulesetLoadError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class DomainRuleset:
    manifest: DomainRulesetManifest
    taxonomy_version: str
    taxonomy: dict[LifeDomain, TaxonomyEntry]
    rules: dict[str, DomainRuleDocument]
    conflicts: dict[str, DomainConflict]
    content_hash: str
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)

    def entry(self, domain: LifeDomain) -> TaxonomyEntry:
        return self.taxonomy[domain]

    def parent_chain(self, domain: LifeDomain) -> tuple[LifeDomain, ...]:
        chain: list[LifeDomain] = []
        current = self.taxonomy[domain].parent
        while current is not None:
            chain.append(current)
            current = self.taxonomy[current].parent
        return tuple(chain)

    def effective_policy(self, domain: LifeDomain) -> tuple[PolicyClass, ...]:
        """The domain's own policy plus its ancestors' (policy inherits; support never does)."""
        found: set[PolicyClass] = set(self.taxonomy[domain].policy)
        for ancestor in self.parent_chain(domain):
            found |= set(self.taxonomy[ancestor].policy)
        return tuple(sorted(found, key=lambda p: p.value))

    def adult_confirmation_required(self, domain: LifeDomain) -> bool:
        return self.taxonomy[domain].adult_confirmation_required or any(
            self.taxonomy[a].adult_confirmation_required for a in self.parent_chain(domain)
        )

    def rules_for(self, domain: LifeDomain) -> tuple[DomainRuleDocument, ...]:
        return tuple(r for r in self.rules.values() if r.domain is domain and r.status == "active")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _read(path: Path, problems: list[str]) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
        documents = list(yaml.safe_load_all(text))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        problems.append(f"{path.name}: invalid YAML ({exc.__class__.__name__})")
        return []
    out: list[dict[str, Any]] = []
    for document in documents:
        if document is None:
            continue
        if not isinstance(document, dict):
            problems.append(f"{path.name}: document is not a mapping")
            continue
        out.append(document)
    return out


def _summ(exc: ValidationError) -> str:
    return "; ".join(".".join(str(p) for p in e["loc"]) + ": " + e["msg"] for e in exc.errors()[:3])


def load_domain_ruleset(rules_dir: Path) -> DomainRuleset:
    if not rules_dir.is_dir():
        raise DomainRulesetLoadError([f"domain rules directory not found: {rules_dir.name}"])
    problems: list[str] = []
    manifests: list[DomainRulesetManifest] = []
    taxonomies: list[TaxonomyDocument] = []
    rules: dict[str, DomainRuleDocument] = {}
    conflicts: dict[str, DomainConflict] = {}
    canonical: dict[str, dict[str, Any]] = {}

    files = sorted(
        (p for p in rules_dir.rglob("*") if p.suffix in {".yaml", ".yml"}),
        key=lambda p: p.relative_to(rules_dir).as_posix(),
    )
    for path in files:
        relative = path.relative_to(rules_dir).as_posix()
        for document in _read(path, problems):
            kind = document.get("document_type")
            model = _DOCUMENT_TYPES.get(str(kind))
            if model is None:
                problems.append(
                    f"{relative}: unknown document_type {kind!r} (not a domain document)"
                )
                continue
            try:
                parsed = model.model_validate(document)
            except ValidationError as exc:
                problems.append(f"{relative}: schema validation failed: {_summ(exc)}")
                continue
            dump = parsed.model_dump(mode="json")
            if isinstance(parsed, DomainRulesetManifest):
                manifests.append(parsed)
                canonical["ruleset:" + parsed.ruleset_id] = dump
            elif isinstance(parsed, TaxonomyDocument):
                taxonomies.append(parsed)
                canonical["taxonomy:" + parsed.taxonomy_version] = dump
            elif isinstance(parsed, DomainRuleDocument):
                if parsed.rule_id in rules:
                    problems.append(f"{relative}: duplicate rule_id {parsed.rule_id}")
                    continue
                rules[parsed.rule_id] = parsed
                canonical["rule:" + parsed.rule_id] = dump
            else:
                assert isinstance(parsed, DomainConflict)
                if parsed.conflict_id in conflicts:
                    problems.append(f"{relative}: duplicate conflict {parsed.conflict_id}")
                    continue
                conflicts[parsed.conflict_id] = parsed
                canonical["conflict:" + parsed.conflict_id] = dump

    if len(manifests) != 1:
        problems.append(f"expected exactly one domain ruleset manifest, found {len(manifests)}")
    if len(taxonomies) != 1:
        problems.append(f"expected exactly one domain taxonomy, found {len(taxonomies)}")
    taxonomy: dict[LifeDomain, TaxonomyEntry] = {}
    if len(taxonomies) == 1:
        taxonomy = _check_taxonomy(taxonomies[0], problems)
    if taxonomy:
        _check_rules(rules, conflicts, taxonomy, problems)
        _check_unruled(rules, taxonomy, problems)
    if problems or not manifests or not taxonomies:
        raise DomainRulesetLoadError(problems)
    payload = {"documents": [canonical[k] for k in sorted(canonical)]}
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return DomainRuleset(
        manifest=manifests[0],
        taxonomy_version=taxonomies[0].taxonomy_version,
        taxonomy=taxonomy,
        rules={k: rules[k] for k in sorted(rules)},
        conflicts={k: conflicts[k] for k in sorted(conflicts)},
        content_hash=digest,
        documents={k: canonical[k] for k in sorted(canonical)},
    )


def _check_taxonomy(doc: TaxonomyDocument, problems: list[str]) -> dict[LifeDomain, TaxonomyEntry]:
    entries: dict[LifeDomain, TaxonomyEntry] = {}
    for entry in doc.entries:
        if entry.domain in entries:
            problems.append(f"taxonomy: duplicate domain {entry.domain.value}")
            continue
        entries[entry.domain] = entry
    missing = [d.value for d in LifeDomain if d not in entries]
    if missing:
        problems.append("taxonomy: missing domains " + ", ".join(missing))
    all_domains = tuple(LifeDomain)
    for index, domain in enumerate(all_domains):
        found = entries.get(domain)
        if found is None:
            continue
        entry = found
        expected = "PHASES_MD" if index < 27 else "EXTENSION"
        if entry.kind != expected:
            problems.append(f"taxonomy: {domain.value} must be {expected}")
        if entry.parent is not None and entry.parent not in entries:
            problems.append(f"taxonomy: {domain.value} has an unknown parent")
    for domain, entry in entries.items():
        seen: set[LifeDomain] = {domain}
        current = entry.parent
        while current is not None:
            if current in seen:
                problems.append(f"taxonomy: parent cycle at {domain.value}")
                break
            seen.add(current)
            parent_entry = entries.get(current)
            current = parent_entry.parent if parent_entry else None
        if (
            entry.support is DomainSupport.NOT_EVALUABLE
            and entry.not_evaluable_reason is None
            and (entry.blocked_reason is None)
        ):
            problems.append(f"taxonomy: {domain.value} is NOT_EVALUABLE without a typed reason")
        if entry.support is not DomainSupport.NOT_EVALUABLE and entry.blocked_reason is not None:
            problems.append(f"taxonomy: {domain.value} is blocked yet claims support")
    return entries


def _house_rules(rules: dict[str, DomainRuleDocument], domain: LifeDomain) -> set[int]:
    return {
        r.params.house
        for r in rules.values()
        if r.domain is domain and isinstance(r.params, HouseParams)
    }


def _check_rules(
    rules: dict[str, DomainRuleDocument],
    conflicts: dict[str, DomainConflict],
    taxonomy: dict[LifeDomain, TaxonomyEntry],
    problems: list[str],
) -> None:
    for rule in rules.values():
        rid = rule.rule_id
        entry = taxonomy[rule.domain]
        if entry.support is DomainSupport.NOT_EVALUABLE:
            problems.append(
                f"{rid}: {rule.domain.value} is NOT_EVALUABLE; no rule may exist for it"
            )
        if entry.blocked_reason is not None:
            problems.append(
                f"{rid}: {rule.domain.value} is policy-blocked; no rule may exist for it"
            )
        for cid in rule.conflict_ids:
            if cid not in conflicts:
                problems.append(f"{rid}: unknown conflict {cid}")
        if rule.support is DomainSupport.UNRESOLVED_CONFLICT and not rule.conflict_ids:
            problems.append(f"{rid}: a conflicting mapping must name its conflict")
        if rule.kind is DomainRuleKind.VARGA_RELEVANCE:
            assert isinstance(rule.params, VargaParams)
            allowed = ALLOWED_VARGA_DOMAINS.get(rule.params.varga, frozenset())
            if rule.domain not in allowed:
                problems.append(
                    f"{rid}: D{rule.params.varga} is not an approved mapping "
                    f"for {rule.domain.value}"
                )
        if (
            rule.kind is DomainRuleKind.MARRIAGE_DASHA_METHOD
            and rule.domain is not LifeDomain.MARRIAGE
        ):
            problems.append(f"{rid}: the marriage dasha method serves Marriage only")
        if (
            rule.kind is DomainRuleKind.SUBJECT_PROFICIENCY
            and rule.domain is not LifeDomain.SUBJECTS
        ):
            problems.append(f"{rid}: the subject method serves Subjects only")
        if rule.kind is DomainRuleKind.BHAVA_TRANSIT_METHOD:
            house = rule.params.house  # type: ignore[union-attr]
            if house not in _house_rules(rules, rule.domain):
                problems.append(
                    f"{rid}: house {house} is not a house this domain maps itself (no inheritance)"
                )
        for tag in (*rule.tags.domain_tags, *rule.tags.signification_tags):
            if _tag_prohibited(tag):
                problems.append(f"{rid}: tag {tag!r} falls in a prohibited category")
        if isinstance(rule.params, WithheldParams) and rule.params.reason not in set(DomainReason):
            problems.append(f"{rid}: unknown withheld reason")


def _check_unruled(
    rules: dict[str, DomainRuleDocument],
    taxonomy: dict[LifeDomain, TaxonomyEntry],
    problems: list[str],
) -> None:
    ruled = {r.domain for r in rules.values() if r.status == "active"}
    for domain, entry in taxonomy.items():
        if domain in ruled or entry.blocked_reason is not None:
            continue
        if entry.not_evaluable_reason is None:
            problems.append(
                f"taxonomy: {domain.value} has no active rule and states no not_evaluable_reason"
            )


def _chain(taxonomy: dict[LifeDomain, TaxonomyEntry], domain: LifeDomain) -> list[LifeDomain]:
    out: list[LifeDomain] = []
    current = taxonomy[domain].parent
    while current is not None:
        out.append(current)
        current = taxonomy[current].parent
    return out
