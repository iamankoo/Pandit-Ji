"""Load and validate the curated Phase 12 content (`services/knowledge/content/`).

The loader turns the YAML and JSONL files into typed records and chunk units. It only
*structures* source-attested material: it adds no interpretation. The few derived records are
mechanical (the inversion of a source table, the difference between two source tables, template
renderings of already-stored terms) and each is labelled as derived.

Validation (every violation raises :class:`ContentError`, so a bad edit fails the build):

* every concept, edition and statement reference resolves;
* every ``rule_id`` resolves to a rule or table in the Phase 6 rule YAML;
* every ``SIG.*`` / ``ROLE.*`` tag has the expected shape and every record has provenance;
* a project rendering is never labelled as source text.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pandit_knowledge.chunking import ChunkUnit
from pandit_knowledge.models import (
    ChunkRecord,
    ConceptRecord,
    ConceptType,
    Confidence,
    DomainMappingRecord,
    EditionRecord,
    ExceptionRecord,
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

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTENT_DIR = PACKAGE_ROOT / "content"
DEFAULT_RULES_DIR = PACKAGE_ROOT / "rules"

TAROT_DECK_PROFILE = "TAROT_DECK_WAITE_SMITH_1910"
WAITE_EDITION = "WAITE_PICTORIAL_KEY_WIKISOURCE"
WAITE_SOURCE = "SRC.WAITE_PICTORIAL_KEY"

_TAG = re.compile(r"^(SIG|ROLE)\.[A-Z0-9_]+$")
_MAJOR_SLUGS: dict[int, str] = {
    0: "fool",
    1: "magician",
    2: "high_priestess",
    3: "empress",
    4: "emperor",
    5: "hierophant",
    6: "lovers",
    7: "chariot",
    8: "strength",
    9: "hermit",
    10: "wheel_of_fortune",
    11: "justice",
    12: "hanged_man",
    13: "death",
    14: "temperance",
    15: "devil",
    16: "tower",
    17: "star",
    18: "moon",
    19: "sun",
    20: "last_judgment",
    21: "world",
}
_ORDINALS = {1: "1st", 2: "2nd", 3: "3rd"}


class ContentError(Exception):
    """The curated content is inconsistent."""


@dataclass
class KnowledgeContent:
    sources: list[SourceRecord] = field(default_factory=list)
    editions: list[EditionRecord] = field(default_factory=list)
    concepts: list[ConceptRecord] = field(default_factory=list)
    statements: list[StatementRecord] = field(default_factory=list)
    terms: list[TermRecord] = field(default_factory=list)
    rule_references: list[RuleReferenceRecord] = field(default_factory=list)
    domain_mappings: list[DomainMappingRecord] = field(default_factory=list)
    exceptions: list[ExceptionRecord] = field(default_factory=list)
    chunk_units: list[ChunkUnit] = field(default_factory=list)
    rules_snapshot_hash: str = ""

    def source_ids(self) -> tuple[str, ...]:
        return tuple(sorted(s.source_id for s in self.sources))

    def methodology_profiles(self) -> tuple[str, ...]:
        profiles = {s.profile_id for s in self.statements}
        profiles |= {u.methodology_profile for u in self.chunk_units}
        profiles |= {e.profile_id for e in self.exceptions}
        return tuple(sorted(profiles))


def ordinal(n: int) -> str:
    return _ORDINALS.get(n, f"{n}th")


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ContentError(f"{path.name}: expected a mapping")
    return data


def statement_id(profile: str, concept: str, kind: str) -> str:
    return f"ST.{profile}.{concept}.{kind}"


def rule_index(rules_dir: Path) -> tuple[dict[str, str], str]:
    """``{rule_or_table_id: kind}`` from the Phase 6 YAML, and a snapshot hash of the files."""
    ids: dict[str, str] = {}
    digest_parts: list[tuple[str, str]] = []
    if not rules_dir.is_dir():
        raise ContentError(f"rules directory not found: {rules_dir}")
    for path in sorted(rules_dir.rglob("*.yaml")):
        raw = path.read_bytes().replace(b"\r\n", b"\n")  # hash is line-ending independent
        digest_parts.append(
            (path.relative_to(rules_dir).as_posix(), hashlib.sha256(raw).hexdigest())
        )
        for doc in yaml.safe_load_all(raw.decode("utf-8")):
            if not isinstance(doc, dict):
                continue
            if doc.get("document_type") == "rule":
                ids[str(doc["rule_id"])] = "RULE"
            elif doc.get("document_type") == "table":
                ids[str(doc["table_id"])] = "TABLE"
    return ids, sha256_hex(digest_parts)


def _concept_records(files: list[dict[str, Any]]) -> list[ConceptRecord]:
    out: dict[str, ConceptRecord] = {}
    for data in files:
        for c in data.get("concepts", []):
            cid = str(c["id"])
            ctype = ConceptType(
                c.get("type")
                or {
                    "PLANET": "PLANET",
                    "HOUSE": "HOUSE",
                    "DOMAIN": "DOMAIN",
                    "TERM": "TERM",
                    "CONCEPT": "CONCEPT",
                }[cid.split(".")[0]]
            )
            rec = ConceptRecord(concept_id=cid, concept_type=ctype, canonical_key=str(c["key"]))
            if cid in out and out[cid] != rec:
                raise ContentError(f"concept {cid} defined twice differently")
            out[cid] = rec
    return list(out.values())


def _statements(data: dict[str, Any], editions: dict[str, EditionRecord]) -> list[StatementRecord]:
    profiles = data.get("profiles", {})
    out: list[StatementRecord] = []
    for s in data.get("statements", []):
        prof = profiles[s["profile"]]
        edition = editions[prof["edition"]]
        kind = StatementKind(s["kind"])
        if kind is StatementKind.HOUSE_KARAKA:
            attributes: dict[str, Any] = {"karaka_planets": list(s["karaka_planets"])}
        else:
            attributes = {
                "items": [{"id": i["id"], "rendering": i["rendering"]} for i in s["items"]]
            }
            for item in attributes["items"]:
                if not _TAG.match(item["id"]):
                    raise ContentError(f"bad tag shape {item['id']}")
        out.append(
            StatementRecord(
                statement_id=statement_id(s["profile"], s["concept"], s["kind"]),
                concept_id=s["concept"],
                statement_kind=kind,
                profile_id=s["profile"],
                edition_id=edition.edition_id,
                source_location=prof["location"],
                location_kind=prof["location_kind"],
                reading_level=ReadingLevel(prof["reading"]),
                registry_verification_level=prof["registry_level"],
                confidence=Confidence(prof["confidence"]),
                support_status=SupportStatus.SOURCE_SUPPORTED,
                language=edition.language,
                attributes=attributes,
            )
        )
    return out


def _derived_karaka_statements(
    statements: list[StatementRecord], conflicts: list[dict[str, Any]]
) -> list[StatementRecord]:
    """Mechanical inversion and cross-profile difference of the two house-karaka tables."""
    by_profile: dict[str, dict[str, list[str]]] = defaultdict(dict)
    meta: dict[str, StatementRecord] = {}
    for st in statements:
        if st.statement_kind is StatementKind.HOUSE_KARAKA:
            by_profile[st.profile_id][st.concept_id] = list(st.attributes["karaka_planets"])
            meta[st.profile_id] = st
    out: list[StatementRecord] = []
    for profile, table in sorted(by_profile.items()):
        inverted: dict[str, list[str]] = defaultdict(list)
        for house in sorted(table):
            for planet in table[house]:
                inverted[planet].append(house)
        base = meta[profile]
        for planet, houses in sorted(inverted.items()):
            out.append(
                StatementRecord(
                    statement_id=statement_id(profile, planet, "DERIVED_INVERSION"),
                    concept_id=planet,
                    statement_kind=StatementKind.DERIVED_INVERSION,
                    profile_id=profile,
                    edition_id=base.edition_id,
                    source_location=base.source_location + " (inverted)",
                    location_kind="derived",
                    reading_level=ReadingLevel.NOT_APPLICABLE,
                    registry_verification_level="NOT_APPLICABLE",
                    confidence=base.confidence,
                    support_status=SupportStatus.PROJECT_DERIVED,
                    language="und",
                    attributes={
                        "houses": houses,
                        "derived_from_profile": profile,
                        "method": "MECHANICAL_INVERSION_OF_SOURCE_TABLE",
                    },
                )
            )
    profiles = sorted(by_profile)
    if len(profiles) == 2:
        first, second = profiles
        for house in sorted(by_profile[first]):
            a, b = by_profile[first][house], by_profile[second].get(house, [])
            if sorted(a) != sorted(b):
                base = meta[first]
                out.append(
                    StatementRecord(
                        statement_id=statement_id(
                            "CROSS_SOURCE.HOUSE_KARAKA", house, "SOURCE_VARIANCE"
                        ),
                        concept_id=house,
                        statement_kind=StatementKind.SOURCE_VARIANCE,
                        profile_id="CROSS_SOURCE.HOUSE_KARAKA",
                        edition_id=base.edition_id,
                        source_location=f"{base.source_location}; {meta[second].source_location}",
                        location_kind="derived",
                        reading_level=ReadingLevel.NOT_APPLICABLE,
                        registry_verification_level="NOT_APPLICABLE",
                        confidence=Confidence.HIGH,
                        support_status=SupportStatus.UNRESOLVED_CONFLICT,
                        language="und",
                        attributes={
                            "kind": "KARAKA_SET_DIFFERS",
                            "profiles": {first: sorted(a), second: sorted(b)},
                            "editions": [base.edition_id, meta[second].edition_id],
                            "note": (
                                "Two source tables name different significators; "
                                "both kept, none preferred."
                            ),
                        },
                    )
                )
    by_id = {st.statement_id: st for st in statements}
    for c in conflicts:
        profiles_c = list(c["profiles"])
        first_st = by_id[statement_id(profiles_c[0], c["concept"], "SIGNIFICATION")]
        out.append(
            StatementRecord(
                statement_id=statement_id(
                    "CROSS_SOURCE.HOUSE_SIGNIFICATION", c["concept"], "SOURCE_VARIANCE"
                ),
                concept_id=c["concept"],
                statement_kind=StatementKind.SOURCE_VARIANCE,
                profile_id="CROSS_SOURCE.HOUSE_SIGNIFICATION",
                edition_id=first_st.edition_id,
                source_location="; ".join(
                    by_id[statement_id(p, c["concept"], "SIGNIFICATION")].source_location
                    for p in profiles_c
                ),
                location_kind="derived",
                reading_level=ReadingLevel.NOT_APPLICABLE,
                registry_verification_level="NOT_APPLICABLE",
                confidence=Confidence.HIGH,
                support_status=SupportStatus.UNRESOLVED_CONFLICT,
                language="und",
                attributes={
                    "kind": "SIGNIFICATION_SETS_DIFFER",
                    "profiles": {
                        p: [
                            i["id"]
                            for i in by_id[
                                statement_id(p, c["concept"], "SIGNIFICATION")
                            ].attributes["items"]
                        ]
                        for p in profiles_c
                    },
                    "note": " ".join(str(c["note"]).split()),
                },
            )
        )
    return out


def _terms(data: dict[str, Any], editions: dict[str, EditionRecord]) -> list[TermRecord]:
    out: list[TermRecord] = []
    counters: dict[str, int] = defaultdict(int)
    for t in data["terms"]:
        src = data["sources"][t["source"]]
        counters[t["concept"]] += 1
        out.append(
            TermRecord(
                term_id=f"TM.{t['concept']}.{counters[t['concept']]:02d}",
                concept_id=t["concept"],
                term_kind=t["kind"],
                script=t["script"],
                language=t["language"],
                text=t["text"],
                profile_id=src["profile"],
                edition_id=editions[src["edition"]].edition_id,
                source_location=src["location"],
                verification_status=src["status"],
            )
        )
    return out


def _rule_references(
    data: dict[str, Any], rules: dict[str, str], concepts: set[str]
) -> list[RuleReferenceRecord]:
    out: list[RuleReferenceRecord] = []

    def add(concept: str, rule_id: str, kind: str, relation: str, location: str) -> None:
        if concept not in concepts:
            raise ContentError(f"rule reference to unknown concept {concept}")
        if kind in {"RULE", "TABLE"}:
            actual = rules.get(rule_id)
            if actual is None:
                raise ContentError(f"rule reference {rule_id} not found in the rule YAML")
            if actual != kind:
                raise ContentError(f"{rule_id} is a {actual}, not a {kind}")
        out.append(
            RuleReferenceRecord(
                reference_id=f"RR.{concept}.{rule_id}",
                concept_id=concept,
                rule_id=rule_id,
                rule_kind=RuleKind(kind),
                relation=relation,
                profile_id=rule_id,
                source_location=location,
            )
        )

    for r in data["rule_references"]:
        add(r["concept"], r["rule_id"], r["kind"], r["relation"], r["location"])
    seven = [
        f"PLANET.{p}" for p in ("SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN")
    ]
    nine = [*seven, "PLANET.RAHU", "PLANET.KETU"]
    for t in data["relationship_tables"]["seven_planets"]:
        for planet in seven:
            add(planet, t["rule_id"], "TABLE", "RELATIONSHIP_METHODOLOGY", t["location"])
    for t in data["relationship_tables"]["all_nine"]:
        for planet in nine:
            add(planet, t["rule_id"], "TABLE", "RELATIONSHIP_METHODOLOGY", t["location"])
    for p in data["strength"]["profile_references"]:
        add("CONCEPT.STRENGTH", p["rule_id"], "PROFILE", p["relation"], p["location"])
    return out


def _exceptions(data: dict[str, Any], rules: dict[str, str]) -> list[ExceptionRecord]:
    out: list[ExceptionRecord] = []
    for e in data["exceptions"]:
        if e["rule_id"] not in rules:
            raise ContentError(f"exception for unknown rule {e['rule_id']}")
        out.append(
            ExceptionRecord(
                exception_id=e["id"],
                affected_rule_id=e["rule_id"],
                affected_concept_id=e["concept"],
                profile_id=e["rule_id"],
                edition_id=e["edition"],
                source_location=e["location"],
                condition_summary=e["summary"],
                effect=e["effect"],
                confidence=Confidence(e["confidence"]),
                conflict_note=" ".join(str(e["conflict_note"]).split()),
            )
        )
    nab = data["nabhasa_sankhya_exception"]
    for rule_id in nab["rule_ids"]:
        if rule_id not in rules:
            raise ContentError(f"exception for unknown rule {rule_id}")
        out.append(
            ExceptionRecord(
                exception_id=f"EX.{rule_id}.EARLIER_NABHASA_YOGA_DERIVABLE",
                affected_rule_id=rule_id,
                affected_concept_id="CONCEPT.NABHASA_YOGA",
                profile_id=rule_id,
                edition_id=nab["edition"],
                source_location=nab["location"],
                condition_summary=nab["summary"],
                effect=nab["effect"],
                confidence=Confidence(nab["confidence"]),
                conflict_note=" ".join(str(nab["conflict_note"]).split()),
            )
        )
    return out


def _domain_mappings(
    data: dict[str, Any], statements: dict[str, StatementRecord]
) -> list[DomainMappingRecord]:
    explicit: dict[tuple[str, str], DomainMappingRecord] = {}
    for m in data["mappings"]:
        ids: list[str] = []
        for s in m["supports"]:
            sid = statement_id(s["profile"], s["concept"], s["kind"])
            if sid not in statements:
                raise ContentError(f"domain mapping support {sid} not found")
            ids.append(sid)
        explicit[(m["domain"], m["house"])] = DomainMappingRecord(
            mapping_id=f"DM.{m['domain']}.{m['house']}",
            domain_id=m["domain"],
            concept_id=m["house"],
            support_status=SupportStatus(m["status"]),
            supporting_statement_ids=tuple(ids),
            profile_id=m["profile"],
            bridge_note=" ".join(str(m["bridge"]).split()),
        )
    notes = {
        (n["domain"], n["house"]): " ".join(str(n["note"]).split())
        for n in data["not_evaluable_notes"]
    }
    out: list[DomainMappingRecord] = []
    domains = sorted({d["id"] for d in data["concepts"]})
    for domain in domains:
        for n in range(1, 13):
            house = f"HOUSE.{n:02d}"
            rec = explicit.get((domain, house))
            if rec is None:
                rec = DomainMappingRecord(
                    mapping_id=f"DM.{domain}.{house}",
                    domain_id=domain,
                    concept_id=house,
                    support_status=SupportStatus.NOT_EVALUABLE,
                    supporting_statement_ids=(),
                    profile_id="NONE",
                    bridge_note=notes.get(
                        (domain, house), "No source read in Phase 12 states this mapping."
                    ),
                )
            out.append(rec)
    return out


def _tarot(
    corpus_path: Path,
) -> tuple[list[ConceptRecord], list[ChunkUnit]]:
    concepts: list[ConceptRecord] = []
    units: list[ChunkUnit] = []
    lines = corpus_path.read_text(encoding="utf-8").splitlines()
    meta = json.loads(lines[0])["_meta"]
    if meta["lesser_count"] != 56 or meta["greater_count"] != 22:
        raise ContentError("Waite corpus must hold 56 lesser and 22 greater cards")
    for line in lines[1:]:
        row = json.loads(line)
        if row["arcana"] == "greater":
            deck_id = f"major_{row['number']:02d}_{_MAJOR_SLUGS[row['number']]}"
            path = f"Part III/§3/{row['title']}"
        else:
            deck_id = f"{row['suit']}_{row['rank']}"
            path = f"Part III/§2/{row['suit']}/{row['rank']}"
        cid = f"TAROT.{deck_id}"
        concepts.append(
            ConceptRecord(
                concept_id=cid, concept_type=ConceptType.TAROT_CARD, canonical_key=deck_id
            )
        )
        units.append(
            ChunkUnit(
                text=row["text"],
                knowledge_domain=KnowledgeDomain.TAROT,
                language="en",
                text_origin=TextOrigin.SOURCE_TEXT,
                text_fidelity=TextFidelity.PROOFREAD_TRANSCRIPTION,
                source_id=WAITE_SOURCE,
                edition_id=WAITE_EDITION,
                source_location=f"{row['section']}, {row['title']}",
                section_path=path,
                parent_concept_id=cid,
                methodology_profile=TAROT_DECK_PROFILE,
                reading_level=ReadingLevel.TRANSCRIPTION_LEVEL,
                confidence=Confidence.MEDIUM,
                external_ref=deck_id,
            )
        )
    return concepts, units


def _display_name(concept_id: str, names: dict[str, str]) -> str:
    if concept_id in names:
        return names[concept_id]
    if concept_id.startswith("HOUSE."):
        return f"the {ordinal(int(concept_id.split('.')[1]))} house"
    return concept_id


def _source_label(edition: EditionRecord) -> str:
    label = {
        "BPHS_SANTHANAM_1984": "BPHS (Santhanam translation)",
        "BPHS_KAPOOR_1987": "BPHS (Kapoor translation)",
        "PHALADEEPIKA_SASTRI": "Phaladeepika (Sastri translation)",
        "BRIHAT_JATAKA_SASTRI": "Brihat Jataka (Sastri translation)",
    }
    return label.get(edition.edition_id, edition.edition_id)


def _rendered_text(
    st: StatementRecord, names: dict[str, str], editions: dict[str, EditionRecord]
) -> str:
    who = _display_name(st.concept_id, names)
    where = f"{_source_label(editions[st.edition_id])} {st.source_location}"
    if st.statement_kind in (StatementKind.SIGNIFICATION, StatementKind.ROLE):
        terms = "; ".join(i["rendering"] for i in st.attributes["items"])
        verb = "lists as its rank" if st.statement_kind is StatementKind.ROLE else "associates with"
        return f"{where} {verb} {who}: {terms}."
    if st.statement_kind is StatementKind.HOUSE_KARAKA:
        planets = ", ".join(_display_name(p, names) for p in st.attributes["karaka_planets"])
        return f"{where} names {planets} as the planetary significator of {who}."
    if st.statement_kind is StatementKind.DERIVED_INVERSION:
        houses = ", ".join(_display_name(h, names) for h in st.attributes["houses"])
        return (
            f"Derived by inverting the table at {where}: {who} is named as a planetary "
            f"significator of {houses}."
        )
    if st.statement_kind is StatementKind.SOURCE_VARIANCE:
        return f"Recorded source difference for {who} ({st.profile_id}): {st.attributes['note']}"
    if st.statement_kind is StatementKind.STRENGTH_NOTE:
        return (
            f"{where} remarks that the effects of {who} scale with strength; no threshold is given."
        )
    raise ContentError(f"no rendering for {st.statement_kind}")


def _rendering_units(
    content: KnowledgeContent, names: dict[str, str], editions: dict[str, EditionRecord]
) -> list[ChunkUnit]:
    units: list[ChunkUnit] = []

    def add(
        text: str,
        concept: str,
        profile: str,
        edition: str,
        location: str,
        reading: ReadingLevel,
        conf: Confidence,
        ref: str,
        path: str,
    ) -> None:
        units.append(
            ChunkUnit(
                text=text,
                knowledge_domain=KnowledgeDomain.VEDIC,
                language="en",
                text_origin=TextOrigin.PROJECT_RENDERING,
                text_fidelity=TextFidelity.TEMPLATE_RENDERING,
                source_id=editions[edition].source_id,
                edition_id=edition,
                source_location=location,
                section_path=path,
                parent_concept_id=concept,
                methodology_profile=profile,
                reading_level=reading,
                confidence=conf,
                external_ref=ref,
            )
        )

    for st in content.statements:
        add(
            _rendered_text(st, names, editions),
            st.concept_id,
            st.profile_id,
            st.edition_id,
            st.source_location,
            st.reading_level,
            st.confidence,
            st.statement_id,
            f"{st.concept_id}/{st.statement_kind.value}/{st.profile_id}",
        )
    statements = {s.statement_id: s for s in content.statements}
    for m in content.domain_mappings:
        if m.support_status is SupportStatus.NOT_EVALUABLE:
            continue
        first = statements[m.supporting_statement_ids[0]]
        house = _display_name(m.concept_id, names)
        text = (
            f"Pandit Ji domain mapping ({m.support_status.value}): "
            f"the {m.domain_id.split('.')[1].lower()} "
            f"domain relates to {house}. {m.bridge_note}"
        )
        add(
            text,
            m.concept_id,
            m.profile_id,
            first.edition_id,
            first.source_location,
            first.reading_level,
            first.confidence,
            m.mapping_id,
            f"{m.concept_id}/DOMAIN_MAPPING/{m.domain_id}",
        )
    for e in content.exceptions:
        text = (
            f"Exception recorded for rule {e.affected_rule_id.replace('_', ' ')}: "
            f"{e.condition_summary} "
            f"Effect as encoded: {e.effect}. {e.conflict_note}"
        )
        add(
            text,
            e.affected_concept_id,
            e.profile_id,
            e.edition_id,
            e.source_location,
            ReadingLevel(editions[e.edition_id].reading_level),
            e.confidence,
            e.exception_id,
            f"{e.affected_concept_id}/EXCEPTION/{e.affected_rule_id}",
        )
    return units


def load_content(
    content_dir: Path = DEFAULT_CONTENT_DIR, rules_dir: Path = DEFAULT_RULES_DIR
) -> KnowledgeContent:
    rules, rules_hash = rule_index(rules_dir)
    src_data = _read_yaml(content_dir / "sources.yaml")
    planets = _read_yaml(content_dir / "planets.yaml")
    houses = _read_yaml(content_dir / "houses.yaml")
    terms = _read_yaml(content_dir / "terms.yaml")
    domains = _read_yaml(content_dir / "domains.yaml")
    refs = _read_yaml(content_dir / "references.yaml")

    content = KnowledgeContent(rules_snapshot_hash=rules_hash)
    content.sources = [
        SourceRecord(
            **{**s, "ingestion_permission": IngestionPermission(s["ingestion_permission"])}
        )
        for s in src_data["sources"]
    ]
    source_ids = {s.source_id for s in content.sources}
    content.editions = [
        EditionRecord(**{**e, "reading_level": ReadingLevel(e["reading_level"])})
        for e in src_data["editions"]
    ]
    editions = {e.edition_id: e for e in content.editions}
    for e in content.editions:
        if e.source_id not in source_ids:
            raise ContentError(f"edition {e.edition_id}: unknown source {e.source_id}")

    tarot_concepts, tarot_units = _tarot(content_dir / "corpus" / "waite_pictorial_key_part3.jsonl")
    extra = {
        "concepts": [
            {"id": "CONCEPT.STRENGTH", "key": "strength", "type": "CONCEPT"},
            {"id": "CONCEPT.NABHASA_YOGA", "key": "nabhasa_yoga", "type": "CONCEPT"},
        ]
    }
    content.concepts = _concept_records([planets, houses, terms, domains, extra]) + tarot_concepts
    concept_ids = {c.concept_id for c in content.concepts}
    if len(concept_ids) != len(content.concepts):
        raise ContentError("duplicate concept identifiers")

    base = _statements(planets, editions) + _statements(houses, editions)
    strength = refs["strength"]["note_statement"]
    base.append(
        StatementRecord(
            statement_id=statement_id(
                strength["profile"], refs["strength"]["concept"], "STRENGTH_NOTE"
            ),
            concept_id=refs["strength"]["concept"],
            statement_kind=StatementKind.STRENGTH_NOTE,
            profile_id=strength["profile"],
            edition_id=strength["edition"],
            source_location=strength["location"],
            location_kind="note",
            reading_level=ReadingLevel.PAGE_IMAGE_LEVEL,
            registry_verification_level="IMAGE-TRANSLATION",
            confidence=Confidence.MEDIUM,
            support_status=SupportStatus.SOURCE_SUPPORTED,
            language="en",
            attributes={
                "tags": list(strength["tags"]),
                "threshold": None,
                "threshold_status": "NOT_LOCKED_SM_11",
            },
        )
    )
    content.statements = base + _derived_karaka_statements(base, houses.get("conflicts", []))
    ids = [s.statement_id for s in content.statements]
    if len(set(ids)) != len(ids):
        raise ContentError("duplicate statement identifiers")
    for st in content.statements:
        if st.concept_id not in concept_ids:
            raise ContentError(f"statement {st.statement_id}: unknown concept {st.concept_id}")
        if st.edition_id not in editions:
            raise ContentError(f"statement {st.statement_id}: unknown edition {st.edition_id}")
        if st.statement_kind is StatementKind.HOUSE_KARAKA:
            for p in st.attributes["karaka_planets"]:
                if p not in concept_ids:
                    raise ContentError(f"karaka planet {p} unknown")

    content.terms = _terms(terms, editions)
    content.rule_references = _rule_references(refs, rules, concept_ids)
    content.exceptions = _exceptions(refs, rules)
    by_id = {s.statement_id: s for s in content.statements}
    content.domain_mappings = _domain_mappings(domains, by_id)

    names = {
        t.concept_id: t.text
        for t in content.terms
        if t.term_kind == "NAME" and t.language == "en" and t.concept_id.startswith("PLANET.")
    }
    renderings = _rendering_units(content, names, editions)
    content.chunk_units = renderings + tarot_units
    _validate_references(content, concept_ids, editions)
    return content


def _validate_references(
    content: KnowledgeContent, concept_ids: set[str], editions: dict[str, EditionRecord]
) -> None:
    for t in content.terms:
        if t.concept_id not in concept_ids or t.edition_id not in editions:
            raise ContentError(f"term {t.term_id}: dangling reference")
    for r in content.rule_references:
        if r.concept_id not in concept_ids:
            raise ContentError(f"rule reference {r.reference_id}: dangling concept")
    for e in content.exceptions:
        if e.affected_concept_id not in concept_ids or e.edition_id not in editions:
            raise ContentError(f"exception {e.exception_id}: dangling reference")
    for m in content.domain_mappings:
        if m.domain_id not in concept_ids or m.concept_id not in concept_ids:
            raise ContentError(f"mapping {m.mapping_id}: dangling reference")
    for u in content.chunk_units:
        if u.parent_concept_id not in concept_ids or u.edition_id not in editions:
            raise ContentError(f"chunk unit {u.external_ref}: dangling reference")
        if (
            u.text_origin is TextOrigin.SOURCE_TEXT
            and editions[u.edition_id].source_id != u.source_id
        ):
            raise ContentError(f"chunk unit {u.external_ref}: source mismatch")


def all_chunks(content: KnowledgeContent) -> list[ChunkRecord]:
    from pandit_knowledge.chunking import chunk_unit

    chunks: list[ChunkRecord] = []
    for unit in content.chunk_units:
        chunks.extend(chunk_unit(unit))
    return chunks
