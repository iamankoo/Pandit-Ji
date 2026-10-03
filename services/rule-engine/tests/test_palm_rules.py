"""The palm ruleset: loading, validation, evaluation (Phase 13; fixture rules only)."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from pandit_contracts.palm import HandSide, RuleStatus

from pandit_rule_engine.palm import (
    PalmRulesetLoadError,
    evaluate_palm_rules,
    load_palm_ruleset,
)
from tests.palm_helpers import KV, PALM_RULES_DIR, fact_set, load_coverage

COVERAGE = load_coverage()


@pytest.fixture(scope="module")
def ruleset() -> Any:
    return load_palm_ruleset(PALM_RULES_DIR, COVERAGE)


def _statuses(evaluations: Any) -> dict[str, RuleStatus]:
    return {e.rule_id: e.status for e in evaluations}


# ---- loading ---------------------------------------------------------------------------------
def test_the_fixture_ruleset_loads_with_its_own_manifest(ruleset: Any) -> None:
    assert ruleset.ruleset_id == "PANDIT_JI_PALM_WESTERN_PHASE13"
    assert ruleset.manifest.methodology_profile == "PALM_WESTERN"
    assert ruleset.manifest.scope == "FIXTURE_SET_NOT_THE_PRODUCTION_RULE_LIST"
    assert len(ruleset.rules) == 6
    assert all(rule_id.startswith("PALMR_") for rule_id in ruleset.rules)
    assert len(ruleset.content_hash) == 64


def test_the_ruleset_hash_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    one = load_palm_ruleset(PALM_RULES_DIR, COVERAGE).content_hash
    assert one == load_palm_ruleset(PALM_RULES_DIR, COVERAGE).content_hash
    copy = tmp_path / "palm_rules"
    shutil.copytree(PALM_RULES_DIR, copy)
    path = copy / "rules" / "ch_left_hand_inherited_tendencies.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("MEDIUM", "LOW"), encoding="utf-8")
    assert load_palm_ruleset(copy, COVERAGE).content_hash != one


def test_every_rule_has_exactly_one_profile_one_location_and_read_support(ruleset: Any) -> None:
    for rule in ruleset.rules.values():
        assert isinstance(rule.source_profile, str) and isinstance(rule.source_location, str)
        assert (
            COVERAGE.problems_for_rule(rule.source_profile, rule.source_location, rule.concepts)
            == ()
        )
        assert rule.framing == "TRADITIONAL_INTERPRETIVE_NOT_SCIENTIFIC"
        assert set(rule.interpretation_tags) <= set(ruleset.tags)


def test_the_recorded_conflict_is_unresolved_with_no_winner(ruleset: Any) -> None:
    conflict = ruleset.conflicts["PALM_CROSS_SOURCE.HANDS"]
    assert conflict.status == "UNRESOLVED_CONFLICT" and len(conflict.profiles) == 3
    assert not hasattr(conflict, "winner")


# ---- evaluation ------------------------------------------------------------------------------
def test_a_left_hand_triggers_each_source_profile_separately(ruleset: Any) -> None:
    evaluations = evaluate_palm_rules(ruleset, fact_set(HandSide.LEFT), KV)
    status = _statuses(evaluations)
    assert status["PALMR_CH_LEFT_HAND_INHERITED_TENDENCIES"] is RuleStatus.TRIGGERED
    assert status["PALMR_BE_LEFT_HAND_NATURAL_MAP"] is RuleStatus.TRIGGERED
    assert status["PALMR_CH_RIGHT_HAND_DEVELOPED_QUALITIES"] is RuleStatus.NOT_TRIGGERED
    assert status["PALMR_BE_RIGHT_HAND_ALTERED_MAP"] is RuleStatus.NOT_TRIGGERED
    triggered = [e for e in evaluations if e.status is RuleStatus.TRIGGERED]
    assert {e.source_profile for e in triggered} == {"PALM_CH_LINES_PART1", "PALM_BE_HANDS_359"}
    # no consensus: the two profiles keep their own tags and the conflict travels with each
    assert {e.interpretation_tags for e in triggered} == {
        ("LEFT_HAND_INHERITED_TENDENCIES",),
        ("LEFT_HAND_NATURAL_MAP",),
    }
    assert all("PALM_CROSS_SOURCE.HANDS" in e.conflict_ids for e in triggered)
    assert len(evaluations) == len(ruleset.rules)  # one evaluation per rule, none merged


def test_a_right_hand_triggers_the_right_hand_rules(ruleset: Any) -> None:
    status = _statuses(evaluate_palm_rules(ruleset, fact_set(HandSide.RIGHT), KV))
    assert status["PALMR_CH_RIGHT_HAND_DEVELOPED_QUALITIES"] is RuleStatus.TRIGGERED
    assert status["PALMR_BE_RIGHT_HAND_ALTERED_MAP"] is RuleStatus.TRIGGERED
    assert status["PALMR_CH_LEFT_HAND_INHERITED_TENDENCIES"] is RuleStatus.NOT_TRIGGERED


def test_a_triggered_evaluation_cites_its_facts_source_and_knowledge_version(ruleset: Any) -> None:
    facts = fact_set(HandSide.LEFT)
    evaluations = {e.rule_id: e for e in evaluate_palm_rules(ruleset, facts, KV)}
    ev = evaluations["PALMR_CH_LEFT_HAND_INHERITED_TENDENCIES"]
    assert ev.fact_refs == (facts.facts[0].fact_id,)
    assert ev.source_id == "SRC-CHEIRO-PALMISTRY-FOR-ALL-1916"
    assert ev.source_location == "Part I ch. XVII, Right and Left Hands"
    assert ev.knowledge_version == KV and ev.standards_version == "1.28.0"


def test_line_rules_are_not_evaluable_without_line_role_facts(ruleset: Any) -> None:
    ev = {e.rule_id: e for e in evaluate_palm_rules(ruleset, fact_set(HandSide.RIGHT), KV)}
    life = ev["PALMR_HA_LIFE_LINE_ORIGIN_UNDER_JUPITER"]
    assert life.status is RuleStatus.NOT_EVALUABLE
    assert life.reason == "REQUIRED_FACT_ABSENT:LINE_ROLE_CANDIDATE/ROLE.LIFE"
    assert life.interpretation_tags == () and life.fact_refs == ()


def test_not_evaluable_role_facts_make_the_rules_not_evaluable_never_guessed(ruleset: Any) -> None:
    facts = fact_set(HandSide.LEFT, not_evaluable_roles=True)
    ev = {e.rule_id: e for e in evaluate_palm_rules(ruleset, facts, KV)}
    for rule_id in (
        "PALMR_HA_LIFE_LINE_ORIGIN_UNDER_JUPITER",
        "PALMR_HA_FATE_LINE_ORIGIN_FROM_LIFE_LINE",
    ):
        assert ev[rule_id].status is RuleStatus.NOT_EVALUABLE
        assert "ROLE_ASSIGNMENT_UNVALIDATED" in (ev[rule_id].reason or "")


def test_validated_role_facts_trigger_the_line_rules_with_tags_only(ruleset: Any) -> None:
    facts = fact_set(HandSide.RIGHT, with_roles=True)
    ev = {e.rule_id: e for e in evaluate_palm_rules(ruleset, facts, KV)}
    life = ev["PALMR_HA_LIFE_LINE_ORIGIN_UNDER_JUPITER"]
    fate = ev["PALMR_HA_FATE_LINE_ORIGIN_FROM_LIFE_LINE"]
    assert life.status is RuleStatus.TRIGGERED and life.interpretation_tags == (
        "AMBITION_INDICATED",
    )
    assert fate.status is RuleStatus.TRIGGERED
    assert fate.interpretation_tags == ("FORTUNE_FROM_PERSONAL_MERIT",)
    assert len(life.fact_refs) == 2 and life.source_profile == "PALM_HA_LINE_LIFE_523_550"
    for e in (life, fate):  # tags, never prose
        assert all(t.isupper() and " " not in t for t in e.interpretation_tags)


def test_the_labelling_profile_must_match(ruleset: Any, tmp_path: Path) -> None:
    copy = tmp_path / "palm_rules"
    shutil.copytree(PALM_RULES_DIR, copy)
    path = copy / "rules" / "ha_life_line_origin_under_jupiter.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "labelling_profile: PALM_HA_MAP_LINES_384_393", "labelling_profile: PALM_CH_LINES_PART1"
        ),
        encoding="utf-8",
    )
    other = load_palm_ruleset(copy, COVERAGE)
    ev = {
        e.rule_id: e
        for e in evaluate_palm_rules(other, fact_set(HandSide.LEFT, with_roles=True), KV)
    }
    assert ev["PALMR_HA_LIFE_LINE_ORIGIN_UNDER_JUPITER"].status is RuleStatus.NOT_TRIGGERED


# ---- validation: what the loader refuses -----------------------------------------------------
def _mutated(tmp_path: Path, relative: str, change: Callable[[dict[str, Any]], None]) -> Path:
    copy = Path(tempfile.mkdtemp(dir=tmp_path)) / "palm_rules"
    shutil.copytree(PALM_RULES_DIR, copy)
    path = copy / relative
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return copy


RULE = "rules/ch_left_hand_inherited_tendencies.yaml"


def _expect(
    tmp_path: Path, relative: str, change: Callable[[dict[str, Any]], None], text: str
) -> None:
    with pytest.raises(PalmRulesetLoadError) as caught:
        load_palm_ruleset(_mutated(tmp_path, relative, change), COVERAGE)
    assert text in str(caught.value), str(caught.value)


def test_a_rule_for_an_unread_concept_is_refused(tmp_path: Path) -> None:
    def change(d: dict[str, Any]) -> None:
        d["concepts"] = ["PALM_FEATURE.THUMB"]
        d["source_profile"] = "PALM_HA_UNREAD"
        d["source_location"] = "pp. 116-121"

    _expect(tmp_path, RULE, change, "cannot back a rule")


def test_a_rule_for_an_excluded_concept_is_refused(tmp_path: Path) -> None:
    def change(d: dict[str, Any]) -> None:
        d["concepts"] = ["PALM_FEATURE.AGE_DATING"]
        d["source_profile"] = "PALM_HA_LINE_LIFE_523_550"
        d["source_location"] = "para. 525, p. 230"

    _expect(tmp_path, RULE, change, "EXCLUDED_BY_POLICY")


def test_a_rule_at_an_unrecorded_location_is_refused(tmp_path: Path) -> None:
    _expect(tmp_path, RULE, lambda d: d.update(source_location="p. 999"), "no coverage record")


def test_a_rule_for_an_unrecorded_concept_is_refused(tmp_path: Path) -> None:
    _expect(
        tmp_path, RULE, lambda d: d.update(concepts=["PALM_LINE.INVENTED"]), "no coverage record"
    )


@pytest.mark.parametrize(
    "tag",
    [
        "DISEASE_RISK",
        "SHORT_LIFESPAN",
        "DEATH_PREDICTION",
        "CRIMINAL_TENDENCY",
        "MENTAL_ILLNESS_SIGN",
        "FERTILITY_SCORE",
        "PATERNITY_DOUBT",
        "SEXUAL_CONDUCT_SIGN",
        "RACIAL_RANKING",
        "INTELLECT_RANKING",
        "MORAL_CHARACTER",
        "INHERENTLY_BAD_PERSON",
    ],
)
def test_prohibited_interpretation_tags_are_refused_in_the_vocabulary(
    tmp_path: Path, tag: str
) -> None:
    def change(d: dict[str, Any]) -> None:
        d["tags"].append({"tag": tag, "claim_kind": "TRADITIONAL_TENDENCY", "description": "x"})

    _expect(tmp_path, "tag_vocabulary.yaml", change, "prohibited")


def test_a_prohibited_description_or_note_is_refused(tmp_path: Path) -> None:
    _expect(
        tmp_path,
        "tag_vocabulary.yaml",
        lambda d: d["tags"][0].update(description="The line indicates a serious disease."),
        "prohibited",
    )
    _expect(
        tmp_path,
        RULE,
        lambda d: d.update(source_note="The source predicts what will happen in the future."),
        "prohibited",
    )


def test_a_tag_outside_the_closed_vocabulary_is_refused(tmp_path: Path) -> None:
    _expect(
        tmp_path,
        RULE,
        lambda d: d.update(interpretation_tags=["BRAND_NEW_TAG"]),
        "closed tag vocabulary",
    )


def test_a_tag_must_match_the_rules_claim_kind(tmp_path: Path) -> None:
    _expect(tmp_path, RULE, lambda d: d.update(claim_kind="TRADITIONAL_TENDENCY"), "claim kind")


def test_a_rule_cannot_carry_prose_a_prediction_or_several_profiles(tmp_path: Path) -> None:
    _expect(
        tmp_path,
        RULE,
        lambda d: d.update(interpretation_text="a free sentence"),
        "schema validation",
    )
    _expect(tmp_path, RULE, lambda d: d.update(source_profile=["A", "B"]), "schema validation")
    _expect(tmp_path, RULE, lambda d: d.update(source_location=""), "schema validation")
    _expect(tmp_path, RULE, lambda d: d.update(claim_kind="EVENT_PREDICTION"), "schema validation")
    _expect(tmp_path, RULE, lambda d: d.update(framing="SCIENTIFIC_FACT"), "schema validation")


def test_a_rule_needs_a_conflict_that_exists(tmp_path: Path) -> None:
    _expect(
        tmp_path, RULE, lambda d: d.update(known_conflicts=["NO_SUCH_CONFLICT"]), "unknown conflict"
    )


def test_the_indian_profile_cannot_have_a_rule(tmp_path: Path) -> None:
    _expect(
        tmp_path,
        RULE,
        lambda d: d.update(methodology_profile="PALM_INDIAN_HASTA_SAMUDRIKA"),
        "schema validation",
    )


def test_the_manifest_and_namespace_rules(tmp_path: Path) -> None:
    _expect(
        tmp_path, "ruleset.yaml", lambda d: d.update(standards_version="1.4.0"), "standards_version"
    )
    _expect(tmp_path, RULE, lambda d: d.update(rule_id="BPHS_SAN_SOMETHING"), "schema validation")
    _expect(tmp_path, RULE, lambda d: d.update(ruleset_id="OTHER"), "differs from the manifest")
    copy = tmp_path / "palm_rules"
    shutil.copytree(PALM_RULES_DIR, copy)
    (copy / "ruleset.yaml").unlink()
    with pytest.raises(PalmRulesetLoadError, match="exactly one palm ruleset manifest"):
        load_palm_ruleset(copy, COVERAGE)


def test_a_duplicate_rule_and_a_reserved_identifier_are_refused(tmp_path: Path) -> None:
    copy = tmp_path / "palm_rules"
    shutil.copytree(PALM_RULES_DIR, copy)
    source = copy / "rules" / "ch_left_hand_inherited_tendencies.yaml"
    shutil.copy(source, copy / "rules" / "duplicate.yaml")
    with pytest.raises(PalmRulesetLoadError, match="duplicate rule_id"):
        load_palm_ruleset(copy, COVERAGE)
    with pytest.raises(PalmRulesetLoadError, match="reserved"):
        load_palm_ruleset(
            PALM_RULES_DIR,
            COVERAGE,
            reserved_ids=frozenset({"PALMR_CH_LEFT_HAND_INHERITED_TENDENCIES"}),
        )
