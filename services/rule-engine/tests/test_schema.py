"""Phase 6A: rule schema validation."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from pandit_rule_engine.schema import Rule, RulesetManifest, TableDocument
from tests.helpers import rule_doc


def _reading(condition: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"reading_id": "R1", "basis": "translation", "conditions": condition}]


def test_valid_rule_parses() -> None:
    rule = Rule.model_validate(rule_doc())
    assert rule.rule_id == "TEST_SAN_JUPITER_KENDRA"
    assert rule.readings[0].reading_id == "R1"
    assert rule.applicability.gender == "not_required"


@pytest.mark.parametrize(
    "missing",
    [
        "source",
        "source_id",
        "source_edition",
        "translator",
        "source_location",
        "source_version",
        "source_tier",
        "verification_level",
        "standards_version",
        "confidence",
        "interpretation_tags",
        "readings",
    ],
)
def test_missing_provenance_or_required_field_is_rejected(missing: str) -> None:
    doc = rule_doc()
    del doc[missing]
    with pytest.raises(ValidationError):
        Rule.model_validate(doc)


def test_translator_may_be_explicit_null_but_not_absent() -> None:
    assert Rule.model_validate(rule_doc(translator=None)).translator is None


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(python_code="run"))


@pytest.mark.parametrize(
    "condition",
    [
        {"op": "run_python", "code": "1"},
        {"op": "planet_house", "planet": "pluto", "houses": [1]},
        {"op": "planet_house", "planet": "jupiter", "houses": [13]},
        {"op": "planet_house", "planet": "jupiter", "houses": []},
        {"op": "planet_house", "planet": "jupiter", "reference": "venus_lagna", "houses": [1]},
        {"op": "planet_dignity", "planet": "sun", "in": ["moolatrikona"]},
        {"op": "all", "args": []},
        {
            "op": "count",
            "over": {},
            "where": {"op": "planet_flag", "planet": "$it", "flag": "combust"},
            "at_least": 0,
        },
    ],
)
def test_invalid_condition_is_rejected(condition: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(readings=_reading(condition)))


def test_duplicate_reading_ids_are_rejected() -> None:
    reading = _reading({"op": "planet_flag", "planet": "jupiter", "flag": "retrograde"})[0]
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(readings=[reading, reading]))


def test_rule_id_must_extend_profile() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(profile="OTHER_PROFILE"))


@pytest.mark.parametrize("bad_id", ["lower_case", "HAS SPACE", "", "-X"])
def test_identifiers_must_be_upper_snake(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(rule_id=bad_id, profile=bad_id))


def test_invalid_dependency_reason_is_rejected() -> None:
    dep = {"dependency_id": "X", "kind": "fact", "reason": "unknown"}
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(dependencies=[dep]))


def test_valid_dependency_reason_is_accepted() -> None:
    dep = {
        "dependency_id": "PARTNER_CHART",
        "kind": "later_phase_input",
        "owner_phase": 11,
        "reason": "requires_partner_chart",
        "unresolved_effect": "not_evaluable_if_detected",
    }
    rule = Rule.model_validate(rule_doc(dependencies=[dep]))
    assert rule.dependencies[0].reason.value == "requires_partner_chart"


def test_interpretation_tags_are_language_neutral_ids() -> None:
    tags = {"domain": ["Career Success"], "signification": [], "effect_class": "supportive"}
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(interpretation_tags=tags))


def test_effect_class_is_closed() -> None:
    tags = {"domain": [], "signification": [], "effect_class": "will_definitely_happen"}
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(interpretation_tags=tags))


def test_gender_is_never_a_detection_requirement() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(applicability={"gender": "required"}))


def test_priority_must_be_non_negative_int() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(priority=-1))


def test_node_policy_values_are_closed() -> None:
    cond = {
        "op": "exists",
        "over": {"nodes": "sometimes"},
        "where": {"op": "planet_flag", "planet": "$it", "flag": "combust"},
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(readings=_reading(cond)))


def test_planet_set_takes_bodies_or_nature_not_both() -> None:
    cond = {
        "op": "exists",
        "over": {"bodies": ["mars"], "nature": "malefic"},
        "where": {"op": "planet_flag", "planet": "$it", "flag": "combust"},
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(rule_doc(readings=_reading(cond)))


def test_manifest_and_table_documents_parse() -> None:
    manifest = RulesetManifest.model_validate(
        {
            "document_type": "ruleset",
            "ruleset_id": "PANDIT_JI_PHASE6",
            "ruleset_version": "1.0.0",
            "schema_version": 1,
            "standards_version": "1.4.0",
        }
    )
    assert manifest.schema_version == 1
    table = TableDocument.model_validate(
        {
            "document_type": "table",
            "table_id": "T",
            "table_kind": "moolatrikona",
            "source": "Test Work",
            "source_id": "TEST_WORK",
            "source_edition": "e",
            "translator": "t",
            "source_location": "l",
            "source_version": "1",
            "source_tier": 2,
            "verification_level": "OCR-TRANSLATION",
            "standards_version": "1.4.0",
            "confidence": "HIGH",
            "data": {},
        }
    )
    assert table.table_kind == "moolatrikona"
