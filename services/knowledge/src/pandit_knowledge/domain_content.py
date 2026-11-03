"""The Phase 17 life-domain methodology knowledge: a SEPARATE knowledge version.

``load_domain_content`` reads ``services/knowledge/content/domain/`` (a subdirectory the Phase 12
loader ``load_content`` never opens: it reads named files only) and returns the same
:class:`KnowledgeContent` structure the ingestion already builds into a sealed, versioned,
immutable knowledge version. Domain methodology is therefore additive and forward-only: it is a
*different* version identifier from the Phase 12 version ``KV-06361d7aba28c1ce`` and from the
Phase 13 palm version ``KV-a21c2c040abe9663``, neither of which is touched.

Everything stored is structured, language-neutral and provenance-tagged (no prose):

* **concepts**: the 36 domains, the twelve houses and nine planets they map to, the sixteen
  divisional charts (``VARGA``) and the researched methods;
* **statements**: each domain's taxonomy entry with its research status and policy (project
  decision), the source's stated use of each divisional chart (BPHS Ch. 7 v. 1-8), the source
  significations the mappings rest on, the researched methods, the recorded source conflicts
  (``SOURCE_VARIANCE``, no winner) and the **policy notes** (a withheld source statement is
  recorded by class and location only, never by wording);
* **domain mappings**: every house, karaka, divisional-chart, method, Phase 6 rule applicability
  and withheld mapping with its own support status, profile and bridge note; a domain with no
  approved mapping carries a ``NOT_EVALUABLE`` record. **A mapping never inherits its parent's
  status.**
* **rule references**: ids of the rules of the separate domain ruleset
  (``services/rule-engine/domain_rules``) and of the Phase 6 rules a domain applicability points
  at. This package imports no rule code and reads no rule-engine file: a cross-package test asserts
  the two agree.

Validation (a violation raises :class:`DomainContentError`): every reference resolves; only the
eight locked divisional-chart mappings exist and D4 maps to no domain; a partially supported or
conflicting mapping is never labelled supported; a sub-domain never claims its parent's status; a
withheld record carries no wording; every Phase 6 rule id resolves in the Phase 6 YAML.

The manifest field ``rules_snapshot_hash`` is the hash of the rule *references* this version holds
and of the Phase 6 rule snapshot, so the version identity changes when either changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pandit_knowledge.content import (
    DEFAULT_CONTENT_DIR,
    DEFAULT_RULES_DIR,
    ContentError,
    KnowledgeContent,
    _read_yaml,
    _statements,
    rule_index,
    statement_id,
)
from pandit_knowledge.models import (
    ConceptRecord,
    ConceptType,
    Confidence,
    DomainMappingRecord,
    EditionRecord,
    IngestionPermission,
    ReadingLevel,
    RuleKind,
    RuleReferenceRecord,
    SourceRecord,
    StatementKind,
    StatementRecord,
    SupportStatus,
    sha256_hex,
)

DOMAIN_KNOWLEDGE_STANDARDS_VERSION = "1.30.0"
DEFAULT_DOMAIN_CONTENT_DIR = DEFAULT_CONTENT_DIR / "domain"
PROJECT_SOURCE = "SRC.PROJECT_PHASE17"
PROJECT_EDITION = "PHASE17_RESEARCH_LOCK"
TAXONOMY_PROFILE = "DOMAIN_TAXONOMY_P17"
#: Owner decision 3 (standards LD-09): the only divisional-chart mappings.
LOCKED_VARGA_DOMAINS: dict[int, frozenset[str]] = {
    2: frozenset({"WEALTH", "FINANCE"}),
    3: frozenset({"SIBLINGS"}),
    7: frozenset({"CHILDREN"}),
    9: frozenset({"MARRIAGE", "SPOUSE"}),
    10: frozenset({"CAREER"}),
    12: frozenset({"PARENTS"}),
    20: frozenset({"SPIRITUALITY"}),
    24: frozenset({"EDUCATION"}),
}
_PHASE12_PROFILES = frozenset(
    {
        "KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        "KB_BPHS_SAN_HOUSE_SIGNIFICATION_32_31_33",
        "KB_BPHS_SAN_HOUSE_KARAKA_32_34",
        "KB_BPHS_SAN_PLANET_KARAKATWA_3_12_13",
        "KB_PHALA_SASTRI_HOUSE_KARAKA_XV_17",
        "KB_PHALA_SASTRI_PLANET_KARAKATWA_XV_15_16",
    }
)
_SUPPORT = {
    "SOURCE_SUPPORTED": SupportStatus.SOURCE_SUPPORTED,
    "PARTIALLY_SUPPORTED": SupportStatus.PARTIALLY_SUPPORTED,
    "UNRESOLVED_CONFLICT": SupportStatus.UNRESOLVED_CONFLICT,
    "NOT_EVALUABLE": SupportStatus.NOT_EVALUABLE,
}
_LEVEL = {
    "IMAGE-TRANSLATION": ReadingLevel.PAGE_IMAGE_LEVEL,
    "OCR-TRANSLATION": ReadingLevel.OCR_LEVEL,
    "OCR-SOURCE-LANGUAGE": ReadingLevel.OCR_LEVEL,
}
_PLANETS = ("SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "RAHU", "KETU")
_VARGAS = (1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60)
_WITHHELD_TEXT_LIMIT = 80


class DomainContentError(ContentError):
    """The domain knowledge content is inconsistent or violates a boundary."""


def _fail(message: str) -> DomainContentError:
    return DomainContentError(message)


def load_domain_content(
    content_dir: Path = DEFAULT_DOMAIN_CONTENT_DIR,
    phase12_dir: Path = DEFAULT_CONTENT_DIR,
    rules_dir: Path = DEFAULT_RULES_DIR,
) -> KnowledgeContent:
    taxonomy = _read_yaml(content_dir / "taxonomy.yaml")
    mappings_doc = _read_yaml(content_dir / "mappings.yaml")
    conflicts_doc = _read_yaml(content_dir / "conflicts.yaml")
    varga_doc = _read_yaml(content_dir / "varga.yaml")
    src_data = _read_yaml(phase12_dir / "sources.yaml")
    houses = _read_yaml(phase12_dir / "houses.yaml")
    planets = _read_yaml(phase12_dir / "planets.yaml")

    phase6_ids, phase6_hash = rule_index(rules_dir)
    content = KnowledgeContent()

    # -- sources and editions: only what the domain mappings rest on, plus the project decision
    wanted_sources = {"SRC.BPHS", "SRC.PHALADEEPIKA", "SRC.BRIHAT_JATAKA"}
    content.sources = [
        SourceRecord(
            **{**s, "ingestion_permission": IngestionPermission(s["ingestion_permission"])}
        )
        for s in src_data["sources"]
        if s["source_id"] in wanted_sources
    ]
    content.sources.append(
        SourceRecord(
            source_id=PROJECT_SOURCE,
            title="Pandit Ji Phase 17 research record and owner decisions",
            author="Project",
            tradition="Project decision",
            original_language="en",
            source_classification="PROJECT_DECISION",
            copyright_status="Project-authored",
            ingestion_permission=IngestionPermission.FULL_TEXT_PUBLIC_DOMAIN,
            copyright_note="Structured project decisions only; no source text.",
            registry_ref="research/PHASE_17_LIFE_DOMAIN_RESEARCH.md",
        )
    )
    content.editions = [
        EditionRecord(**{**e, "reading_level": ReadingLevel(e["reading_level"])})
        for e in src_data["editions"]
        if e["source_id"] in wanted_sources
    ]
    content.editions.append(
        EditionRecord(
            edition_id=PROJECT_EDITION,
            source_id=PROJECT_SOURCE,
            edition_label="Research and architecture lock and owner decisions, 2026-10-06",
            translator="",
            publisher="Pandit Ji project",
            publication_year="2026",
            language="en",
            location_url="research/PHASE_17_LIFE_DOMAIN_RESEARCH.md",
            reading_level=ReadingLevel.NOT_APPLICABLE,
            registry_verification_level="NONE",
        )
    )
    editions = {e.edition_id: e for e in content.editions}
    source_to_edition = {
        "BPHS_SANTHANAM_1984": "BPHS_SANTHANAM_1984",
        "BPHS_KAPOOR_1987": "BPHS_KAPOOR_1987",
        "PHALADEEPIKA_SASTRI": "PHALADEEPIKA_SASTRI",
        "JATAKA_PARIJATA_CHAUKHAMBHA": PROJECT_EDITION,
    }

    # -- concepts
    concepts: dict[str, ConceptRecord] = {}

    def concept(cid: str, ctype: ConceptType, key: str) -> None:
        rec = ConceptRecord(concept_id=cid, concept_type=ctype, canonical_key=key)
        if cid in concepts and concepts[cid] != rec:
            raise _fail(f"concept {cid} defined twice differently")
        concepts[cid] = rec

    domains = {d["domain"]: d for d in taxonomy["domains"]}
    for name in domains:
        concept(f"DOMAIN.{name}", ConceptType.DOMAIN, name.lower())
    for n in range(1, 13):
        concept(f"HOUSE.{n:02d}", ConceptType.HOUSE, str(n))
    for planet in _PLANETS:
        concept(f"PLANET.{planet}", ConceptType.PLANET, planet.lower())
    for n in _VARGAS:
        concept(f"VARGA.D{n}", ConceptType.VARGA, f"d{n}")

    # -- Phase 12 significations the mappings cite (reused verbatim, same ids)
    base = [
        s
        for s in _statements(houses, editions) + _statements(planets, editions)
        if s.profile_id in _PHASE12_PROFILES
    ]
    statements: dict[str, StatementRecord] = {s.statement_id: s for s in base}

    def add_statement(rec: StatementRecord) -> None:
        if rec.statement_id in statements:
            raise _fail(f"duplicate statement {rec.statement_id}")
        statements[rec.statement_id] = rec

    profiles = mappings_doc["profiles"]

    def profile_edition(profile_id: str) -> str:
        if profile_id in profiles:
            return source_to_edition[profiles[profile_id]["source"]]
        return PROJECT_EDITION

    # -- taxonomy statements (project decision, never a source claim)
    mapped_domains = {m["domain"] for m in mappings_doc["mappings"]}
    for name, entry in domains.items():
        attributes: dict[str, Any] = {
            "label": entry["label"],
            "parent": entry.get("parent"),
            "kind": entry["kind"],
            "research_support": entry["support"],
            "policy_classes": list(entry.get("policy", [])),
            "adult_confirmation_required": bool(entry.get("adult_confirmation_required", False)),
            "blocked_reason": entry.get("blocked_reason"),
            "not_evaluable_reason": entry.get("not_evaluable_reason"),
            "has_approved_mappings": name in mapped_domains,
            "support_inherited_from_parent": False,
        }
        if entry["support"] != "NOT_EVALUABLE" and name not in mapped_domains:
            if not entry.get("not_evaluable_reason"):
                raise _fail(f"{name}: supported without a mapping or an explicit reason")
        parent = entry.get("parent")
        if parent is not None and parent not in domains:
            raise _fail(f"{name}: unknown parent {parent}")
        add_statement(
            StatementRecord(
                statement_id=statement_id(TAXONOMY_PROFILE, f"DOMAIN.{name}", "DOMAIN_DEFINITION"),
                concept_id=f"DOMAIN.{name}",
                statement_kind=StatementKind.DOMAIN_DEFINITION,
                profile_id=TAXONOMY_PROFILE,
                edition_id=PROJECT_EDITION,
                source_location="research/PHASE_17_LIFE_DOMAIN_RESEARCH.md s.0 and matrix sheet F",
                location_kind="derived",
                reading_level=ReadingLevel.NOT_APPLICABLE,
                registry_verification_level="NONE",
                confidence=Confidence.HIGH,
                support_status=SupportStatus.PROJECT_DERIVED,
                language="und",
                attributes=attributes,
            )
        )

    # -- the divisional charts as BPHS Ch. 7 v. 1-8 states their use
    for use in varga_doc["varga_uses"]:
        n = int(use["varga"])
        mapped = sorted(use["mapped_domains"])
        if n in LOCKED_VARGA_DOMAINS:
            if set(mapped) != LOCKED_VARGA_DOMAINS[n]:
                raise _fail(f"D{n}: mapped domains differ from the locked mapping")
        elif mapped:
            raise _fail(f"D{n} is not a locked divisional-chart mapping")
        add_statement(
            StatementRecord(
                statement_id=statement_id(varga_doc["profile"], f"VARGA.D{n}", "VARGA_USE"),
                concept_id=f"VARGA.D{n}",
                statement_kind=StatementKind.VARGA_USE,
                profile_id=varga_doc["profile"],
                edition_id=source_to_edition[varga_doc["source"]],
                source_location=varga_doc["location"],
                location_kind="verse",
                reading_level=ReadingLevel.PAGE_IMAGE_LEVEL,
                registry_verification_level="IMAGE-TRANSLATION",
                confidence=Confidence.HIGH,
                support_status=SupportStatus.SOURCE_SUPPORTED,
                language="en",
                attributes={"source_term": use["source_term"], "mapped_domains": mapped},
            )
        )

    # -- the source's own terms for the mappings that rest on a non-Phase-12 profile
    by_profile_concept: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for m in mappings_doc["mappings"]:
        target = m["target"]
        if (
            m["kind"] in {"HOUSE_RELEVANCE", "KARAKA_RELEVANCE"}
            and m["profile"] not in _PHASE12_PROFILES
        ):
            by_profile_concept.setdefault((m["profile"], target), []).append(m)
    for (profile_id, target), items in sorted(by_profile_concept.items()):
        meta = profiles[profile_id]
        add_statement(
            StatementRecord(
                statement_id=statement_id(profile_id, target, "SIGNIFICATION"),
                concept_id=target,
                statement_kind=StatementKind.SIGNIFICATION,
                profile_id=profile_id,
                edition_id=profile_edition(profile_id),
                source_location=meta["location"],
                location_kind="verse",
                reading_level=_LEVEL[meta["registry_level"]],
                registry_verification_level=meta["registry_level"],
                confidence=Confidence(meta["confidence"]),
                support_status=SupportStatus.PARTIALLY_SUPPORTED
                if all(i["support"] != "SOURCE_SUPPORTED" for i in items)
                else SupportStatus.SOURCE_SUPPORTED,
                language="en",
                attributes={"items": sorted({i["source_term"] for i in items})},
            )
        )

    # -- methods (how a source says a relation is read), conflicts, policy notes
    method_concepts: dict[str, str] = {}
    for m in mappings_doc["mappings"]:
        if m["kind"] in {"MARRIAGE_DASHA_METHOD", "BHAVA_TRANSIT_METHOD", "SUBJECT_PROFICIENCY"}:
            cid = "METHOD." + m["target"].split(".", 1)[1].replace(".", "_")
            method_concepts[m["mapping_id"]] = cid
            concept(cid, ConceptType.CONCEPT, cid.split(".", 1)[1].lower())
            meta = profiles[m["profile"]]
            add_statement(
                StatementRecord(
                    statement_id=statement_id(m["profile"], cid, "READING_CONVENTION"),
                    concept_id=cid,
                    statement_kind=StatementKind.READING_CONVENTION,
                    profile_id=m["profile"],
                    edition_id=profile_edition(m["profile"]),
                    source_location=meta["location"],
                    location_kind="verse",
                    reading_level=_LEVEL[meta["registry_level"]],
                    registry_verification_level=meta["registry_level"],
                    confidence=Confidence(meta["confidence"]),
                    support_status=_SUPPORT[m["support"]],
                    language="en",
                    attributes={
                        "source_term": m["source_term"],
                        "domain": m["domain"],
                        "bridge": m["bridge"],
                    },
                )
            )

    for c in conflicts_doc["conflicts"]:
        anchor = {
            "DC-01": "DOMAIN.PARENTS",
            "DC-02": "DOMAIN.MARRIAGE",
            "DC-03": "DOMAIN.CAREER",
            "DC-04": "DOMAIN.CAREER",
            "DC-05": "VARGA.D4",
            "KUJA_DOSHA_TOPIC": "DOMAIN.MARRIAGE",
        }[c["conflict_id"]]
        add_statement(
            StatementRecord(
                statement_id=statement_id(
                    TAXONOMY_PROFILE, anchor, f"SOURCE_VARIANCE.{c['conflict_id']}"
                ),
                concept_id=anchor,
                statement_kind=StatementKind.SOURCE_VARIANCE,
                profile_id=TAXONOMY_PROFILE,
                edition_id=PROJECT_EDITION,
                source_location="research/PHASE_17_LIFE_DOMAIN_RESEARCH.md section 12",
                location_kind="derived",
                reading_level=ReadingLevel.NOT_APPLICABLE,
                registry_verification_level="NONE",
                confidence=Confidence.HIGH,
                support_status=SupportStatus.UNRESOLVED_CONFLICT,
                language="und",
                attributes={
                    "conflict_id": c["conflict_id"],
                    "profiles": list(c["profiles"]),
                    "resolution": "NONE",
                },
            )
        )

    for m in mappings_doc["mappings"]:
        flagged = m["kind"] == "POLICY_WITHHELD" or m.get("blocked")
        if not flagged:
            continue
        domain_cid = f"DOMAIN.{m['domain']}"
        add_statement(
            StatementRecord(
                statement_id=statement_id(
                    m["profile"], domain_cid, f"POLICY_NOTE.{m['mapping_id']}"
                ),
                concept_id=domain_cid,
                statement_kind=StatementKind.POLICY_NOTE,
                profile_id=m["profile"],
                edition_id=profile_edition(m["profile"]),
                source_location=(
                    profiles[m["profile"]]["location"]
                    if m["profile"] in profiles
                    else "Phase 6 rule"
                ),
                location_kind="derived",
                reading_level=ReadingLevel.NOT_APPLICABLE,
                registry_verification_level="NONE",
                confidence=Confidence.HIGH,
                support_status=SupportStatus.PROJECT_DERIVED,
                language="und",
                # class and reason only: the withheld wording is never stored here
                attributes={
                    "mapping_id": m["mapping_id"],
                    "reason": m.get("withheld_reason")
                    or (
                        "SPOUSE_LONGEVITY_BLOCKED"
                        if m.get("phase6_signification") == "marriage.spouse_longevity"
                        else "HISTORICAL_STATEMENT_WITHHELD"
                    ),
                    "policy_classes": list(m.get("policy_flags", [])),
                    "transformation": "NOT_EVALUABLE"
                    if m.get("outcome") == "NOT_EVALUABLE"
                    else "BLOCK",
                },
            )
        )

    # -- domain mappings
    mappings: list[DomainMappingRecord] = []
    rule_refs: list[RuleReferenceRecord] = []
    seen_mapping_ids: set[str] = set()
    for m in mappings_doc["mappings"]:
        if m["mapping_id"] in seen_mapping_ids:
            raise _fail(f"duplicate mapping {m['mapping_id']}")
        seen_mapping_ids.add(m["mapping_id"])
        domain_cid = f"DOMAIN.{m['domain']}"
        if domain_cid not in concepts:
            raise _fail(f"{m['mapping_id']}: unknown domain")
        support = _SUPPORT[m["support"]]
        entry = domains[m["domain"]]
        if entry["support"] == "NOT_EVALUABLE":
            raise _fail(f"{m['mapping_id']}: a NOT_EVALUABLE domain has no approved mapping")
        if entry.get("blocked_reason"):
            raise _fail(f"{m['mapping_id']}: a policy-blocked domain has no mapping")
        kind = m["kind"]
        target = m["target"]
        if kind == "VARGA_RELEVANCE":
            n = int(target.split(".D")[1])
            if m["domain"] not in LOCKED_VARGA_DOMAINS.get(n, frozenset()):
                raise _fail(f"{m['mapping_id']}: D{n} is not an approved mapping for {m['domain']}")
        if support is SupportStatus.UNRESOLVED_CONFLICT and not m.get("conflict_ids"):
            raise _fail(f"{m['mapping_id']}: a conflicting mapping names its conflict")
        for cid in m.get("conflict_ids", []):
            if cid not in {c["conflict_id"] for c in conflicts_doc["conflicts"]}:
                raise _fail(f"{m['mapping_id']}: unknown conflict {cid}")
        if kind in {"HOUSE_RELEVANCE", "KARAKA_RELEVANCE", "VARGA_RELEVANCE"}:
            concept_id = target
        elif m["mapping_id"] in method_concepts:
            concept_id = method_concepts[m["mapping_id"]]
        else:
            concept_id = domain_cid
        if concept_id not in concepts:
            raise _fail(f"{m['mapping_id']}: unknown target {concept_id}")
        supports: list[str] = []
        if kind == "HOUSE_RELEVANCE" or kind == "KARAKA_RELEVANCE":
            candidates = [statement_id(m["profile"], target, "SIGNIFICATION")]
            if m.get("for_house"):
                candidates.append(
                    statement_id(m["profile"], f"HOUSE.{int(m['for_house']):02d}", "HOUSE_KARAKA")
                )
            for sid in candidates:
                if sid in statements:
                    supports.append(sid)
            if not supports:
                raise _fail(f"{m['mapping_id']}: no supporting statement for {target}")
        elif kind == "VARGA_RELEVANCE":
            supports.append(statement_id(varga_doc["profile"], target, "VARGA_USE"))
        elif m["mapping_id"] in method_concepts:
            supports.append(statement_id(m["profile"], concept_id, "READING_CONVENTION"))
        if kind == "PHASE6_RULE_APPLICABILITY":
            rid = m["phase6_rule_id"]
            if phase6_ids.get(rid) != "RULE":
                raise _fail(f"{m['mapping_id']}: {rid} is not a Phase 6 rule")
            rule_refs.append(
                RuleReferenceRecord(
                    reference_id=f"RR.{domain_cid}.{rid}",
                    concept_id=domain_cid,
                    rule_id=rid,
                    rule_kind=RuleKind.RULE,
                    relation="DOMAIN_APPLICABILITY",
                    profile_id=m["profile"],
                    source_location="Phase 6 rule",
                )
            )
        rule_refs.append(
            RuleReferenceRecord(
                reference_id=f"RR.{domain_cid}.{m['rule_id']}",
                concept_id=domain_cid,
                rule_id=m["rule_id"],
                rule_kind=RuleKind.DOMAIN_RULE,
                relation="EXECUTES_MAPPING:" + m["mapping_id"],
                profile_id=m["profile"],
                source_location=profiles[m["profile"]]["location"]
                if m["profile"] in profiles
                else "Phase 6 rule",
            )
        )
        note = m["bridge"] or m["source_term"]
        if m.get("conflict_ids"):
            note = f"{note} [conflict: {','.join(m['conflict_ids'])}]".strip()
        mappings.append(
            DomainMappingRecord(
                mapping_id=m["mapping_id"],
                domain_id=domain_cid,
                concept_id=concept_id,
                support_status=support,
                supporting_statement_ids=tuple(supports),
                profile_id=m["profile"],
                bridge_note=" ".join(str(note).split()),
            )
        )
    for name, entry in sorted(domains.items()):
        if name in mapped_domains:
            continue
        if entry["support"] != "NOT_EVALUABLE" and not entry.get("not_evaluable_reason"):
            raise _fail(f"{name}: no mapping and no stated reason")
        reason = (
            entry.get("blocked_reason") or entry.get("not_evaluable_reason") or "NO_SOURCE_READ"
        )
        mappings.append(
            DomainMappingRecord(
                mapping_id=f"MAP.{name}.DOMAIN",
                domain_id=f"DOMAIN.{name}",
                concept_id=f"DOMAIN.{name}",
                support_status=SupportStatus.NOT_EVALUABLE,
                supporting_statement_ids=(),
                profile_id="NONE",
                bridge_note=f"No approved methodology: {reason}.",
            )
        )

    for rec in mappings:
        if rec.domain_id not in concepts or rec.concept_id not in concepts:
            raise _fail(f"mapping {rec.mapping_id}: dangling reference")
        for sid in rec.supporting_statement_ids:
            if sid not in statements:
                raise _fail(f"mapping {rec.mapping_id}: support {sid} not found")
    for st in statements.values():
        if st.concept_id not in concepts:
            raise _fail(f"statement {st.statement_id}: unknown concept {st.concept_id}")
        if st.edition_id not in editions:
            raise _fail(f"statement {st.statement_id}: unknown edition {st.edition_id}")
    for ref in rule_refs:
        if ref.concept_id not in concepts:
            raise _fail(f"rule reference {ref.reference_id}: dangling concept")

    content.concepts = sorted(concepts.values(), key=lambda c: c.concept_id)
    content.statements = sorted(statements.values(), key=lambda s: s.statement_id)
    content.domain_mappings = sorted(mappings, key=lambda m: m.mapping_id)
    content.rule_references = sorted(rule_refs, key=lambda r: r.reference_id)
    content.rules_snapshot_hash = sha256_hex(
        {
            "domain_rule_references": [
                (r.rule_id, r.rule_kind.value, r.relation) for r in content.rule_references
            ],
            "phase6_rules_snapshot": phase6_hash,
        }
    )
    return content


__all__ = [
    "DEFAULT_DOMAIN_CONTENT_DIR",
    "DOMAIN_KNOWLEDGE_STANDARDS_VERSION",
    "DomainContentError",
    "LOCKED_VARGA_DOMAINS",
    "load_domain_content",
]
