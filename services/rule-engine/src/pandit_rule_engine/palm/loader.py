"""Load and validate the palm ruleset (Phase 13; isolated from the Vedic ruleset).

``load_palm_ruleset(rules_dir, coverage)`` reads **only** palm documents. A document of any other
type (a Vedic ``rule``, ``table`` or ``ruleset``) is an error, so the palm loader cannot absorb
the Vedic ruleset; the Vedic loader in turn rejects the palm document types, so neither can load
the other. Every violation of the rules below is collected and raised together
(:class:`PalmRulesetLoadError`):

* exactly one palm ruleset manifest, at the palm standards version, methodology ``PALM_WESTERN``;
* rule identifiers are in the ``PALMR_`` namespace and unique;
* every rule has exactly one source profile and one source location, and both must be backed by
  the **source coverage manifest** with every concept the rule depends on (read and supported):
  an unread, unsupported or excluded concept cannot back a rule;
* interpretation tags come from the closed tag vocabulary; the vocabulary, the tags and every
  rule text field pass the prohibited-interpretation scan (standards PM-13, PM-25);
* referenced conflicts exist; a rule names no event prediction.

The ruleset hash is the SHA-256 of the canonical content of the validated documents, so a
changed rule changes it, and it is independent of the Vedic ruleset hash.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pandit_contracts.palm_canonical import sha256_hex
from pandit_contracts.palm_coverage import PalmSourceCoverage
from pandit_contracts.palm_policy import find_prohibited
from pydantic import BaseModel, ValidationError

from pandit_rule_engine.palm.schema import (
    PALM_STANDARDS_VERSION,
    PALM_TAG,
    PalmConflict,
    PalmRule,
    PalmRulesetManifest,
    PalmTagVocabulary,
)

_DOCUMENT_TYPES: dict[str, type[BaseModel]] = {
    "palm_ruleset": PalmRulesetManifest,
    "palm_rule": PalmRule,
    "palm_tag_vocabulary": PalmTagVocabulary,
    "palm_conflict": PalmConflict,
}


class PalmRulesetLoadError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class PalmRuleset:
    manifest: PalmRulesetManifest
    rules: dict[str, PalmRule]
    tags: dict[str, str]  # tag -> claim_kind
    conflicts: dict[str, PalmConflict]
    content_hash: str

    @property
    def ruleset_id(self) -> str:
        return self.manifest.ruleset_id


def _scan(text: str, where: str, problems: list[str]) -> None:
    for match in find_prohibited(text):
        problems.append(
            f"{where}: prohibited interpretation ({match.category.value}: {match.term!r})"
        )


def load_documents(rules_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    if not rules_dir.is_dir():
        raise PalmRulesetLoadError([f"palm rules directory not found: {rules_dir.name}"])
    problems: list[str] = []
    documents: list[tuple[str, dict[str, Any]]] = []
    files = sorted(
        (p for p in rules_dir.rglob("*") if p.suffix in {".yaml", ".yml"}),
        key=lambda p: p.relative_to(rules_dir).as_posix(),
    )
    for path in files:
        relative = path.relative_to(rules_dir).as_posix()
        try:
            for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
                if not isinstance(doc, dict):
                    problems.append(f"{relative}: document is not a mapping")
                    continue
                documents.append((relative, doc))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            problems.append(f"{relative}: invalid YAML ({exc.__class__.__name__})")
    if problems:
        raise PalmRulesetLoadError(problems)
    return documents


def load_palm_ruleset(
    rules_dir: Path,
    coverage: PalmSourceCoverage,
    *,
    reserved_ids: frozenset[str] = frozenset(),
) -> PalmRuleset:
    """Load, validate and register the palm ruleset in ``rules_dir`` against ``coverage``.

    ``reserved_ids`` are identifiers that must not be used (for example the Vedic rule ids), so
    the two namespaces stay disjoint.
    """
    problems: list[str] = []
    manifests: list[PalmRulesetManifest] = []
    rules: dict[str, PalmRule] = {}
    vocabularies: list[PalmTagVocabulary] = []
    conflicts: dict[str, PalmConflict] = {}
    canonical: dict[str, Any] = {}

    for relative, doc in load_documents(rules_dir):
        kind = doc.get("document_type")
        model = _DOCUMENT_TYPES.get(str(kind))
        if model is None:
            problems.append(f"{relative}: {kind!r} is not a palm document type")
            continue
        try:
            parsed = model.model_validate(doc)
        except ValidationError as exc:
            problems.append(f"{relative}: schema validation failed: {exc.error_count()} error(s)")
            continue
        if isinstance(parsed, PalmRulesetManifest):
            manifests.append(parsed)
            canonical["ruleset:" + parsed.ruleset_id] = parsed.model_dump(mode="json")
        elif isinstance(parsed, PalmRule):
            if parsed.rule_id in rules:
                problems.append(f"{relative}: duplicate rule_id {parsed.rule_id}")
                continue
            rules[parsed.rule_id] = parsed
            canonical["rule:" + parsed.rule_id] = parsed.model_dump(mode="json")
        elif isinstance(parsed, PalmTagVocabulary):
            vocabularies.append(parsed)
            canonical["vocabulary:" + parsed.vocabulary_id] = parsed.model_dump(mode="json")
        elif isinstance(parsed, PalmConflict):
            conflicts[parsed.conflict_id] = parsed
            canonical["conflict:" + parsed.conflict_id] = parsed.model_dump(mode="json")

    if len(manifests) != 1:
        problems.append(f"expected exactly one palm ruleset manifest, found {len(manifests)}")
    manifest = manifests[0] if manifests else None
    if manifest is not None and manifest.standards_version != PALM_STANDARDS_VERSION:
        problems.append(
            f"manifest standards_version {manifest.standards_version} "
            f"is not {PALM_STANDARDS_VERSION}"
        )
    if len(vocabularies) != 1:
        problems.append(f"expected exactly one palm tag vocabulary, found {len(vocabularies)}")

    tags: dict[str, str] = {}
    for vocabulary in vocabularies:
        for entry in vocabulary.tags:
            if not PALM_TAG.match(entry.tag):
                problems.append(f"tag {entry.tag!r} does not have the tag shape")
            if entry.tag in tags:
                problems.append(f"duplicate tag {entry.tag}")
            tags[entry.tag] = entry.claim_kind
            _scan(entry.tag, f"tag {entry.tag}", problems)
            _scan(entry.description, f"tag {entry.tag} description", problems)

    for rule in rules.values():
        where = rule.rule_id
        if manifest is not None and rule.ruleset_id != manifest.ruleset_id:
            problems.append(f"{where}: ruleset_id {rule.ruleset_id} differs from the manifest")
        if rule.rule_id in reserved_ids:
            problems.append(f"{where}: identifier collides with a reserved (Vedic) identifier")
        for tag in rule.interpretation_tags:
            if tag not in tags:
                problems.append(f"{where}: tag {tag} is not in the closed tag vocabulary")
            elif tags[tag] != rule.claim_kind:
                problems.append(
                    f"{where}: tag {tag} has claim kind {tags[tag]}, not {rule.claim_kind}"
                )
            _scan(tag, f"{where} tag", problems)
        for field in (rule.source_note, rule.source_location):
            _scan(field, f"{where} text", problems)
        for conflict_id in rule.known_conflicts:
            if conflict_id not in conflicts:
                problems.append(f"{where}: unknown conflict {conflict_id}")
        problems += [
            f"{where}: {p}"
            for p in coverage.problems_for_rule(
                rule.source_profile, rule.source_location, rule.concepts
            )
        ]
    for conflict in conflicts.values():
        _scan(conflict.summary, f"conflict {conflict.conflict_id}", problems)

    if problems or manifest is None:
        raise PalmRulesetLoadError(problems)
    ordered = {k: canonical[k] for k in sorted(canonical)}
    return PalmRuleset(
        manifest=manifest,
        rules={k: rules[k] for k in sorted(rules)},
        tags=tags,
        conflicts={k: conflicts[k] for k in sorted(conflicts)},
        content_hash=sha256_hex(ordered),
    )
