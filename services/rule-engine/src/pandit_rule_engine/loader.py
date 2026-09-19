"""Rule loader (Phase 6B): deterministic loading and registration.

Rules live as YAML under `services/knowledge/rules/`, grouped by source
tradition (`bphs/`, `phaladeepika/`, `jataka_parijata/`, `modern/`;
`docs/ARCHITECTURE.md` §7). The loader

- reads every `*.yaml` / `*.yml` file in sorted relative-path order, so the
  result never depends on filesystem traversal order;
- parses with `yaml.safe_load`-equivalent semantics and rejects duplicate
  mapping keys (a silent overwrite would make a rule's meaning depend on
  file layout);
- validates each document with the typed schema (`schema.py`);
- requires exactly one `ruleset` manifest and a matching `standards_version`
  on every rule and table;
- rejects duplicate rule IDs and table IDs, unknown `rule_result` targets
  and dependency cycles between rules.

All problems are collected and raised together as a `RulesetLoadError`, so a
broken ruleset is reported completely rather than one error at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from pandit_rule_engine.schema import (
    AllOf,
    AnyOf,
    Condition,
    CountAtLeast,
    Exists,
    ForAll,
    Not,
    Rule,
    RuleResultIs,
    RulesetManifest,
    TableDocument,
)
from pandit_rule_engine.tables import validate_table_data

_DOCUMENT_TYPES = frozenset({"rule", "table", "ruleset"})
_SKIPPED_NAMES = {"README.md"}


class RulesetLoadError(Exception):
    """Raised with every problem found while loading a ruleset."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


class _UniqueKeyLoader(yaml.SafeLoader):
    """`SafeLoader` that rejects duplicate mapping keys."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


@dataclass(frozen=True)
class Ruleset:
    """A validated, registered ruleset.

    `rules` is keyed by rule ID in registration (sorted-ID) order.
    `evaluation_order` lists active rule IDs so that every rule appears after
    the rules it depends on (`rule_result`), breaking ties by
    (priority, rule_id) -- priority orders evaluation only and never
    influences a result.
    """

    manifest: RulesetManifest
    rules: dict[str, Rule]
    tables: dict[str, TableDocument]
    evaluation_order: tuple[str, ...]
    #: Canonical logical documents, keyed by ID; used for hashing.
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        from pandit_rule_engine.hashing import ruleset_content_hash

        return ruleset_content_hash(self)


def _referenced_rule_ids(condition: Condition) -> set[str]:
    if isinstance(condition, RuleResultIs):
        return {condition.rule_id}
    if isinstance(condition, (AllOf, AnyOf)):
        found: set[str] = set()
        for arg in condition.args:
            found |= _referenced_rule_ids(arg)
        return found
    if isinstance(condition, Not):
        return _referenced_rule_ids(condition.arg)
    if isinstance(condition, (Exists, ForAll, CountAtLeast)):
        return _referenced_rule_ids(condition.where)
    return set()


def rule_dependencies(rule: Rule) -> set[str]:
    """Rule IDs this rule reads through `rule_result` conditions."""
    found: set[str] = set()
    if rule.conditions is not None:
        found |= _referenced_rule_ids(rule.conditions)
    for reading in rule.readings:
        found |= _referenced_rule_ids(reading.conditions)
    for exception in rule.exceptions:
        found |= _referenced_rule_ids(exception.when)
    for cancellation in rule.cancellations:
        found |= _referenced_rule_ids(cancellation.when)
    return found


def _order_rules(rules: dict[str, Rule], problems: list[str]) -> tuple[str, ...]:
    active = {rule_id: rule for rule_id, rule in rules.items() if rule.status == "active"}
    deps = {rule_id: rule_dependencies(rule) for rule_id, rule in active.items()}
    for rule_id, needed in deps.items():
        for target in sorted(needed):
            if target not in rules:
                problems.append(f"{rule_id}: rule_result refers to unknown rule {target}")
            elif target not in active:
                problems.append(f"{rule_id}: rule_result refers to inactive rule {target}")
    ordered: list[str] = []
    done: set[str] = set()
    remaining = set(active)
    while remaining:
        ready = sorted(
            (
                rule_id
                for rule_id in remaining
                if all(dep in done or dep not in active for dep in deps[rule_id])
            ),
            key=lambda rule_id: (active[rule_id].priority, rule_id),
        )
        if not ready:
            problems.append("rule dependency cycle among: " + ", ".join(sorted(remaining)))
            return tuple(ordered)
        chosen = ready[0]
        ordered.append(chosen)
        done.add(chosen)
        remaining.remove(chosen)
    return tuple(ordered)


def load_documents(rules_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Read every YAML document under `rules_dir` in sorted relative-path order.

    Returns (relative POSIX path, mapping) pairs. Raises `RulesetLoadError`
    for unreadable or invalid YAML and for non-mapping documents.
    """
    if not rules_dir.is_dir():
        raise RulesetLoadError([f"rules directory not found: {rules_dir.name}"])
    problems: list[str] = []
    documents: list[tuple[str, dict[str, Any]]] = []
    files = sorted(
        (path for path in rules_dir.rglob("*") if path.suffix in {".yaml", ".yml"}),
        key=lambda path: path.relative_to(rules_dir).as_posix(),
    )
    for path in files:
        relative = path.relative_to(rules_dir).as_posix()
        if path.name in _SKIPPED_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            for document in yaml.load_all(text, Loader=_UniqueKeyLoader):
                if not isinstance(document, dict):
                    problems.append(f"{relative}: document is not a mapping")
                    continue
                documents.append((relative, document))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            problems.append(f"{relative}: invalid YAML ({exc.__class__.__name__})")
    if problems:
        raise RulesetLoadError(problems)
    return documents


def load_ruleset(rules_dir: Path) -> Ruleset:
    """Load, validate and register the ruleset in `rules_dir`."""
    problems: list[str] = []
    manifests: list[RulesetManifest] = []
    rules: dict[str, Rule] = {}
    tables: dict[str, TableDocument] = {}
    canonical: dict[str, dict[str, Any]] = {}

    for relative, document in load_documents(rules_dir):
        document_type = document.get("document_type")
        if document_type not in _DOCUMENT_TYPES:
            problems.append(f"{relative}: unknown document_type {document_type!r}")
            continue
        try:
            parsed: RulesetManifest | Rule | TableDocument
            if document_type == "rule":
                parsed = Rule.model_validate(document)
            elif document_type == "table":
                parsed = TableDocument.model_validate(document)
            else:
                parsed = RulesetManifest.model_validate(document)
        except ValidationError as exc:
            problems.append(f"{relative}: schema validation failed: {_summarize(exc)}")
            continue
        if isinstance(parsed, RulesetManifest):
            manifests.append(parsed)
            canonical["ruleset:" + parsed.ruleset_id] = parsed.model_dump(
                mode="json", by_alias=True
            )
        elif isinstance(parsed, Rule):
            if parsed.rule_id in rules:
                problems.append(f"{relative}: duplicate rule_id {parsed.rule_id}")
                continue
            rules[parsed.rule_id] = parsed
            canonical["rule:" + parsed.rule_id] = parsed.model_dump(mode="json", by_alias=True)
        else:
            if parsed.table_id in tables:
                problems.append(f"{relative}: duplicate table_id {parsed.table_id}")
                continue
            try:
                validate_table_data(parsed)
            except ValidationError as exc:
                problems.append(f"{relative}: table data invalid: {_summarize(exc)}")
                continue
            tables[parsed.table_id] = parsed
            canonical["table:" + parsed.table_id] = parsed.model_dump(mode="json", by_alias=True)

    if len(manifests) != 1:
        problems.append(f"expected exactly one ruleset manifest, found {len(manifests)}")
    manifest = manifests[0] if manifests else None
    if manifest is not None:
        for rule in rules.values():
            if rule.standards_version != manifest.standards_version:
                problems.append(
                    f"{rule.rule_id}: standards_version {rule.standards_version} "
                    f"does not match ruleset {manifest.standards_version}"
                )
        for table in tables.values():
            if table.standards_version != manifest.standards_version:
                problems.append(
                    f"{table.table_id}: standards_version {table.standards_version} "
                    f"does not match ruleset {manifest.standards_version}"
                )

    sorted_rules = {rule_id: rules[rule_id] for rule_id in sorted(rules)}
    order = _order_rules(sorted_rules, problems)
    if problems or manifest is None:
        raise RulesetLoadError(problems)
    return Ruleset(
        manifest=manifest,
        rules=sorted_rules,
        tables={table_id: tables[table_id] for table_id in sorted(tables)},
        evaluation_order=order,
        documents={key: canonical[key] for key in sorted(canonical)},
    )


def _summarize(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:3]:
        location = ".".join(str(item) for item in error["loc"])
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)
