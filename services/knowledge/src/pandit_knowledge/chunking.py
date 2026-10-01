"""Deterministic, provenance-preserving chunking (KB-18, KB-19).

A *unit* is one passage that already has a single source, edition, location and methodology
profile (for example one Tarot card entry, or one structured statement rendered as text). A
unit is never merged with another unit and is split, if at all, only at sentence boundaries, so
every chunk keeps its unit's full provenance. The same input always gives the same chunks and
the same chunk identifiers (re-runnable); a chunk identifier changes only when its provenance or
text changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pandit_knowledge.models import (
    CHUNKING_VERSION,
    ChunkRecord,
    Confidence,
    KnowledgeDomain,
    ReadingLevel,
    TextFidelity,
    TextOrigin,
    sha256_hex,
)

DEFAULT_MAX_CHARS = 1200
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(‘“])")


@dataclass(frozen=True)
class ChunkUnit:
    """One passage with its provenance; the chunker adds only the sequence and the identifier."""

    text: str
    knowledge_domain: KnowledgeDomain
    language: str
    text_origin: TextOrigin
    text_fidelity: TextFidelity
    source_id: str
    edition_id: str
    source_location: str
    section_path: str
    parent_concept_id: str
    methodology_profile: str
    reading_level: ReadingLevel
    confidence: Confidence
    external_ref: str


def embedding_text(chunk: ChunkRecord) -> str:
    """The text that is embedded: the chunk's location (which names the card or the passage)
    followed by its text. Derived only from stored fields, so it is reproducible."""
    return f"{chunk.source_location}. {chunk.text}"


def split_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Greedy sentence packing. A single sentence longer than ``max_chars`` stays whole."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(text):
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > max_chars:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def chunk_unit(unit: ChunkUnit, max_chars: int = DEFAULT_MAX_CHARS) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for index, piece in enumerate(split_text(unit.text, max_chars)):
        key = "|".join(
            (
                unit.source_id,
                unit.edition_id,
                unit.source_location,
                unit.section_path,
                unit.methodology_profile,
                unit.language,
                str(index),
                piece,
            )
        )
        chunks.append(
            ChunkRecord(
                chunk_id="CH-" + sha256_hex(key)[:20],
                knowledge_domain=unit.knowledge_domain,
                text=piece,
                language=unit.language,
                text_origin=unit.text_origin,
                text_fidelity=unit.text_fidelity,
                source_id=unit.source_id,
                edition_id=unit.edition_id,
                source_location=unit.source_location,
                section_path=unit.section_path,
                sequence=index,
                parent_concept_id=unit.parent_concept_id,
                methodology_profile=unit.methodology_profile,
                reading_level=unit.reading_level,
                confidence=unit.confidence,
                external_ref=unit.external_ref,
                chunking_version=CHUNKING_VERSION,
            )
        )
    return chunks
