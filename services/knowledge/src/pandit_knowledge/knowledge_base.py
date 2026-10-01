"""Read access to the structured side of one sealed knowledge version (KB-27 to KB-34).

Everything returned is a source-profile record with its provenance. The accessor never merges
profiles, never ranks one source over another and never turns a mapping into a rule: a house to
domain mapping carries its :class:`SupportStatus`, and a pair that no source supports is
``NOT_EVALUABLE``. Rule logic stays in the rule engine; ``rule_references`` only say where a rule
lives.
"""

from __future__ import annotations

from typing import Any

from pandit_knowledge.models import (
    ConceptRecord,
    DomainMappingRecord,
    ExceptionRecord,
    RuleReferenceRecord,
    StatementKind,
    StatementRecord,
    TermRecord,
)
from pandit_knowledge.store import KnowledgeStore


def _strip(row: dict[str, Any], *extra: str) -> dict[str, Any]:
    drop = {"version_id", "content_hash", *extra}
    return {k: v for k, v in row.items() if k not in drop}


class KnowledgeBase:
    def __init__(self, store: KnowledgeStore, version_id: str) -> None:
        version = store.get_version(version_id)
        if version is None:
            raise KeyError(version_id)
        if version.status != "SEALED":
            raise ValueError("a knowledge base reads a sealed version only")
        self._store = store
        self.version_id = version_id

    def concept(self, concept_id: str) -> ConceptRecord:
        rows = self._store.select_rows(self.version_id, "concepts", {"concept_id": concept_id})
        if not rows:
            raise KeyError(concept_id)
        return ConceptRecord.model_validate(_strip(rows[0]))

    def concepts(self, concept_type: str | None = None) -> list[ConceptRecord]:
        where = {"concept_type": concept_type} if concept_type else None
        return [
            ConceptRecord.model_validate(_strip(r))
            for r in self._store.select_rows(self.version_id, "concepts", where)
        ]

    def statements(
        self,
        concept_id: str,
        kind: StatementKind | None = None,
        profile_id: str | None = None,
    ) -> list[StatementRecord]:
        where: dict[str, Any] = {"concept_id": concept_id}
        if kind is not None:
            where["statement_kind"] = kind.value
        if profile_id is not None:
            where["profile_id"] = profile_id
        return [
            StatementRecord.model_validate(_strip(r))
            for r in self._store.select_rows(self.version_id, "statements", where)
        ]

    def terms(self, concept_id: str) -> list[TermRecord]:
        return [
            TermRecord.model_validate(_strip(r))
            for r in self._store.select_rows(self.version_id, "terms", {"concept_id": concept_id})
        ]

    def rule_references(self, concept_id: str) -> list[RuleReferenceRecord]:
        return [
            RuleReferenceRecord.model_validate(_strip(r))
            for r in self._store.select_rows(
                self.version_id, "rule_references", {"concept_id": concept_id}
            )
        ]

    def exceptions(self, rule_id: str | None = None) -> list[ExceptionRecord]:
        where = {"affected_rule_id": rule_id} if rule_id else None
        return [
            ExceptionRecord.model_validate(_strip(r))
            for r in self._store.select_rows(self.version_id, "exceptions", where)
        ]

    def domain_mappings(
        self, domain_id: str | None = None, house_id: str | None = None
    ) -> list[DomainMappingRecord]:
        where: dict[str, Any] = {}
        if domain_id:
            where["domain_id"] = domain_id
        if house_id:
            where["concept_id"] = house_id
        return [
            DomainMappingRecord.model_validate(_strip(r))
            for r in self._store.select_rows(self.version_id, "domain_mappings", where or None)
        ]
