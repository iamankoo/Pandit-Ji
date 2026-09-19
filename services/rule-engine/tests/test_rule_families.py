"""Phase 6: ruleset-wide invariants and rule-family behaviour."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from pandit_rule_engine.engine import RuleEngine
from pandit_rule_engine.loader import Ruleset, load_ruleset
from pandit_rule_engine.results import status_label
from pandit_rule_engine.vocab import Reason, Status
from tests.chart_builder import kundli_dict
from tests.golden_cases import SAMPLE_A
from tests.helpers import rule_doc, rules_dir

EXPECTED_PROFILES = {
    "BPHS_KAPOOR_PMP_75_1_2_RUCHAKA",
    "BPHS_KAPOOR_PMP_75_1_2_BHADRA",
    "BPHS_KAPOOR_PMP_75_1_2_HAMSA",
    "BPHS_KAPOOR_PMP_75_1_2_MALAVYA",
    "BPHS_KAPOOR_PMP_75_1_2_SHASHA",
    "BPHS_SAN_SUNAPHA_37_7_10",
    "BPHS_SAN_ANAPHA_37_7_10",
    "BPHS_SAN_DURADHARA_37_7_10",
    "BPHS_SAN_VESI_38_1",
    "BPHS_SAN_VOSI_38_1",
    "BPHS_SAN_UBHAYACHARI_38_1",
    "BPHS_SAN_ADHI_MOON_37_5",
    "BPHS_SAN_LAGNADHI_36_37",
    "BPHS_SAN_DHANA_MOON_37_6",
    "BPHS_SAN_KEMADRUMA_37_11_13",
    "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5",
    "PHALADEEPIKA_SASTRI_KESARI_6_14",
    "BPHS_SAN_GAJAKESARI_36_3_4",
    "BPHS_KAPOOR_80_47_49_MARS_HOUSES",
    "JP_KUJA_DOSHA",
}
NABHASA_NAMES = {
    "RAJJU", "MUSALA", "NALA", "MAALA", "SARPA", "GADA", "SAKATA", "VIHAGA", "SRINGATAKA",
    "HALA", "VAJRA", "YAVA", "KAMALA", "VAPI", "YUPA", "SARA", "SAKTHI", "DANDA", "NAUKA",
    "KOOTA", "CHATRA", "CHAPA", "CHAKRA", "SAMUDRA", "GOLA", "YUGA", "SOOLA", "KEDARA",
    "PAASA", "DAAMA", "VEENA",
}  # fmt: skip


@pytest.fixture(scope="module")
def ruleset() -> Ruleset:
    return load_ruleset(rules_dir())


@pytest.fixture(scope="module")
def engine(ruleset: Ruleset) -> RuleEngine:
    return RuleEngine(ruleset)


# --------------------------------------------------------------------------
# The shipped ruleset
# --------------------------------------------------------------------------


def test_ruleset_contains_exactly_the_approved_first_tranche(ruleset: Ruleset) -> None:
    ids = set(ruleset.rules)
    nabhasa = {rid for rid in ids if rid.startswith("BPHS_SAN_NABHASA_35_")}
    assert {rid.removeprefix("BPHS_SAN_NABHASA_35_") for rid in nabhasa} == NABHASA_NAMES
    assert len(nabhasa) == 31  # 3 Asraya + 2 Dala + 19 defined Akriti + 7 Sankhya
    assert ids - nabhasa == EXPECTED_PROFILES
    assert len(ruleset.rules) == 51
    assert ruleset.manifest.standards_version == "1.4.0"


def test_out_of_scope_rules_are_absent(ruleset: Ruleset) -> None:
    joined = " ".join(ruleset.rules).upper()
    for forbidden in ("ARDHACHANDRA", "KAAL", "KALA_SARP", "KALSARP", "GULIKA", "MANDI",
                      "PRANAPADA", "UPAGRAHA", "JAIMINI", "KARAKA", "LONGEVITY", "D27",
                      "SHADBALA", "SADE_SATI", "NADI", "BHAKOOT"):  # fmt: skip
        assert forbidden not in joined, forbidden


def test_every_rule_has_complete_provenance_and_readings(ruleset: Ruleset) -> None:
    for rule in ruleset.rules.values():
        assert rule.source and rule.source_id and rule.source_edition, rule.rule_id
        assert rule.source_location and rule.source_version, rule.rule_id
        assert rule.translator is not None, rule.rule_id
        assert rule.standards_version == "1.4.0"
        assert rule.status == "active"
        assert rule.readings and all(r.reading_id for r in rule.readings)
        assert rule.interpretation_tags.effect_class in {
            "supportive", "challenging", "mixed", "neutral", "context_dependent"
        }  # fmt: skip
        assert rule.verification_level != "SANSKRIT-LEVEL", rule.rule_id


def test_no_rule_claims_sanskrit_level_verification(ruleset: Ruleset) -> None:
    levels = {rule.verification_level for rule in ruleset.rules.values()}
    assert "SANSKRIT-LEVEL" not in levels
    assert "SANSKRIT-LEVEL" not in {t.verification_level for t in ruleset.tables.values()}


def test_source_profiles_are_kept_apart(ruleset: Ruleset) -> None:
    gaja = {r.rule_id for r in ruleset.rules.values() if r.conflict_group == "GAJAKESARI_TOPIC"}
    assert gaja == {"BPHS_SAN_GAJAKESARI_36_3_4", "PHALADEEPIKA_SASTRI_KESARI_6_14"}
    kem = {r.rule_id for r in ruleset.rules.values() if r.conflict_group == "KEMADRUMA_TOPIC"}
    assert kem == {"BPHS_SAN_KEMADRUMA_37_11_13", "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5"}
    kuja = {r.rule_id for r in ruleset.rules.values() if r.conflict_group == "KUJA_DOSHA_TOPIC"}
    assert kuja == {"BPHS_KAPOOR_80_47_49_MARS_HOUSES", "JP_KUJA_DOSHA"}
    canonical = ruleset.rules["BPHS_SAN_GAJAKESARI_36_3_4"]
    assert canonical.source_id == "BPHS_SANTHANAM_1984"
    assert ruleset.rules["JP_KUJA_DOSHA"].source_id == "JATAKA_PARIJATA_CHAUKHAMBHA"
    assert ruleset.rules["PHALADEEPIKA_SASTRI_KESARI_6_14"].source_id == "PHALADEEPIKA_SASTRI"


def test_mangal_bphs_profile_keeps_both_readings_and_the_partner_dependency(
    ruleset: Ruleset,
) -> None:
    rule = ruleset.rules["BPHS_KAPOOR_80_47_49_MARS_HOUSES"]
    assert [r.reading_id for r in rule.readings] == [
        "TRANSLATION_12_4_7_8",
        "SANSKRIT_LAGNE_12_4_7_8",
    ]
    assert [r.basis for r in rule.readings] == ["translation", "sanskrit_reading"]
    dependency = rule.dependencies[0]
    assert dependency.reason is Reason.REQUIRES_PARTNER_CHART
    assert dependency.owner_phase == 11
    assert rule.applicability.gender == "effect_label_only"
    assert rule.category == "dosha"


def test_gajakesari_canonical_profile_has_the_four_documented_readings(ruleset: Ruleset) -> None:
    rule = ruleset.rules["BPHS_SAN_GAJAKESARI_36_3_4"]
    assert {r.reading_id for r in rule.readings} == {
        "EXCLUSIONS_ON_JUPITER_ENEMY_SIGN_NATURAL",
        "EXCLUSIONS_ON_JUPITER_ENEMY_SIGN_COMPOUND",
        "EXCLUSIONS_ON_BENEFIC_ENEMY_SIGN_NATURAL",
        "EXCLUSIONS_ON_BENEFIC_ENEMY_SIGN_COMPOUND",
    }


def test_sankhya_suppression_refers_only_to_the_defined_earlier_yogas(ruleset: Ruleset) -> None:
    sankhya = {"GOLA", "YUGA", "SOOLA", "KEDARA", "PAASA", "DAAMA", "VEENA"}
    rule = ruleset.rules["BPHS_SAN_NABHASA_35_GOLA"]
    text = yaml.safe_dump(rule.cancellations[0].when.model_dump(mode="json", by_alias=True))
    referenced = {
        line.split("BPHS_SAN_NABHASA_35_")[1].strip()
        for line in text.splitlines()
        if "NABHASA_35_" in line
    }
    assert len(referenced) == 24
    assert not referenced & sankhya
    assert rule.dependencies[0].reason is Reason.CONDITION_ABSENT_IN_SOURCE


# --------------------------------------------------------------------------
# Behaviour through the engine
# --------------------------------------------------------------------------


def test_conflicting_traditions_are_both_retained_in_the_bundle(engine: RuleEngine) -> None:
    kundli = kundli_dict(
        "aries",
        {
            "sun": ("aries", 10.0), "moon": ("gemini", 10.0), "mars": ("leo", 10.0),
            "mercury": ("virgo", 10.0), "jupiter": ("scorpio", 10.0),
            "venus": ("sagittarius", 10.0), "saturn": ("aquarius", 10.0),
            "rahu": ("pisces", 10.0), "ketu": ("virgo", 20.0),
        },
    )  # fmt: skip
    bundle = engine.evaluate_kundli(kundli)
    group = next(g for g in bundle.conflicts if g.group_id == "KEMADRUMA_TOPIC")
    assert set(group.rule_ids) == {
        "BPHS_SAN_KEMADRUMA_37_11_13",
        "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5",
    }
    assert group.statuses["BPHS_SAN_KEMADRUMA_37_11_13"] == "NOT_EVALUABLE"
    assert group.statuses["PHALADEEPIKA_SASTRI_KEMADRUMA_6_5"] == "CANCELLED"


def test_priority_never_changes_a_result(ruleset: Ruleset, tmp_path: Path) -> None:
    baseline = RuleEngine(ruleset).evaluate_kundli(kundli_dict("aries", SAMPLE_A))
    copy = tmp_path / "rules"
    shutil.copytree(rules_dir(), copy)
    for path in copy.rglob("*.yaml"):
        documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        for document in documents:
            if document.get("document_type") == "rule":
                document["priority"] = 999 - int(document["priority"])
        path.write_text(yaml.safe_dump_all(documents, sort_keys=False), encoding="utf-8")
    shuffled = RuleEngine.from_directory(copy).evaluate_kundli(kundli_dict("aries", SAMPLE_A))

    def outcomes(bundle: Any) -> dict[str, tuple[str, str | None, tuple[str, ...]]]:
        return {
            r.rule_id: (
                r.status.value,
                r.reason.value if r.reason else None,
                tuple(f"{x.reading_id}:{x.status.value}" for x in r.readings),
            )
            for r in bundle.results
        }

    assert outcomes(baseline) == outcomes(shuffled)
    assert baseline.versions.ruleset_content_hash != shuffled.versions.ruleset_content_hash


def test_engine_is_deterministic_across_engine_instances(ruleset: Ruleset) -> None:
    kundli = kundli_dict("aries", SAMPLE_A)
    first = RuleEngine(ruleset).evaluate_kundli(kundli)
    second = RuleEngine.from_directory(rules_dir()).evaluate_kundli(kundli)
    assert first.canonical_json() == second.canonical_json()
    assert first.bundle_hash == second.bundle_hash


def test_real_ruleset_hash_is_independent_of_directory_layout(
    ruleset: Ruleset, tmp_path: Path
) -> None:
    copy = tmp_path / "moved"
    for index, path in enumerate(sorted(rules_dir().rglob("*.yaml"))):
        target = copy / f"z{index % 3}" / f"file_{index}.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
    assert load_ruleset(copy).content_hash == ruleset.content_hash


def test_dhana_records_the_structural_count(engine: RuleEngine) -> None:
    bundle = engine.evaluate_kundli(kundli_dict("aries", SAMPLE_A))
    result = next(r for r in bundle.results if r.rule_id == "BPHS_SAN_DHANA_MOON_37_6")
    assert result.status is Status.TRIGGERED
    assert "count = 1" in result.readings[0].evidence
    assert result.interpretation_tags is not None


def test_bundle_carries_derived_facts_and_both_standards_versions(engine: RuleEngine) -> None:
    bundle = engine.evaluate_kundli(kundli_dict("aries", SAMPLE_A))
    derived = bundle.derived_facts
    assert derived["natural_nature"]["moon"]["value"] == "benefic"
    assert derived["natural_nature"]["rahu"]["value"] == "malefic"
    assert derived["relationships_natural"]["sun"]["moon"] == "friend"
    assert derived["moolatrikona"]["rahu"] == "not_evaluable:requires_moolatrikona"
    assert derived["functional_nature"]["cells"]["venus"]["labels"] == ["malefic", "killer"]
    assert derived["functional_nature"]["cells"]["moon"]["status"] == "not_specified_by_source"
    assert bundle.versions.calculation_standards_version == "1.3.0"
    assert bundle.versions.rule_standards_version == "1.4.0"
    assert bundle.chart.calculation.ayanamsa == "lahiri"


# --------------------------------------------------------------------------
# Structured reasons for dependencies owned by later phases
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    [
        "requires_shadbala",
        "requires_dasha",
        "requires_partial_drishti",
        "requires_gender",
        "requires_partner_chart",
        "requires_moolatrikona",
        "node_participation_unspecified",
        "varga_scheme_conflict",
        "time_base_unspecified",
        "source_profile_not_selected",
        "scope",
        "not_specified_by_source",
        "condition_absent_in_source",
    ],
)
def test_declared_dependency_yields_its_structured_reason_instead_of_a_guess(
    engine: RuleEngine, reason: str
) -> None:
    from pandit_rule_engine.adapters import facts_from_kundli
    from pandit_rule_engine.conditions import EvalContext
    from pandit_rule_engine.derived import TableDerivedFacts
    from pandit_rule_engine.evaluator import evaluate_rule
    from pandit_rule_engine.facts import ChartFacts
    from pandit_rule_engine.schema import Rule

    facts: ChartFacts = facts_from_kundli(kundli_dict("aries", SAMPLE_A))
    dependency = {
        "dependency_id": "LATER_PHASE_INPUT",
        "kind": "later_phase_input",
        "owner_phase": 9,
        "reason": reason,
        "unresolved_effect": "not_evaluable_if_detected",
    }
    rule = Rule.model_validate(rule_doc(dependencies=[dependency]))
    context = EvalContext(facts=facts, derived=TableDerivedFacts(facts, engine.tables))
    result = evaluate_rule(context, rule)
    assert status_label(result.status, result.reason, result.detail) == (
        f"NOT_EVALUABLE({reason}:LATER_PHASE_INPUT)"
    )
    assert result.readings[0].detected_status is Status.TRIGGERED


def test_moolatrikona_atom_uses_the_separate_fact(engine: RuleEngine) -> None:
    from pandit_rule_engine.adapters import facts_from_kundli
    from pandit_rule_engine.conditions import EvalContext
    from pandit_rule_engine.derived import TableDerivedFacts
    from pandit_rule_engine.evaluator import evaluate_rule
    from pandit_rule_engine.schema import Rule

    kundli = kundli_dict("aries", SAMPLE_A | {"sun": ("leo", 10.0)})
    facts = facts_from_kundli(kundli)
    context = EvalContext(facts=facts, derived=TableDerivedFacts(facts, engine.tables))

    def run(planet: str) -> Any:
        cond = {"op": "planet_moolatrikona", "planet": planet}
        reading = [{"reading_id": "R1", "basis": "translation", "conditions": cond}]
        return evaluate_rule(context, Rule.model_validate(rule_doc(readings=reading)))

    assert run("sun").status is Status.TRIGGERED
    assert run("moon").status is Status.NOT_TRIGGERED
    assert run("rahu").reason is Reason.REQUIRES_MOOLATRIKONA


# --------------------------------------------------------------------------
# Hard boundaries of this phase
# --------------------------------------------------------------------------


def test_source_never_calls_astronomy_network_or_the_other_services() -> None:
    package = Path(__file__).resolve().parents[1] / "src" / "pandit_rule_engine"
    forbidden = (
        "pandit_astro_engine", "swisseph", "socket", "urllib", "requests", "httpx", "subprocess",
        "openai", "anthropic", "datetime.now", "time.time", "random",
    )  # fmt: skip
    for path in package.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, (path.name, token)
