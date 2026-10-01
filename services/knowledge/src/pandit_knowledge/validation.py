"""Audit checks for the knowledge corpus and for stored versions (KB-33, KB-36).

* :func:`find_personal_data` -- the corpus is static domain content and must hold no personal
  data (e-mail addresses, phone-number-like digit runs, calendar dates written as a birth date).
* :func:`verify_version` -- recompute every stored row's content hash and check that every chunk
  of a sealed version has an embedding, so a silent edit or a missing vector is detectable.
"""

from __future__ import annotations

import re
from typing import Any

from pandit_knowledge.content import KnowledgeContent, all_chunks
from pandit_knowledge.models import (
    ChunkRecord,
    ConceptRecord,
    DomainMappingRecord,
    EditionRecord,
    ExceptionRecord,
    RuleReferenceRecord,
    SourceRecord,
    StatementRecord,
    TermRecord,
)
from pandit_knowledge.store import KnowledgeStore

_PATTERNS: dict[str, re.Pattern[str]] = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE_LIKE": re.compile(r"(?<!\d)(?:\+?\d[\s-]?){10,}(?!\d)"),
    "NUMERIC_DATE": re.compile(
        r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b|\b(?:19|20)\d{2}-\d{2}-\d{2}\b"
    ),
    "COORDINATES": re.compile(r"\b\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}\b"),
    "URL_CREDENTIALS": re.compile(r"://[^/\s:@]+:[^/\s@]+@"),
}

_MODELS: dict[str, Any] = {
    "sources": SourceRecord,
    "source_editions": EditionRecord,
    "concepts": ConceptRecord,
    "statements": StatementRecord,
    "terms": TermRecord,
    "rule_references": RuleReferenceRecord,
    "domain_mappings": DomainMappingRecord,
    "exceptions": ExceptionRecord,
}


def find_personal_data(text: str) -> list[str]:
    """Names of the personal-data patterns found in ``text`` (empty when clean)."""
    return [name for name, pattern in _PATTERNS.items() if pattern.search(text)]


def content_text_fields(content: KnowledgeContent) -> list[tuple[str, str]]:
    """Every free-text field of the curated content, labelled for error messages."""
    out: list[tuple[str, str]] = []
    for chunk in all_chunks(content):
        out.append((f"chunk {chunk.chunk_id}", chunk.text))
    for st in content.statements:
        out.append((f"statement {st.statement_id}", str(st.attributes)))
    for term in content.terms:
        out.append((f"term {term.term_id}", term.text))
    for exc in content.exceptions:
        out.append(
            (f"exception {exc.exception_id}", f"{exc.condition_summary} {exc.conflict_note}")
        )
    for mapping in content.domain_mappings:
        out.append((f"mapping {mapping.mapping_id}", mapping.bridge_note))
    for source in content.sources:
        out.append((f"source {source.source_id}", f"{source.copyright_note} {source.title}"))
    return out


def personal_data_findings(content: KnowledgeContent) -> list[str]:
    findings = []
    for label, text in content_text_fields(content):
        for name in find_personal_data(text):
            findings.append(f"{label}: {name}")
    return findings


def verify_version(store: KnowledgeStore, version_id: str) -> list[str]:
    """Return a list of problems (empty when the stored version is intact and complete)."""
    problems: list[str] = []
    version = store.get_version(version_id)
    if version is None:
        return [f"unknown version {version_id}"]
    if version.status != "SEALED":
        problems.append("version is not sealed")
    for table, model in _MODELS.items():
        for row in store.select_rows(version_id, table):
            stored = row["content_hash"]
            data = {k: v for k, v in row.items() if k not in {"version_id", "content_hash"}}
            if model.model_validate(data).content_hash() != stored:
                problems.append(f"{table}: content hash mismatch")
    chunk_rows = store.select_rows(version_id, "chunks")
    for row in chunk_rows:
        data = {
            k: v for k, v in row.items() if k not in {"version_id", "content_hash", "char_count"}
        }
        chunk = ChunkRecord.model_validate(data)
        if chunk.content_hash() != row["content_hash"]:
            problems.append(f"chunks: content hash mismatch for {row['chunk_id']}")
        if chunk.char_count != row["char_count"]:
            problems.append(f"chunks: char_count mismatch for {row['chunk_id']}")
    embedded = store.embedded_chunk_ids(version_id, version.manifest.embedding_config_id)
    missing = {r["chunk_id"] for r in chunk_rows} - embedded
    if missing:
        problems.append(f"{len(missing)} chunks have no embedding")
    for table, count in version.manifest.record_counts.items():
        actual = len(store.select_rows(version_id, table))
        if actual != count:
            problems.append(f"{table}: manifest says {count}, store holds {actual}")
    return problems
