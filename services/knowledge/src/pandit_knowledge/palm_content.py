"""The palmistry knowledge content (Phase 13): a SEPARATE knowledge version.

``load_palm_content`` reads ``services/knowledge/content/palm/`` (a subdirectory that the Phase 12
loader ``load_content`` never opens: it reads named files only) and returns the same
:class:`KnowledgeContent` structure the ingestion already builds into a sealed, versioned,
immutable knowledge version. Palm knowledge is therefore additive and forward-only: it is a
*different* version identifier from the Phase 12 version ``KV-06361d7aba28c1ce``, which is not
touched.

Everything stored is structured and provenance-tagged:

* **concepts**: palm lines, regions and features (every concept with a coverage status);
* **statements**: where a source says a named line or region lies, how a source says the hands are
  read, the source significations used by the fixture rules (tags only), the recorded differences
  between profiles (``UNRESOLVED_CONFLICT``, no winner), and one ``COVERAGE`` statement per record
  of the source coverage manifest;
* **terms**: the books' own names for a structure;
* **rule references**: ids of rules in the separate palm ruleset
  (``services/rule-engine/palm_rules``). This package imports no rule code and reads no
  rule-engine file: a cross-package integration test asserts the ids exist;
* **chunks**: template renderings of the structured records, labelled ``PROJECT_RENDERING``.

Validation (a violation raises :class:`PalmContentError`): every reference resolves; every
location, interpretation or convention statement is backed by a **read, supported** coverage record
at the same profile, location and concept (an unread concept cannot become a statement); no
statement tag or rendered text falls in a prohibited interpretation category (standards PM-13,
PM-25); the Indian methodology profile has no statement and only a ``RESEARCH_PENDING`` coverage
record.

The manifest field ``rules_snapshot_hash`` of this version is the hash of the rule *references* it
holds (not of the palm rule files, which this package does not read), so the version identity
changes when the references change.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pandit_contracts.palm_coverage import CoverageRecord, CoverageStatus, PalmSourceCoverage
from pandit_contracts.palm_policy import find_prohibited

from pandit_knowledge.chunking import ChunkUnit
from pandit_knowledge.content import KnowledgeContent, _validate_references, statement_id
from pandit_knowledge.models import (
    ConceptRecord,
    ConceptType,
    Confidence,
    EditionRecord,
    IngestionPermission,
    KnowledgeDomain,
    ReadingLevel,
    RuleKind,
    RuleReferenceRecord,
    SourceRecord,
    StatementKind,
    StatementRecord,
    SupportStatus,
    TermRecord,
    TextFidelity,
    TextOrigin,
    sha256_hex,
)

PALM_KNOWLEDGE_STANDARDS_VERSION = "1.28.0"
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PALM_CONTENT_DIR = PACKAGE_ROOT / "content" / "palm"
METHODOLOGY_WESTERN = "PALM_WESTERN"
METHODOLOGY_INDIAN = "PALM_INDIAN_HASTA_SAMUDRIKA"

_BACKED_KINDS = {
    StatementKind.LOCATION_DEFINITION,
    StatementKind.READING_CONVENTION,
    StatementKind.SIGNIFICATION,
}
_COVERAGE_TO_SUPPORT = {
    CoverageStatus.SUPPORTED: SupportStatus.SOURCE_SUPPORTED,
    CoverageStatus.PARTIALLY_SUPPORTED: SupportStatus.SOURCE_SUPPORTED,
}
_VERIFICATION = {
    ReadingLevel.PAGE_IMAGE_LEVEL: "IMAGE-ORIGINAL-ENGLISH",
    ReadingLevel.OCR_LEVEL: "OCR-ORIGINAL-ENGLISH",
    ReadingLevel.TRANSCRIPTION_LEVEL: "WEB-TRANSCRIPTION-ORIGINAL-ENGLISH",
    ReadingLevel.NOT_APPLICABLE: "NONE",
}


class PalmContentError(Exception):
    """The palm knowledge content is inconsistent or violates a boundary."""


@dataclass(frozen=True)
class PalmKnowledgeContent:
    knowledge: KnowledgeContent
    coverage: PalmSourceCoverage


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PalmContentError(f"{path.name}: expected a mapping")
    return data


def _location_kind(location: str) -> Literal["paragraph", "page", "chapter"]:
    low = location.lower()
    if low.startswith(("para", "paras")):
        return "paragraph"
    if low.startswith(("p.", "pp.")):
        return "page"
    return "chapter"


def _short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _scan(text: str, where: str) -> None:
    found = find_prohibited(text)
    if found:
        raise PalmContentError(
            f"{where}: prohibited interpretation ({found[0].category.value}: {found[0].term!r})"
        )


def _chunk(
    text: str,
    *,
    concept_key: str,
    concept_id: str,
    profile: str,
    source_id: str,
    edition_id: str,
    location: str,
    reading: ReadingLevel,
    confidence: Confidence,
    ref: str,
    section: str,
    methodology: str = METHODOLOGY_WESTERN,
) -> ChunkUnit:
    return ChunkUnit(
        text=text,
        knowledge_domain=KnowledgeDomain.PALMISTRY,
        language="en",
        text_origin=TextOrigin.PROJECT_RENDERING,
        text_fidelity=TextFidelity.TEMPLATE_RENDERING,
        source_id=source_id,
        edition_id=edition_id,
        source_location=location,
        section_path=f"{methodology}/{section}/{concept_key}",
        parent_concept_id=concept_id,
        methodology_profile=profile,
        reading_level=reading,
        confidence=confidence,
        external_ref=ref,
    )


def load_palm_coverage(content_dir: Path = DEFAULT_PALM_CONTENT_DIR) -> PalmSourceCoverage:
    data = _read(content_dir / "source_coverage.yaml")
    return PalmSourceCoverage(
        manifest_id=data["manifest_id"],
        manifest_version=data["manifest_version"],
        records=tuple(CoverageRecord(**rec) for rec in data["records"]),
    )


def load_palm_content(content_dir: Path = DEFAULT_PALM_CONTENT_DIR) -> PalmKnowledgeContent:
    sources_data = _read(content_dir / "sources.yaml")
    concepts_data = _read(content_dir / "concepts.yaml")
    statements_data = _read(content_dir / "statements.yaml")
    terms_data = _read(content_dir / "terms_and_references.yaml")
    coverage = load_palm_coverage(content_dir)

    content = KnowledgeContent()
    content.sources = [
        SourceRecord(
            **{**s, "ingestion_permission": IngestionPermission(s["ingestion_permission"])}
        )
        for s in sources_data["sources"]
    ]
    content.editions = [
        EditionRecord(**{**e, "reading_level": ReadingLevel(e["reading_level"])})
        for e in sources_data["editions"]
    ]
    editions = {e.edition_id: e for e in content.editions}
    source_ids = {s.source_id for s in content.sources}
    edition_of_source = {e.source_id: e.edition_id for e in content.editions}
    for e in content.editions:
        if e.source_id not in source_ids:
            raise PalmContentError(f"edition {e.edition_id}: unknown source {e.source_id}")

    content.concepts = [
        ConceptRecord(
            concept_id=c["id"], concept_type=ConceptType(c["type"]), canonical_key=c["key"]
        )
        for c in concepts_data["concepts"]
    ]
    concept_ids = {c.concept_id for c in content.concepts}
    if len(concept_ids) != len(content.concepts):
        raise PalmContentError("duplicate concept identifiers")
    keys = {c.concept_id: c.canonical_key for c in content.concepts}

    statements: list[StatementRecord] = []
    units: list[ChunkUnit] = []
    for st in statements_data["statements"]:
        kind = StatementKind(st["kind"])
        profile, concept, location = st["profile"], st["concept"], st["location"]
        if concept not in concept_ids or st["edition"] not in editions:
            raise PalmContentError(f"statement {profile}/{concept}: dangling reference")
        if kind in _BACKED_KINDS:
            problems = coverage.problems_for_rule(profile, location, [concept])
            if problems:
                raise PalmContentError(f"statement {profile}/{concept} is not backed: {problems}")
        extras = {k: v for k, v in st.items() if k not in _STATEMENT_KEYS}
        for tag in st["tags"]:
            _scan(tag, f"statement {profile}/{concept} tag")
        record = StatementRecord(
            statement_id=statement_id(profile, concept, kind.value),
            concept_id=concept,
            statement_kind=kind,
            profile_id=profile,
            edition_id=st["edition"],
            source_location=location,
            location_kind=st["location_kind"],
            reading_level=ReadingLevel(st["reading_level"]),
            registry_verification_level=st["verification"],
            confidence=Confidence(st["confidence"]),
            support_status=SupportStatus(st["support"]),
            language="en",
            attributes={
                "methodology_profile": METHODOLOGY_WESTERN,
                "tags": list(st["tags"]),
                **extras,
            },
        )
        statements.append(record)
        text = (
            f"Palm {keys[concept]} ({profile}) at {location}: {'; '.join(st['tags'])}. "
            f"Status {record.support_status.value}. A source statement, not a fact about any hand."
        )
        _scan(text, f"chunk of {record.statement_id}")
        units.append(
            _chunk(
                text,
                concept_key=keys[concept],
                concept_id=concept,
                profile=profile,
                source_id=editions[record.edition_id].source_id,
                edition_id=record.edition_id,
                location=location,
                reading=record.reading_level,
                confidence=record.confidence,
                ref=record.statement_id,
                section=kind.value,
            )
        )

    for var in statements_data["variances"]:
        profile = f"PALM_CROSS_SOURCE.{var['id']}"
        if var["concept"] not in concept_ids or var["edition"] not in editions:
            raise PalmContentError(f"variance {profile}/{var['concept']}: dangling reference")
        for tag in var["tags"]:
            _scan(tag, f"variance {profile} tag")
        record = StatementRecord(
            statement_id=statement_id(profile, var["concept"], "SOURCE_VARIANCE"),
            concept_id=var["concept"],
            statement_kind=StatementKind.SOURCE_VARIANCE,
            profile_id=profile,
            edition_id=var["edition"],
            source_location="; ".join(var["profiles"]),
            location_kind="derived",
            reading_level=ReadingLevel.NOT_APPLICABLE,
            registry_verification_level="DERIVED",
            confidence=Confidence.MEDIUM,
            support_status=SupportStatus.UNRESOLVED_CONFLICT,
            language="en",
            attributes={
                "methodology_profile": METHODOLOGY_WESTERN,
                "profiles": list(var["profiles"]),
                "tags": list(var["tags"]),
                "resolved": False,
                "winner": None,
            },
        )
        statements.append(record)
        text = (
            f"Palm {keys[var['concept']]}: the profiles {', '.join(var['profiles'])} differ "
            f"({'; '.join(var['tags'])}). Recorded UNRESOLVED_CONFLICT; no winner is chosen."
        )
        _scan(text, f"chunk of {record.statement_id}")
        units.append(
            _chunk(
                text,
                concept_key=keys[var["concept"]],
                concept_id=var["concept"],
                profile=profile,
                source_id=editions[var["edition"]].source_id,
                edition_id=var["edition"],
                location=record.source_location,
                reading=ReadingLevel.NOT_APPLICABLE,
                confidence=Confidence.MEDIUM,
                ref=record.statement_id,
                section="SOURCE_VARIANCE",
            )
        )

    # one COVERAGE statement per manifest record (the manifest becomes part of the version)
    for rec in coverage.records:
        if rec.concept_id not in concept_ids:
            raise PalmContentError(f"coverage {rec.concept_id}: unknown concept")
        edition_id = edition_of_source.get(rec.source_id)
        if edition_id is None:
            raise PalmContentError(f"coverage {rec.concept_id}: unknown source {rec.source_id}")
        reading = ReadingLevel(rec.reading_level)
        record = StatementRecord(
            statement_id=f"ST.{rec.profile_id}.{rec.concept_id}.COVERAGE.{_short(rec.location)}",
            concept_id=rec.concept_id,
            statement_kind=StatementKind.COVERAGE,
            profile_id=rec.profile_id,
            edition_id=edition_id,
            source_location=rec.location,
            location_kind=_location_kind(rec.location),
            reading_level=reading,
            registry_verification_level=_VERIFICATION[reading],
            confidence=Confidence(rec.confidence),
            support_status=_COVERAGE_TO_SUPPORT.get(rec.status, SupportStatus.NOT_EVALUABLE),
            language="en",
            attributes={
                "methodology_profile": rec.methodology_profile,
                "coverage_status": rec.status.value,
                "read": rec.read,
                "statement": rec.statement,
                "note": rec.note,
            },
        )
        statements.append(record)
        units.append(
            _chunk(
                f"Palm {keys[rec.concept_id]}: coverage {rec.status.value} for {rec.profile_id} "
                f"at {rec.location}; read {'yes' if rec.read else 'no'}.",
                concept_key=keys[rec.concept_id],
                concept_id=rec.concept_id,
                profile=rec.profile_id,
                source_id=rec.source_id,
                edition_id=edition_id,
                location=rec.location,
                reading=reading,
                confidence=Confidence(rec.confidence),
                ref=record.statement_id,
                section="COVERAGE",
                methodology=rec.methodology_profile,
            )
        )

    ids = [s.statement_id for s in statements]
    if len(set(ids)) != len(ids):
        raise PalmContentError("duplicate statement identifiers")
    content.statements = statements

    for stmt in statements:
        if (
            stmt.attributes.get("methodology_profile") == METHODOLOGY_INDIAN
            and stmt.statement_kind is not StatementKind.COVERAGE
        ):
            raise PalmContentError("the Indian profile may carry no statement but its coverage")

    terms: list[TermRecord] = []
    for index, t in enumerate(terms_data["terms"]):
        if t["concept"] not in concept_ids or t["edition"] not in editions:
            raise PalmContentError(f"term {t['text']}: dangling reference")
        terms.append(
            TermRecord(
                term_id=f"TM.{t['concept']}.{t['profile']}.{t['kind']}.{index:03d}",
                concept_id=t["concept"],
                term_kind=t["kind"],
                script="Latn",
                language="en",
                text=t["text"],
                profile_id=t["profile"],
                edition_id=t["edition"],
                source_location=t["location"],
                verification_status=_VERIFICATION[editions[t["edition"]].reading_level],
            )
        )
    content.terms = terms

    refs: list[RuleReferenceRecord] = []
    for r in terms_data["rule_references"]:
        if r["concept"] not in concept_ids:
            raise PalmContentError(f"rule reference {r['rule_id']}: dangling concept")
        refs.append(
            RuleReferenceRecord(
                reference_id=f"RR.{r['rule_id']}",
                concept_id=r["concept"],
                rule_id=r["rule_id"],
                rule_kind=RuleKind.PALM_RULE,
                relation=r["relation"],
                profile_id=r["profile"],
                source_location=r["location"],
            )
        )
    content.rule_references = refs
    content.chunk_units = units
    content.rules_snapshot_hash = sha256_hex([r.model_dump(mode="json") for r in refs])
    _validate_references(content, concept_ids, editions)
    return PalmKnowledgeContent(content, coverage)


_STATEMENT_KEYS = {
    "concept",
    "kind",
    "profile",
    "edition",
    "location",
    "location_kind",
    "reading_level",
    "verification",
    "confidence",
    "support",
    "tags",
}

__all__ = [
    "DEFAULT_PALM_CONTENT_DIR",
    "PALM_KNOWLEDGE_STANDARDS_VERSION",
    "PalmContentError",
    "PalmKnowledgeContent",
    "load_palm_content",
    "load_palm_coverage",
]
