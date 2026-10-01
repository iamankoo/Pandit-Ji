"""The curated Phase 12 content: structure, provenance and boundaries (KB-01 to KB-34)."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pytest
import yaml

from pandit_knowledge.content import (
    DEFAULT_CONTENT_DIR,
    DEFAULT_RULES_DIR,
    ContentError,
    KnowledgeContent,
    all_chunks,
    load_content,
    rule_index,
)
from pandit_knowledge.models import (
    IngestionPermission,
    KnowledgeDomain,
    RuleKind,
    StatementKind,
    SupportStatus,
    TextOrigin,
)
from pandit_knowledge.validation import personal_data_findings

PLANETS = [
    "PLANET.SUN",
    "PLANET.MOON",
    "PLANET.MARS",
    "PLANET.MERCURY",
    "PLANET.JUPITER",
    "PLANET.VENUS",
    "PLANET.SATURN",
    "PLANET.RAHU",
    "PLANET.KETU",
]
HOUSES = [f"HOUSE.{n:02d}" for n in range(1, 13)]


def test_canonical_planet_and_house_concepts(content: KnowledgeContent) -> None:
    ids = {c.concept_id for c in content.concepts}
    assert set(PLANETS) <= ids
    assert set(HOUSES) <= ids
    assert {"DOMAIN.CAREER", "DOMAIN.MARRIAGE", "DOMAIN.FINANCE", "DOMAIN.EDUCATION"} <= ids


def test_concept_identifiers_are_language_neutral(content: KnowledgeContent) -> None:
    for c in content.concepts:
        assert c.concept_id.isascii()
        assert c.concept_id == c.concept_id.strip()
    for st in content.statements:
        for item in st.attributes.get("items", []):
            assert item["id"].isascii()
            assert item["id"].startswith(("SIG.", "ROLE."))


def test_every_statement_has_full_provenance(content: KnowledgeContent) -> None:
    editions = {e.edition_id for e in content.editions}
    for st in content.statements:
        assert st.edition_id in editions
        assert st.profile_id
        assert st.source_location
        assert st.registry_verification_level
        assert st.statement_id.startswith("ST.")


def test_each_source_statement_belongs_to_exactly_one_profile(content: KnowledgeContent) -> None:
    """Profiles are never merged: a statement names one profile; only derived rows span two."""
    for st in content.statements:
        if st.statement_kind is StatementKind.SOURCE_VARIANCE:
            assert st.profile_id.startswith("CROSS_SOURCE.")
        else:
            assert not st.profile_id.startswith("CROSS_SOURCE.")


def test_every_planet_has_a_bphs_role_and_planets_have_significations(
    content: KnowledgeContent,
) -> None:
    roles = {
        s.concept_id
        for s in content.statements
        if s.statement_kind is StatementKind.ROLE and s.edition_id == "BPHS_SANTHANAM_1984"
    }
    assert roles == set(PLANETS)
    seven = set(PLANETS[:7])
    for profile in (
        "KB_BPHS_SAN_PLANET_KARAKATWA_3_12_13",
        "KB_BJ_SASTRI_PLANET_KARAKATWA_2_1",
    ):
        covered = {
            s.concept_id
            for s in content.statements
            if s.profile_id == profile and s.statement_kind is StatementKind.SIGNIFICATION
        }
        assert covered == seven, profile
    nine = {
        s.concept_id
        for s in content.statements
        if s.profile_id == "KB_PHALA_SASTRI_PLANET_KARAKATWA_XV_15_16"
    }
    assert nine == set(PLANETS)


def test_every_house_has_a_bphs_ch11_signification_and_both_karaka_tables(
    content: KnowledgeContent,
) -> None:
    for profile in (
        "KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        "KB_BPHS_SAN_HOUSE_KARAKA_32_34",
        "KB_PHALA_SASTRI_HOUSE_KARAKA_XV_17",
    ):
        houses = {
            s.concept_id
            for s in content.statements
            if s.profile_id == profile and s.concept_id.startswith("HOUSE.")
        }
        assert houses == set(HOUSES), profile


def test_house_karaka_tables_match_the_images_read(content: KnowledgeContent) -> None:
    by = {
        (s.profile_id, s.concept_id): s.attributes["karaka_planets"]
        for s in content.statements
        if s.statement_kind is StatementKind.HOUSE_KARAKA
    }
    bphs = [by[("KB_BPHS_SAN_HOUSE_KARAKA_32_34", h)] for h in HOUSES]
    assert [p[0].split(".")[1] for p in bphs] == [
        "SUN", "JUPITER", "MARS", "MOON", "JUPITER", "MARS",
        "VENUS", "SATURN", "JUPITER", "MERCURY", "JUPITER", "SATURN",
    ]  # fmt: skip
    assert by[("KB_PHALA_SASTRI_HOUSE_KARAKA_XV_17", "HOUSE.10")] == [
        "PLANET.JUPITER",
        "PLANET.SUN",
        "PLANET.MERCURY",
        "PLANET.SATURN",
    ]


def test_karaka_source_differences_are_recorded_not_resolved(content: KnowledgeContent) -> None:
    variances = [s for s in content.statements if s.profile_id == "CROSS_SOURCE.HOUSE_KARAKA"]
    assert {v.concept_id for v in variances} == {"HOUSE.04", "HOUSE.06", "HOUSE.09", "HOUSE.10"}
    for v in variances:
        assert v.support_status is SupportStatus.UNRESOLVED_CONFLICT
        assert len(v.attributes["profiles"]) == 2


def test_house_two_wife_conflict_is_preserved(content: KnowledgeContent) -> None:
    variance = next(
        s for s in content.statements if s.profile_id == "CROSS_SOURCE.HOUSE_SIGNIFICATION"
    )
    assert variance.concept_id == "HOUSE.02"
    assert variance.support_status is SupportStatus.UNRESOLVED_CONFLICT
    sets = variance.attributes["profiles"]
    assert "SIG.WIFE" in sets["KB_BPHS_SAN_HOUSE_SIGNIFICATION_32_31_33"]
    assert "SIG.WIFE" not in sets["KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13"]


def test_derived_inversion_is_labelled_project_derived(content: KnowledgeContent) -> None:
    derived = [s for s in content.statements if s.statement_kind is StatementKind.DERIVED_INVERSION]
    assert derived
    for d in derived:
        assert d.support_status is SupportStatus.PROJECT_DERIVED
        assert d.location_kind == "derived"
        assert d.attributes["method"] == "MECHANICAL_INVERSION_OF_SOURCE_TABLE"
    jupiter = next(
        d
        for d in derived
        if d.concept_id == "PLANET.JUPITER" and d.profile_id == "KB_BPHS_SAN_HOUSE_KARAKA_32_34"
    )
    assert jupiter.attributes["houses"] == ["HOUSE.02", "HOUSE.05", "HOUSE.09", "HOUSE.11"]


def test_domain_mappings_cover_every_pair_and_never_overclaim(content: KnowledgeContent) -> None:
    pairs = {(m.domain_id, m.concept_id): m for m in content.domain_mappings}
    assert len(pairs) == 4 * 12
    supported = {k for k, m in pairs.items() if m.support_status is SupportStatus.SOURCE_SUPPORTED}
    assert supported == {
        ("DOMAIN.CAREER", "HOUSE.10"),
        ("DOMAIN.MARRIAGE", "HOUSE.07"),
        ("DOMAIN.FINANCE", "HOUSE.02"),
        ("DOMAIN.FINANCE", "HOUSE.11"),
        ("DOMAIN.FINANCE", "HOUSE.12"),
        ("DOMAIN.EDUCATION", "HOUSE.05"),
    }
    assert (
        pairs[("DOMAIN.MARRIAGE", "HOUSE.02")].support_status is SupportStatus.UNRESOLVED_CONFLICT
    )
    for key, m in pairs.items():
        if key not in supported and key != ("DOMAIN.MARRIAGE", "HOUSE.02"):
            assert m.support_status is SupportStatus.NOT_EVALUABLE
            assert m.supporting_statement_ids == ()
        else:
            assert m.supporting_statement_ids
            assert "Pandit Ji" in m.bridge_note or "Source term" in m.bridge_note or m.bridge_note


def test_education_house_four_is_not_evaluable_with_a_reason(content: KnowledgeContent) -> None:
    m = next(
        m
        for m in content.domain_mappings
        if m.domain_id == "DOMAIN.EDUCATION" and m.concept_id == "HOUSE.04"
    )
    assert m.support_status is SupportStatus.NOT_EVALUABLE
    assert "no source read in Phase 12" in m.bridge_note


def test_rule_references_resolve_to_the_phase6_rule_files(content: KnowledgeContent) -> None:
    index, _ = rule_index(DEFAULT_RULES_DIR)
    seen = 0
    for r in content.rule_references:
        if r.rule_kind in (RuleKind.RULE, RuleKind.TABLE):
            assert index[r.rule_id] == r.rule_kind.value
            seen += 1
    assert seen > 40


def test_relationship_data_is_referenced_never_restated(content: KnowledgeContent) -> None:
    tables = {r.rule_id for r in content.rule_references if r.rule_kind is RuleKind.TABLE}
    assert {
        "BPHS_SAN_REL_NATURAL_3_55",
        "BPHS_SAN_REL_TEMPORAL_3_56",
        "BPHS_SAN_REL_COMPOUND_3_57_58",
        "BPHS_SAN_NATURE_3_11",
    } <= tables
    allowed = {
        "items",
        "karaka_planets",
        "houses",
        "derived_from_profile",
        "method",
        "kind",
        "profiles",
        "editions",
        "note",
        "tags",
        "threshold",
        "threshold_status",
    }
    for st in content.statements:
        assert set(st.attributes) <= allowed, st.statement_id


def test_exceptions_are_first_class_and_never_merged(content: KnowledgeContent) -> None:
    ids = {e.exception_id for e in content.exceptions}
    assert len(ids) == len(content.exceptions) == 3 + 7
    kem = [
        e for e in content.exceptions if e.affected_rule_id == "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5"
    ]
    assert len(kem) == 2
    assert not [
        e for e in content.exceptions if e.affected_rule_id == "BPHS_SAN_KEMADRUMA_37_11_13"
    ]
    for e in content.exceptions:
        assert e.source_location and e.edition_id and e.profile_id


def test_strength_has_no_threshold(content: KnowledgeContent) -> None:
    notes = [s for s in content.statements if s.statement_kind is StatementKind.STRENGTH_NOTE]
    assert len(notes) == 1
    assert notes[0].attributes["threshold"] is None
    assert notes[0].attributes["threshold_status"] == "NOT_LOCKED_SM_11"
    assert notes[0].location_kind == "note"
    strength_refs = {
        r.rule_id for r in content.rule_references if r.concept_id == "CONCEPT.STRENGTH"
    }
    assert strength_refs == {"SHADBALA_RAMAN_GRAHA_BHAVA_BALAS", "SHADBALA_BPHS_SANTHANAM_27_VERSE"}
    text = " ".join(
        u.text.lower() for u in content.chunk_units if u.knowledge_domain.value == "VEDIC"
    )
    for banned in ("strong planet", "weak planet", "is strong", "is weak", "virupa"):
        assert banned not in text


def test_terms_never_invent_hindi_or_hinglish(content: KnowledgeContent) -> None:
    for t in content.terms:
        assert t.language in {"en", "sa", "sa-Latn"}
        assert t.language not in {"hi", "hi-Latn"}
        if t.script == "Deva":
            assert t.verification_status == "SANSKRIT_READ_ON_PAGE_IMAGE_UNREVIEWED"
    assert {t.script for t in content.terms} == {"Latn", "Deva"}


def test_mars_ketu_and_rahu_terms_match_the_page_image(content: KnowledgeContent) -> None:
    deva = {t.concept_id: t.text for t in content.terms if t.script == "Deva"}
    assert deva["PLANET.RAHU"] == "स्वर्भानु"
    assert deva["PLANET.KETU"] == "पुच्छक"
    assert deva["PLANET.MARS"] == "धरात्मज"


def test_sources_state_what_may_be_stored(content: KnowledgeContent) -> None:
    perms = {s.source_id: s.ingestion_permission for s in content.sources}
    assert perms["SRC.WAITE_PICTORIAL_KEY"] is IngestionPermission.FULL_TEXT_PUBLIC_DOMAIN
    for sid in ("SRC.BPHS", "SRC.PHALADEEPIKA", "SRC.BRIHAT_JATAKA"):
        assert perms[sid] is IngestionPermission.FACTS_AND_CITATIONS_ONLY
    for sid in ("SRC.CHEIRO", "SRC.BALLIETT", "SRC.LAL_KITAB"):
        assert perms[sid] is IngestionPermission.DEFERRED_UNRESOLVED
    assert perms["SRC.JATAKA_PARIJATA"] is IngestionPermission.LOCATION_ONLY


def test_only_public_domain_text_is_stored_verbatim(content: KnowledgeContent) -> None:
    pd = {
        s.source_id
        for s in content.sources
        if s.ingestion_permission is IngestionPermission.FULL_TEXT_PUBLIC_DOMAIN
    }
    for u in content.chunk_units:
        if u.text_origin is TextOrigin.SOURCE_TEXT:
            assert u.source_id in pd
    # No chunk is built from a source whose text may not be stored.
    blocked = {
        s.source_id
        for s in content.sources
        if s.ingestion_permission
        in (IngestionPermission.DEFERRED_UNRESOLVED, IngestionPermission.LOCATION_ONLY)
    }
    assert not {u.source_id for u in content.chunk_units} & blocked


def test_no_lal_kitab_numerology_or_remedy_content_is_stored(content: KnowledgeContent) -> None:
    texts = [c.text.lower() for c in all_chunks(content)]
    blob = " ".join(texts)
    assert "lal kitab" not in blob
    assert not [c for c in all_chunks(content) if c.source_id in {"SRC.CHEIRO", "SRC.BALLIETT"}]
    for banned in ("remed", "mantra", "gemstone", "puja", "lucky number"):
        assert banned not in blob
    assert not [s for s in content.statements if "REMED" in str(s.attributes).upper()]


def test_corpus_holds_no_personal_data(content: KnowledgeContent) -> None:
    assert personal_data_findings(content) == []


def test_chunk_domains_and_origins(content: KnowledgeContent) -> None:
    chunks = all_chunks(content)
    by_domain = Counter(c.knowledge_domain for c in chunks)
    assert by_domain[KnowledgeDomain.TAROT] == 78
    assert by_domain[KnowledgeDomain.VEDIC] > 100
    for c in chunks:
        if c.knowledge_domain is KnowledgeDomain.TAROT:
            assert c.text_origin is TextOrigin.SOURCE_TEXT
            assert c.language == "en"
        else:
            assert c.text_origin is TextOrigin.PROJECT_RENDERING


def test_bad_rule_reference_fails_the_build(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    shutil.copytree(DEFAULT_CONTENT_DIR, content_dir)
    path = content_dir / "references.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["rule_references"][0]["rule_id"] = "NO_SUCH_RULE"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="NO_SUCH_RULE"):
        load_content(content_dir)


def test_unknown_edition_fails_the_build(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    shutil.copytree(DEFAULT_CONTENT_DIR, content_dir)
    path = content_dir / "planets.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["profiles"]["KB_BJ_SASTRI_PLANET_KARAKATWA_2_1"]["edition"] = "NO_SUCH_EDITION"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(KeyError):
        load_content(content_dir)


def test_bad_signification_tag_fails_the_build(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    shutil.copytree(DEFAULT_CONTENT_DIR, content_dir)
    path = content_dir / "planets.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["statements"][0]["items"][0]["id"] = "soul"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="bad tag shape"):
        load_content(content_dir)


def test_rules_snapshot_hash_is_line_ending_independent(tmp_path: Path) -> None:
    rules = tmp_path / "rules"
    shutil.copytree(DEFAULT_RULES_DIR, rules)
    _, baseline = rule_index(rules)
    for f in rules.rglob("*.yaml"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert rule_index(rules)[1] == baseline


# ---- the content is a projection of the single canonical registry --------------------------
REGISTRY = Path(__file__).resolve().parents[3] / "research" / "ASTROLOGY_SOURCES.md"


def test_every_source_names_an_entry_in_the_canonical_registry(content: KnowledgeContent) -> None:
    registry = REGISTRY.read_text(encoding="utf-8")
    for source in content.sources:
        assert source.registry_ref in registry, source.source_id


def test_profile_ids_and_the_registry_agree_in_both_directions(content: KnowledgeContent) -> None:
    import re

    registry = REGISTRY.read_text(encoding="utf-8")
    ours = {s.profile_id for s in content.statements if s.profile_id.startswith("KB_")}
    ours |= {t.profile_id for t in content.terms}
    assert ours
    for profile in ours:
        assert f"`{profile}`" in registry, profile
    section = registry[registry.index("### 6.10 Phase 12 knowledge profile IDs") :]
    listed = set(re.findall(r"`(KB_[A-Z0-9_]+)`", section))
    ours_all = ours | {"KB_BPHS_SAN_STRENGTH_NOTE_3_12_13"}
    assert listed == ours_all
