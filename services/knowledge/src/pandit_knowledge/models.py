"""Knowledge records and vocabularies (Phase 12; `docs/ASTROLOGY_STANDARDS.md` v1.26.0 KB-xx).

Every record is a frozen, ``extra=forbid`` pydantic model with a deterministic content
hash. Identifiers are language-neutral (``PLANET.SUN``, ``HOUSE.10``, ``SIG.SOUL``); the
language of any text is a separate field, never part of an identifier.

Five concepts stay separate (KB-01): CALCULATION, RULE, KNOWLEDGE, INTERPRETATION and
NARRATION. This package holds KNOWLEDGE and source-backed INTERPRETATION records only. It
never calculates, never evaluates a rule and never narrates.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

STANDARDS_VERSION = "1.26.0"
KNOWLEDGE_SCHEMA_VERSION = "1.0.0"
INGESTION_VERSION = "1.0.0"
CHUNKING_VERSION = "1.0.0"
MAX_TOP_K = 50
# Cosine-distance floor for a hit (bounded retrieval, not a relevance claim): a candidate farther
# than this is treated as unrelated.
DEFAULT_MAX_DISTANCE = 0.8


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConceptType(str, Enum):
    PLANET = "PLANET"
    HOUSE = "HOUSE"
    DOMAIN = "DOMAIN"
    TERM = "TERM"
    TAROT_CARD = "TAROT_CARD"
    CONCEPT = "CONCEPT"


class StatementKind(str, Enum):
    """What a structured statement says about its concept."""

    SIGNIFICATION = "SIGNIFICATION"  # what the source says the planet or house indicates
    ROLE = "ROLE"  # the planet's allegorical rank in the source (not a fact about a chart)
    HOUSE_KARAKA = "HOUSE_KARAKA"  # the source's planetary significator(s) of a house
    DERIVED_INVERSION = "DERIVED_INVERSION"  # mechanical inversion of a source table
    STRENGTH_NOTE = "STRENGTH_NOTE"  # a source remark about strength; never a threshold
    SOURCE_VARIANCE = "SOURCE_VARIANCE"  # recorded difference between two source profiles


class SupportStatus(str, Enum):
    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    PROJECT_DERIVED = "PROJECT_DERIVED"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ReadingLevel(str, Enum):
    """How the content was actually read. Never stronger than what was done (KB-05)."""

    SANSKRIT_LEVEL = "SANSKRIT_LEVEL"
    TRANSLATION_LEVEL = "TRANSLATION_LEVEL"
    PAGE_IMAGE_LEVEL = "PAGE_IMAGE_LEVEL"
    OCR_LEVEL = "OCR_LEVEL"
    TRANSCRIPTION_LEVEL = (
        "TRANSCRIPTION_LEVEL"  # a proofread web transcription of an English original
    )
    SECONDARY_REFERENCE = "SECONDARY_REFERENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # project-derived records


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IngestionPermission(str, Enum):
    """What the project may store of a source (KB-12; `LEGAL_REGULATIONS.md` AI/IP)."""

    FACTS_AND_CITATIONS_ONLY = "FACTS_AND_CITATIONS_ONLY"
    FULL_TEXT_PUBLIC_DOMAIN = "FULL_TEXT_PUBLIC_DOMAIN"
    LOCATION_ONLY = "LOCATION_ONLY"
    DEFERRED_UNRESOLVED = "DEFERRED_UNRESOLVED"


class TextOrigin(str, Enum):
    SOURCE_TEXT = "SOURCE_TEXT"  # verbatim from a source (public domain only)
    SOURCE_TERMS = "SOURCE_TERMS"  # short source renderings inside a structured record
    PROJECT_RENDERING = "PROJECT_RENDERING"  # generated from structured records; not source text


class TextFidelity(str, Enum):
    PROOFREAD_TRANSCRIPTION = "PROOFREAD_TRANSCRIPTION"
    OCR_UNCORRECTED = "OCR_UNCORRECTED"
    TEMPLATE_RENDERING = "TEMPLATE_RENDERING"


class KnowledgeDomain(str, Enum):
    VEDIC = "VEDIC"
    TAROT = "TAROT"


class RuleKind(str, Enum):
    RULE = "RULE"
    TABLE = "TABLE"
    PROFILE = "PROFILE"  # a Phase 9-11 methodology profile implemented in astro-engine


def canonical_json(value: Any) -> str:
    """Deterministic JSON used for every content hash."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(value: Any) -> str:
    text = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SourceRecord(_Model):
    source_id: str
    title: str
    author: str
    tradition: str
    original_language: str
    source_classification: str
    copyright_status: str
    ingestion_permission: IngestionPermission
    copyright_note: str
    registry_ref: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class EditionRecord(_Model):
    edition_id: str
    source_id: str
    edition_label: str
    translator: str
    publisher: str
    publication_year: str
    language: str
    location_url: str
    reading_level: ReadingLevel
    registry_verification_level: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class ConceptRecord(_Model):
    concept_id: str
    concept_type: ConceptType
    canonical_key: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class StatementRecord(_Model):
    statement_id: str
    concept_id: str
    statement_kind: StatementKind
    profile_id: str
    edition_id: str
    source_location: str
    location_kind: Literal["verse", "note", "derived", "verse_and_note"]
    reading_level: ReadingLevel
    registry_verification_level: str
    confidence: Confidence
    support_status: SupportStatus
    language: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class TermRecord(_Model):
    term_id: str
    concept_id: str
    term_kind: Literal["NAME", "ALIAS", "RENDERING"]
    script: str
    language: str
    text: str
    profile_id: str
    edition_id: str
    source_location: str
    verification_status: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class RuleReferenceRecord(_Model):
    reference_id: str
    concept_id: str
    rule_id: str
    rule_kind: RuleKind
    relation: str
    profile_id: str
    source_location: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class DomainMappingRecord(_Model):
    mapping_id: str
    domain_id: str
    concept_id: str
    support_status: SupportStatus
    supporting_statement_ids: tuple[str, ...]
    profile_id: str
    bridge_note: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class ExceptionRecord(_Model):
    exception_id: str
    affected_rule_id: str
    affected_concept_id: str
    profile_id: str
    edition_id: str
    source_location: str
    condition_summary: str
    effect: str
    confidence: Confidence
    conflict_note: str

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class ChunkRecord(_Model):
    chunk_id: str
    knowledge_domain: KnowledgeDomain
    text: str
    language: str
    text_origin: TextOrigin
    text_fidelity: TextFidelity
    source_id: str
    edition_id: str
    source_location: str
    section_path: str
    sequence: int
    parent_concept_id: str
    methodology_profile: str
    reading_level: ReadingLevel
    confidence: Confidence
    external_ref: str
    chunking_version: str = CHUNKING_VERSION

    @property
    def char_count(self) -> int:
        return len(self.text)

    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class EmbeddingConfig(_Model):
    """Identifies one embedding setup. Changing any field makes a new configuration (KB-20)."""

    provider: str
    model: str
    model_version: str
    dimension: int
    metric: Literal["cosine"] = "cosine"
    config_version: str
    is_semantic: bool
    languages_declared: tuple[str, ...] = ()

    @property
    def embedding_config_id(self) -> str:
        return "EC-" + sha256_hex(self.model_dump(mode="json"))[:16]


class VersionManifest(_Model):
    """What a knowledge version is made of. The snapshot hash is the version's identity."""

    standards_version: str
    schema_version: str
    ingestion_version: str
    chunking_version: str
    embedding_config_id: str
    source_ids: tuple[str, ...]
    methodology_profiles: tuple[str, ...]
    record_counts: dict[str, int]
    rules_snapshot_hash: str
    snapshot_hash: str

    @property
    def version_id(self) -> str:
        return "KV-" + self.snapshot_hash[:16]


class KnowledgeVersion(_Model):
    version_id: str
    status: Literal["DRAFT", "SEALED"]
    manifest: VersionManifest


class RetrievalFilters(_Model):
    source_ids: tuple[str, ...] = ()
    edition_ids: tuple[str, ...] = ()
    methodology_profiles: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    knowledge_domains: tuple[KnowledgeDomain, ...] = ()
    text_origins: tuple[TextOrigin, ...] = ()
    parent_concept_ids: tuple[str, ...] = ()


class RetrievalQuery(_Model):
    text: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)
    max_distance: float = Field(default=DEFAULT_MAX_DISTANCE, gt=0.0, le=1.0)
    version_id: str | None = None
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)


class RetrievalHit(_Model):
    """One retrieved chunk with its provenance (KB-26).

    ``authority`` is fixed: a retrieved chunk is knowledge text, never a statement about a
    user's chart, never a calculation and never a rule result.
    """

    rank: int
    chunk_id: str
    distance: float
    metric: str
    knowledge_version_id: str
    embedding_config_id: str
    is_semantic: bool
    knowledge_domain: KnowledgeDomain
    source_id: str
    edition_id: str
    source_location: str
    section_path: str
    methodology_profile: str
    language: str
    text_origin: TextOrigin
    text_fidelity: TextFidelity
    reading_level: ReadingLevel
    confidence: Confidence
    parent_concept_id: str
    content_hash: str
    text: str
    authority: Literal["KNOWLEDGE_TEXT_NOT_A_CHART_FACT"] = "KNOWLEDGE_TEXT_NOT_A_CHART_FACT"


class RetrievalResult(_Model):
    knowledge_version_id: str
    embedding_config_id: str
    is_semantic: bool
    metric: str
    hits: tuple[RetrievalHit, ...]
    notes: tuple[str, ...] = ()
