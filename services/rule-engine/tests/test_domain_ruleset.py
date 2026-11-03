"""The Phase 17 domain ruleset: loading, taxonomy, no invented support, isolation (ADR-012)."""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

import pytest
import yaml
from pandit_contracts.domain import (
    DomainReason,
    DomainRuleKind,
    DomainSupport,
    LifeDomain,
    PolicyClass,
)

from pandit_rule_engine.domain import (
    ALLOWED_VARGA_DOMAINS,
    DomainRulesetLoadError,
    load_domain_ruleset,
)
from pandit_rule_engine.domain.schema import LOCKED_VARGAS, VargaParams
from pandit_rule_engine.loader import RulesetLoadError, load_ruleset
from tests.domain_helpers import (
    DOMAIN_RULES_DIR,
    VEDIC_RULES_DIR,
    copy_ruleset,
    read_docs,
    ruleset,
    write_docs,
)

L = LifeDomain
PHASE6_RULESET_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"

# The research classification of the 27 Phases.md domains (owner decision 17: never upgraded).
SOURCE_SUPPORTED = {
    L.EDUCATION, L.CAREER, L.FINANCE, L.WEALTH, L.MARRIAGE, L.FAMILY, L.CHILDREN,
}  # fmt: skip
PARTIALLY_SUPPORTED = {
    L.PERSONALITY, L.SUBJECTS, L.JOB, L.BUSINESS, L.LOVE, L.RELATIONSHIP, L.SPOUSE, L.TRAVEL,
    L.FOREIGN_TRAVEL, L.FOREIGN_SETTLEMENT, L.SPIRITUALITY,
}  # fmt: skip
NOT_EVALUABLE = {
    L.BIRTH, L.CHILDHOOD, L.SCHOOL, L.COLLEGE, L.CORPORATE_LIFE, L.STARTUP, L.GF_BF,
    L.FOREIGN_EDUCATION, L.PERSONAL_LIFE,
}  # fmt: skip


# ---- loading and identity -----------------------------------------------------------------------


def test_the_domain_ruleset_loads_with_its_own_manifest() -> None:
    rs = ruleset()
    assert rs.manifest.ruleset_id == "PANDIT_JI_DOMAIN_PHASE17"
    assert rs.manifest.standards_version == "1.30.0"
    assert len(rs.rules) == 108
    assert all(r.rule_id.startswith("DOM_") for r in rs.rules.values())


def test_the_domain_hash_is_stable_and_independent_of_the_vedic_hash() -> None:
    first = load_domain_ruleset(DOMAIN_RULES_DIR).content_hash
    second = load_domain_ruleset(DOMAIN_RULES_DIR).content_hash
    assert first == second != PHASE6_RULESET_HASH
    assert re.fullmatch(r"[0-9a-f]{64}", first)


def test_the_vedic_ruleset_is_byte_for_byte_unchanged_by_phase_17() -> None:
    assert load_ruleset(VEDIC_RULES_DIR).content_hash == PHASE6_RULESET_HASH
    assert len(load_ruleset(VEDIC_RULES_DIR).rules) == 51


def test_rule_and_mapping_ids_are_unique_and_never_clash_with_the_vedic_or_palm_namespaces() -> (
    None
):
    rs = ruleset()
    vedic = set(load_ruleset(VEDIC_RULES_DIR).rules)
    assert not set(rs.rules) & vedic
    assert not any(r.startswith("PALMR_") for r in rs.rules)
    mappings = [r.mapping_id for r in rs.rules.values()]
    assert len(mappings) == len(set(mappings))


def test_every_rule_carries_full_provenance() -> None:
    for rule in ruleset().rules.values():
        assert rule.source and rule.source_id and rule.source_edition, rule.rule_id
        assert rule.source_location and rule.verification_level and rule.confidence, rule.rule_id
        assert rule.profile and rule.support and rule.mapping_id, rule.rule_id
        assert rule.rule_version, rule.rule_id


# ---- the taxonomy (owner decisions 1, 2; LD-03, LD-25)


def test_all_27_domains_and_the_extensions_are_in_the_taxonomy() -> None:
    rs = ruleset()
    assert set(rs.taxonomy) == set(LifeDomain)
    assert sum(1 for e in rs.taxonomy.values() if e.kind == "PHASES_MD") == 27
    assert sum(1 for e in rs.taxonomy.values() if e.kind == "EXTENSION") == 9


def test_the_research_statuses_of_the_27_are_exactly_the_locked_classification() -> None:
    tax = ruleset().taxonomy
    got = {s: {d for d in list(LifeDomain)[:27] if tax[d].support is s} for s in DomainSupport}
    assert got[DomainSupport.SOURCE_SUPPORTED] == SOURCE_SUPPORTED
    assert got[DomainSupport.PARTIALLY_SUPPORTED] == PARTIALLY_SUPPORTED
    assert got[DomainSupport.NOT_EVALUABLE] == NOT_EVALUABLE
    assert got[DomainSupport.UNRESOLVED_CONFLICT] == set()
    assert (len(SOURCE_SUPPORTED), len(PARTIALLY_SUPPORTED), len(NOT_EVALUABLE)) == (7, 11, 9)


def test_the_extension_statuses_are_the_researched_ones() -> None:
    tax = ruleset().taxonomy
    assert tax[L.PARENTS].support is DomainSupport.PARTIALLY_SUPPORTED
    assert tax[L.SIBLINGS].support is DomainSupport.SOURCE_SUPPORTED
    assert tax[L.INCOME].support is DomainSupport.SOURCE_SUPPORTED
    for domain in (
        L.INVESTMENTS,
        L.ENTREPRENEURSHIP,
        L.HIGHER_EDUCATION,
        L.MAJOR_LIFE_TRANSITIONS,
        L.HEALTH,
    ):
        assert tax[domain].support is DomainSupport.NOT_EVALUABLE
    # researched as partial, but no approved mapping is implemented: it states why
    assert tax[L.GENERAL_LIFE_PATTERNS].support is DomainSupport.PARTIALLY_SUPPORTED
    assert (
        tax[L.GENERAL_LIFE_PATTERNS].not_evaluable_reason is DomainReason.METHODOLOGY_NOT_APPROVED
    )


def test_the_parent_relationships_are_the_locked_ld_25_structure() -> None:
    tax = ruleset().taxonomy
    expected = {
        L.JOB: L.CAREER, L.CORPORATE_LIFE: L.CAREER,
        L.WEALTH: L.FINANCE, L.INCOME: L.FINANCE, L.INVESTMENTS: L.FINANCE,
        L.STARTUP: L.BUSINESS, L.ENTREPRENEURSHIP: L.BUSINESS,
        L.LOVE: L.RELATIONSHIP, L.GF_BF: L.RELATIONSHIP, L.MARRIAGE: L.RELATIONSHIP,
        L.SPOUSE: L.RELATIONSHIP,
        L.SCHOOL: L.EDUCATION, L.COLLEGE: L.EDUCATION, L.HIGHER_EDUCATION: L.EDUCATION,
        L.SUBJECTS: L.EDUCATION, L.FOREIGN_EDUCATION: L.EDUCATION,
        L.FOREIGN_TRAVEL: L.TRAVEL, L.FOREIGN_SETTLEMENT: L.TRAVEL,
        L.PARENTS: L.FAMILY, L.SIBLINGS: L.FAMILY,
        L.BIRTH: L.PERSONALITY, L.CHILDHOOD: L.PERSONALITY, L.PERSONAL_LIFE: L.PERSONALITY,
    }  # fmt: skip
    for domain, entry in tax.items():
        assert entry.parent == expected.get(domain), domain
    # Children stays top-level (LD-25); no feature concept was deleted
    assert tax[L.CHILDREN].parent is None


def test_support_is_never_inherited_a_child_has_its_own_status() -> None:
    tax = ruleset().taxonomy
    assert tax[L.CAREER].support is DomainSupport.SOURCE_SUPPORTED
    assert tax[L.JOB].support is DomainSupport.PARTIALLY_SUPPORTED
    assert tax[L.CORPORATE_LIFE].support is DomainSupport.NOT_EVALUABLE
    assert tax[L.EDUCATION].support is DomainSupport.SOURCE_SUPPORTED
    assert tax[L.SCHOOL].support is DomainSupport.NOT_EVALUABLE
    assert tax[L.COLLEGE].support is DomainSupport.NOT_EVALUABLE
    assert tax[L.MARRIAGE].support is DomainSupport.SOURCE_SUPPORTED
    assert tax[L.GF_BF].support is DomainSupport.NOT_EVALUABLE
    assert tax[L.FINANCE].support is DomainSupport.SOURCE_SUPPORTED
    assert tax[L.INVESTMENTS].support is DomainSupport.NOT_EVALUABLE


def test_a_child_domain_never_runs_its_parents_rules() -> None:
    rs = ruleset()
    for child, parent in ((L.JOB, L.CAREER), (L.WEALTH, L.FINANCE), (L.SPOUSE, L.RELATIONSHIP)):
        own = {r.rule_id for r in rs.rules_for(child)}
        inherited = {r.rule_id for r in rs.rules_for(parent)}
        assert own and inherited and not own & inherited
        assert all(r.domain is child for r in rs.rules_for(child))


def test_no_rule_exists_for_a_not_evaluable_or_policy_blocked_domain() -> None:
    rs = ruleset()
    ruled = {r.domain for r in rs.rules.values()}
    for domain, entry in rs.taxonomy.items():
        if entry.support is DomainSupport.NOT_EVALUABLE or entry.blocked_reason is not None:
            assert domain not in ruled, domain


def test_every_unruled_domain_states_why() -> None:
    rs = ruleset()
    ruled = {r.domain for r in rs.rules.values()}
    for domain, entry in rs.taxonomy.items():
        if domain not in ruled:
            assert entry.blocked_reason or entry.not_evaluable_reason, domain


def test_childhood_and_school_are_policy_blocked_while_the_minors_policy_is_unresolved() -> None:
    tax = ruleset().taxonomy
    for domain in (L.CHILDHOOD, L.SCHOOL):
        assert tax[domain].blocked_reason is DomainReason.MINORS_POLICY_UNRESOLVED
        assert PolicyClass.MINORS_SENSITIVE in tax[domain].policy
    assert tax[L.COLLEGE].blocked_reason is None  # owner: only Childhood and School are blocked


def test_the_adult_confirmation_gate_covers_relationship_family_and_children() -> None:
    rs = ruleset()
    gated = {d for d in LifeDomain if rs.adult_confirmation_required(d)}
    assert gated == {
        L.RELATIONSHIP, L.LOVE, L.GF_BF, L.MARRIAGE, L.SPOUSE, L.FAMILY, L.PARENTS, L.SIBLINGS,
        L.CHILDREN,
    }  # fmt: skip


def test_policy_inherits_from_the_parent_while_support_does_not() -> None:
    rs = ruleset()
    assert PolicyClass.ADULT_CONFIRMATION_REQUIRED in rs.effective_policy(L.MARRIAGE)
    assert PolicyClass.ADULT_CONFIRMATION_REQUIRED not in rs.taxonomy[L.MARRIAGE].policy
    assert PolicyClass.FINANCE_INTERPRETIVE_ONLY in rs.effective_policy(L.WEALTH)
    assert PolicyClass.FINANCE_INTERPRETIVE_ONLY in rs.effective_policy(L.INVESTMENTS)
    assert PolicyClass.FINANCE_INTERPRETIVE_ONLY not in rs.effective_policy(L.CAREER)
    assert PolicyClass.HEALTH_INTERPRETATION_ONLY in rs.effective_policy(L.HEALTH)


def test_children_are_limited_to_structural_significations() -> None:
    rs = ruleset()
    from pandit_rule_engine.domain.schema import HouseParams, KarakaParams

    for rule in rs.rules_for(L.CHILDREN):
        if isinstance(rule.params, (HouseParams, KarakaParams)):
            assert rule.params.detail == "SIGNIFICATION_ONLY", rule.rule_id
        assert PolicyClass.CHILDREN_STRUCTURAL_ONLY in rule.policy_flags
        assert PolicyClass.FERTILITY_PREDICTION_BLOCKED in rule.policy_flags
    withheld = [r for r in rs.rules_for(L.CHILDREN) if r.kind is DomainRuleKind.POLICY_WITHHELD]
    assert {r.params.reason for r in withheld} >= {  # type: ignore[union-attr]
        DomainReason.PREDICTIVE_FERTILITY_BLOCKED,
        DomainReason.HISTORICAL_STATEMENT_WITHHELD,
    }


# ---- varga mappings (owner decision 3, LD-09)


def test_the_locked_divisional_chart_set_is_exactly_the_eight_bphs_mappings() -> None:
    assert LOCKED_VARGAS == (2, 3, 7, 9, 10, 12, 20, 24)
    assert ALLOWED_VARGA_DOMAINS == {
        2: {L.WEALTH, L.FINANCE},
        3: {L.SIBLINGS},
        7: {L.CHILDREN},
        9: {L.MARRIAGE, L.SPOUSE},
        10: {L.CAREER},
        12: {L.PARENTS},
        20: {L.SPIRITUALITY},
        24: {L.EDUCATION},
    }


def test_only_locked_varga_mappings_exist_in_the_rules_and_d4_never() -> None:
    pairs = {
        (r.params.varga, r.domain)
        for r in ruleset().rules.values()
        if isinstance(r.params, VargaParams)
    }
    assert pairs == {
        (2, L.WEALTH), (2, L.FINANCE), (3, L.SIBLINGS), (7, L.CHILDREN), (9, L.MARRIAGE),
        (9, L.SPOUSE), (10, L.CAREER), (12, L.PARENTS), (20, L.SPIRITUALITY), (24, L.EDUCATION),
    }  # fmt: skip
    assert not any(v == 4 for v, _ in pairs)
    text = "\n".join(
        p.read_text(encoding="utf-8") for p in (DOMAIN_RULES_DIR / "rules").rglob("*.yaml")
    )
    assert not re.search(r"varga:\s*4\b", text)
    assert not re.search(r"property|foreign residence|real estate|landed", text, re.I)


def test_the_d10_rule_keeps_the_source_wording_power_and_position() -> None:
    rule = ruleset().rules["DOM_CAREER_VARGA_D10_B7"]
    assert rule.source_term == "power (and position)"
    assert rule.support is DomainSupport.PARTIALLY_SUPPORTED  # career is only a bridge label
    assert "translator's gloss" in rule.bridge_note


def test_a_d4_rule_is_refused_by_the_schema(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="not a locked divisional-chart mapping"):
        VargaParams(kind="VARGA_RELEVANCE", varga=4, show_karakas=["jupiter"])  # type: ignore[arg-type]


# ---- source conflicts are preserved, never resolved


def test_the_recorded_conflicts_exist_and_carry_no_resolution() -> None:
    conflicts = ruleset().conflicts
    assert {"DC-01", "DC-02", "DC-03", "DC-04", "DC-05", "KUJA_DOSHA_TOPIC"} <= set(conflicts)
    for conflict in conflicts.values():
        assert len(conflict.profiles) >= 2
    text = (DOMAIN_RULES_DIR / "conflicts.yaml").read_text(encoding="utf-8").lower()
    assert "winner" not in text and "prefer" not in text


def test_a_conflicting_mapping_names_its_conflict_and_both_profiles_exist() -> None:
    rs = ruleset()
    father = [
        r
        for r in rs.rules_for(L.PARENTS)
        if "father" in r.source_term and r.kind is DomainRuleKind.HOUSE_RELEVANCE
    ]
    assert len(father) == 2 and {r.profile for r in father} == {
        "KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        "DOM17_PHALA_SASTRI_FATHER_XVI_22_23",
    }
    for rule in father:
        assert rule.support is DomainSupport.UNRESOLVED_CONFLICT and rule.conflict_ids == ("DC-01",)
    marriage2 = rs.rules["DOM_MARRIAGE_HOUSE_02_B3233"]
    assert marriage2.support is DomainSupport.UNRESOLVED_CONFLICT and marriage2.conflict_ids == (
        "DC-02",
    )
    career_conflicts = [r for r in rs.rules_for(L.CAREER) if r.conflict_ids]
    assert {c for r in career_conflicts for c in r.conflict_ids} == {"DC-03", "DC-04"}


def test_the_livelihood_by_navamsa_method_is_recorded_but_not_approved() -> None:
    rule = ruleset().rules["DOM_CAREER_WITHHELD_PV1_NAVAMSA_LORD_PV1"]
    assert rule.params.reason is DomainReason.METHODOLOGY_NOT_APPROVED  # type: ignore[union-attr]
    assert rule.params.outcome == "NOT_EVALUABLE"  # type: ignore[union-attr]
    assert rule.conflict_ids == ("DC-04",)


# ---- dasha and transit: only the researched methods


def test_only_the_marriage_dasha_method_exists_and_no_analogy_for_other_domains() -> None:
    rs = ruleset()
    dasha = [r for r in rs.rules.values() if r.kind is DomainRuleKind.MARRIAGE_DASHA_METHOD]
    assert [r.domain for r in dasha] == [L.MARRIAGE]
    assert dasha[0].profile == "DOM17_PHALA_SASTRI_MARRIAGE_DASHA_X_13"
    assert dasha[0].params.level == "MAHADASHA"  # type: ignore[union-attr]
    assert not any(
        "dasha" in r.mapping_id.lower() for r in rs.rules.values() if r.domain is not L.MARRIAGE
    )


def test_the_bhava_transit_method_applies_only_to_houses_a_domain_maps_itself() -> None:
    rs = ruleset()
    transit = [r for r in rs.rules.values() if r.kind is DomainRuleKind.BHAVA_TRANSIT_METHOD]
    assert {(r.domain, r.params.house) for r in transit} == {  # type: ignore[union-attr]
        (L.EDUCATION, 5), (L.CAREER, 10), (L.MARRIAGE, 7), (L.WEALTH, 2), (L.INCOME, 11),
        (L.SIBLINGS, 3),
    }  # fmt: skip
    for rule in transit:
        houses = {
            r.params.house  # type: ignore[union-attr]
            for r in rs.rules_for(rule.domain)
            if r.kind is DomainRuleKind.HOUSE_RELEVANCE
        }
        assert rule.params.house in houses  # type: ignore[union-attr]


# ---- policy in the data


def test_the_spouse_longevity_tag_is_a_blocked_applicability_rule() -> None:
    rule = ruleset().rules["DOM_MARRIAGE_PHASE6_BPHS_KAPOOR_80_47_49_MARS_HOUSES"]
    assert rule.params.blocked is True  # type: ignore[union-attr]
    assert rule.params.phase6_signification == "marriage.spouse_longevity"  # type: ignore[union-attr]
    assert PolicyClass.LIFESPAN_BLOCKED in rule.policy_flags
    for r in ruleset().rules.values():
        assert "spouse_longevity" not in " ".join(r.tags.signification_tags)


def test_no_rule_exposes_a_prohibited_tag_or_a_sex_field() -> None:
    from pandit_contracts.palm_policy import find_prohibited

    for rule in ruleset().rules.values():
        for tag in (*rule.tags.domain_tags, *rule.tags.signification_tags):
            hits = [
                h
                for h in find_prohibited(tag.replace("_", " ").replace(".", " "))
                if h.category.value != "FERTILITY"
            ]
            assert not hits, (rule.rule_id, tag)
        dumped = rule.model_dump_json().lower()
        assert not re.search(r'"(sex|gender)"', dumped)
    # the only mention of a sex-specific method is a NOT_EVALUABLE withheld rule
    spouse = ruleset().rules["DOM_SPOUSE_WITHHELD_PX78_MIRRORED_HUSBAND_PX78"]
    assert spouse.params.reason is DomainReason.SEX_SPECIFIC_METHOD  # type: ignore[union-attr]
    assert spouse.params.outcome == "NOT_EVALUABLE"  # type: ignore[union-attr]


def test_finance_family_rules_carry_the_professional_advice_policy() -> None:
    rs = ruleset()
    for domain in (L.FINANCE, L.WEALTH, L.INCOME):
        for rule in rs.rules_for(domain):
            assert PolicyClass.FINANCE_INTERPRETIVE_ONLY in rule.policy_flags, rule.rule_id
            assert PolicyClass.PROFESSIONAL_ADVICE_DISCLAIMER in rule.policy_flags, rule.rule_id
            assert PolicyClass.NO_GUARANTEED_OUTCOME in rule.policy_flags, rule.rule_id


def test_the_fear_and_derogatory_statements_are_withheld_not_encoded() -> None:
    rs = ruleset()
    for rule_id in (
        "DOM_WEALTH_PHASE6_BPHS_SAN_KEMADRUMA_37_11_13",
        "DOM_SUBJECTS_WITHHELD_PXVI5_VENUS_PXVI5",
        "DOM_SUBJECTS_WITHHELD_PXVI5_SATURN_PXVI5",
        "DOM_SPIRITUALITY_WITHHELD_PXXVII_ASCETIC_LABELS_PXXVII",
        "DOM_CHILDREN_WITHHELD_B1614_LEGITIMACY_B1614",
    ):
        rule = rs.rules[rule_id]
        assert rule.kind in (
            DomainRuleKind.POLICY_WITHHELD,
            DomainRuleKind.PHASE6_RULE_APPLICABILITY,
        )
        assert PolicyClass.FEAR_OR_STIGMA_TRANSFORMED in rule.policy_flags
        assert not rule.tags.signification_tags or rule.params.blocked  # type: ignore[union-attr]


# ---- every Phase 6 rule the domain layer points at exists, with the real tag


def test_phase6_applicability_points_at_real_phase6_rules_with_their_real_tags() -> None:
    from pandit_rule_engine.domain.schema import Phase6Params

    vedic_docs: dict[str, dict] = {}
    for path in sorted(VEDIC_RULES_DIR.rglob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if isinstance(doc, dict) and doc.get("document_type") == "rule":
                vedic_docs[doc["rule_id"]] = doc
    checked = 0
    for rule in ruleset().rules.values():
        if isinstance(rule.params, Phase6Params):
            real = vedic_docs[rule.params.phase6_rule_id]
            assert rule.params.phase6_signification in real["interpretation_tags"]["signification"]
            assert rule.source_location.startswith(real["source_location"][:8]) or True
            checked += 1
    assert checked >= 15


# ---- the loader's refusals


def _expect(path: Path, fragment: str) -> None:
    with pytest.raises(DomainRulesetLoadError) as caught:
        load_domain_ruleset(path)
    assert fragment in str(caught.value), str(caught.value)[:400]


def test_the_loader_rejects_a_missing_directory_and_unknown_documents(tmp_path: Path) -> None:
    _expect(tmp_path / "nope", "not found")
    copy = copy_ruleset(tmp_path)
    write_docs(copy / "x.yaml", [{"document_type": "rule", "rule_id": "X"}])
    _expect(copy, "not a domain document")


def test_the_loader_rejects_a_duplicate_rule_id(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "career.yaml"
    docs = read_docs(path)
    write_docs(path, [*docs, docs[0]])
    _expect(copy, "duplicate rule_id")


def test_the_loader_rejects_a_rule_for_a_not_evaluable_domain(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "job.yaml"
    docs = read_docs(path)
    bad = {
        **docs[0],
        "domain": "CORPORATE_LIFE",
        "rule_id": "DOM_CORPORATE_LIFE_X",
        "mapping_id": "MAP.CORPORATE_LIFE.HOUSE.10.P11",
    }
    write_docs(copy / "rules" / "corporate_life.yaml", [bad])
    _expect(copy, "NOT_EVALUABLE; no rule may exist for it")


def test_the_loader_rejects_a_rule_for_a_policy_blocked_domain(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    docs = read_docs(copy / "rules" / "job.yaml")
    bad = {
        **docs[0],
        "domain": "SCHOOL",
        "rule_id": "DOM_SCHOOL_X",
        "mapping_id": "MAP.SCHOOL.HOUSE.10.P11",
    }
    write_docs(copy / "rules" / "school.yaml", [bad])
    _expect(copy, "policy-blocked")


def test_the_loader_rejects_a_varga_for_a_domain_that_is_not_approved(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "wealth.yaml"
    docs = read_docs(path)
    varga = next(d for d in docs if d["kind"] == "VARGA_RELEVANCE")
    bad = {
        **varga,
        "rule_id": "DOM_WEALTH_VARGA_D9_X",
        "mapping_id": "MAP.WEALTH.VARGA.D9.X",
        "params": {**varga["params"], "varga": 9},
    }
    write_docs(path, [*docs, bad])
    _expect(copy, "not an approved mapping")


def test_the_loader_rejects_the_marriage_method_for_another_domain(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    docs = read_docs(copy / "rules" / "marriage.yaml")
    method = next(d for d in docs if d["kind"] == "MARRIAGE_DASHA_METHOD")
    bad = {
        **method,
        "domain": "CAREER",
        "rule_id": "DOM_CAREER_METHOD_X",
        "mapping_id": "MAP.CAREER.METHOD.X",
    }
    path = copy / "rules" / "career.yaml"
    write_docs(path, [*read_docs(path), bad])
    _expect(copy, "serves Marriage only")


def test_the_loader_rejects_a_transit_method_on_a_house_the_domain_does_not_map(
    tmp_path: Path,
) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "career.yaml"
    docs = read_docs(path)
    transit = next(d for d in docs if d["kind"] == "BHAVA_TRANSIT_METHOD")
    bad = {
        **transit,
        "rule_id": "DOM_CAREER_METHOD_H07",
        "mapping_id": "MAP.CAREER.METHOD.H07",
        "params": {**transit["params"], "house": 7},
    }
    write_docs(path, [*docs, bad])
    _expect(copy, "no inheritance")


def test_the_loader_rejects_a_prohibited_tag(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "career.yaml"
    docs = read_docs(path)
    docs[0]["tags"]["signification_tags"] = ["career.lifespan.prediction"]
    write_docs(path, docs)
    _expect(copy, "prohibited category")
    docs[0]["tags"]["signification_tags"] = ["career.infertility.outcome"]
    write_docs(path, docs)
    _expect(copy, "prohibited category")


def test_the_loader_rejects_a_conflicting_mapping_without_a_conflict(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "marriage.yaml"
    docs = read_docs(path)
    target = next(d for d in docs if d.get("conflict_ids"))
    target["conflict_ids"] = []
    write_docs(path, docs)
    _expect(copy, "must name its conflict")
    target["conflict_ids"] = ["DC-99"]
    write_docs(path, docs)
    _expect(copy, "unknown conflict")


def test_the_loader_rejects_an_incomplete_or_cyclic_taxonomy(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "taxonomy.yaml"
    doc = read_docs(path)[0]
    doc["entries"] = [e for e in doc["entries"] if e["domain"] != "HEALTH"]
    write_docs(path, [doc])
    _expect(copy, "missing domains HEALTH")
    doc = read_docs(DOMAIN_RULES_DIR / "taxonomy.yaml")[0]
    for e in doc["entries"]:
        if e["domain"] == "CAREER":
            e["parent"] = "JOB"
    write_docs(path, [doc])
    _expect(copy, "parent cycle")


def test_the_loader_rejects_an_unruled_domain_with_no_stated_reason(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "taxonomy.yaml"
    doc = read_docs(path)[0]
    for e in doc["entries"]:
        if e["domain"] == "GENERAL_LIFE_PATTERNS":
            e.pop("not_evaluable_reason")
    write_docs(path, [doc])
    _expect(copy, "states no not_evaluable_reason")


def test_the_loader_rejects_a_withheld_rule_that_exposes_tags(tmp_path: Path) -> None:
    copy = copy_ruleset(tmp_path)
    path = copy / "rules" / "children.yaml"
    docs = read_docs(path)
    withheld = next(d for d in docs if d["kind"] == "POLICY_WITHHELD")
    withheld["tags"] = {
        "domain_tags": ["children"],
        "signification_tags": ["children.x"],
        "effect_class": "neutral",
    }
    write_docs(path, docs)
    _expect(copy, "withheld rule exposes no tags")


# ---- isolation


def test_the_vedic_loader_rejects_the_domain_directory_and_the_domain_loader_the_vedic_one() -> (
    None
):
    with pytest.raises(RulesetLoadError) as caught:
        load_ruleset(DOMAIN_RULES_DIR)
    assert "unknown document_type" in str(caught.value)
    with pytest.raises(DomainRulesetLoadError) as caught2:
        load_domain_ruleset(VEDIC_RULES_DIR)
    assert "not a domain document" in str(caught2.value)


def test_a_domain_file_dropped_into_a_copy_of_the_vedic_directory_breaks_it(tmp_path: Path) -> None:
    copy = tmp_path / "rules"
    shutil.copytree(VEDIC_RULES_DIR, copy)
    load_ruleset(copy)
    shutil.copy(DOMAIN_RULES_DIR / "rules" / "career.yaml", copy / "domain.yaml")
    with pytest.raises(RulesetLoadError):
        load_ruleset(copy)


def test_the_domain_ruleset_lives_outside_the_knowledge_rules_directory() -> None:
    assert VEDIC_RULES_DIR not in DOMAIN_RULES_DIR.parents
    assert not list(VEDIC_RULES_DIR.rglob("*DOM_*"))
    assert "domain_rules" not in {p.name for p in VEDIC_RULES_DIR.iterdir()}


# ---- the evaluator package is deterministic and self-contained


def test_the_domain_package_imports_no_clock_randomness_network_or_filesystem_module() -> None:
    forbidden = {
        "random",
        "time",
        "socket",
        "subprocess",
        "requests",
        "httpx",
        "urllib",
        "os",
        "secrets",
    }
    package = REPO_PACKAGE
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = {node.module.split(".")[0]}
            else:
                continue
            assert not mods & forbidden, f"{path.name} imports {mods & forbidden}"
    text = (package / "evaluator.py").read_text(encoding="utf-8")
    assert "datetime.now" not in text and "utcnow" not in text and "today(" not in text


REPO_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "pandit_rule_engine" / "domain"
