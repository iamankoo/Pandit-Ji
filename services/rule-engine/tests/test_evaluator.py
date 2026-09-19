"""Phase 6C/6D: condition operators, statuses, cancellations, dependencies,
ambiguity policy and priority."""

from __future__ import annotations

from typing import Any

import pytest

from pandit_rule_engine.adapters import FactsError, facts_from_kundli
from pandit_rule_engine.conditions import RuleOutcome
from pandit_rule_engine.results import status_label
from pandit_rule_engine.vocab import Reason, Status
from tests.chart_builder import chart, full_placements, kundli_dict
from tests.helpers import StubDerived, evaluate_doc, rule_doc


def _rule(condition: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    reading = {"reading_id": "R1", "basis": "translation", "conditions": condition}
    return rule_doc(readings=[reading], **overrides)


def _house(planet: str, houses: list[int], reference: str = "lagna") -> dict[str, Any]:
    return {"op": "planet_house", "planet": planet, "reference": reference, "houses": houses}


def _status(doc: dict[str, Any], facts: Any, derived: Any = None) -> Status:
    result = evaluate_doc(doc, facts, derived)
    assert isinstance(result.status, Status)
    return result.status


def _label(result: Any) -> str:
    return status_label(result.status, result.reason, result.detail)


# --------------------------------------------------------------------------
# Adapter
# --------------------------------------------------------------------------


def test_adapter_reads_phase5_shape_and_keeps_standards_version() -> None:
    facts = chart("aries", full_placements(jupiter="cancer"))
    assert facts.lagna_sign.value == "aries"
    assert facts.planets[next(iter(facts.planets))].house >= 1
    assert facts.snapshot.standards_version == "1.3.0"
    assert facts.snapshot.ayanamsa == "lahiri"
    assert facts.snapshot.timezone == "Asia/Kolkata"
    assert facts.snapshot.latitude == pytest.approx(28.61)


def test_adapter_rejects_missing_required_field() -> None:
    data = kundli_dict("aries", full_placements())
    del data["planets"][0]["retrograde"]
    with pytest.raises(FactsError, match="retrograde"):
        facts_from_kundli(data)


def test_adapter_rejects_unknown_sign_and_inconsistent_house() -> None:
    data = kundli_dict("aries", full_placements())
    data["planets"][0]["rashi"] = "ophiuchus"
    with pytest.raises(FactsError, match="unknown sign"):
        facts_from_kundli(data)
    bad = kundli_dict("aries", full_placements())
    bad["planets"][0]["house"] = 12
    with pytest.raises(FactsError, match="inconsistent"):
        facts_from_kundli(bad)


# --------------------------------------------------------------------------
# Atoms
# --------------------------------------------------------------------------


def test_planet_house_from_lagna_and_from_moon() -> None:
    facts = chart("aries", full_placements(jupiter="cancer", moon="libra"))
    assert evaluate_doc(_rule(_house("jupiter", [4])), facts).status is Status.TRIGGERED
    assert evaluate_doc(_rule(_house("jupiter", [10], "moon")), facts).status is Status.TRIGGERED
    assert evaluate_doc(_rule(_house("jupiter", [5], "moon")), facts).status is Status.NOT_TRIGGERED


def test_planet_dignity_flag_and_modality() -> None:
    facts = chart(
        "aries",
        full_placements(jupiter="cancer", saturn="libra", sun="leo"),
        retrograde=frozenset({"saturn"}),
        combust=frozenset({"jupiter"}),
    )
    dignity = {"op": "planet_dignity", "planet": "jupiter", "in": ["exalted", "own_sign"]}
    assert evaluate_doc(_rule(dignity), facts).status is Status.TRIGGERED
    retro = {"op": "planet_flag", "planet": "saturn", "flag": "retrograde"}
    assert evaluate_doc(_rule(retro), facts).status is Status.TRIGGERED
    combust = {"op": "planet_flag", "planet": "jupiter", "flag": "combust"}
    assert evaluate_doc(_rule(combust), facts).status is Status.TRIGGERED
    modality = {"op": "planet_modality", "planet": "sun", "in": ["fixed"]}
    assert evaluate_doc(_rule(modality), facts).status is Status.TRIGGERED


def test_sun_is_never_combust_and_nodes_are_not_evaluated() -> None:
    facts = chart("aries", full_placements())
    sun = {"op": "planet_flag", "planet": "sun", "flag": "combust"}
    assert evaluate_doc(_rule(sun), facts).status is Status.NOT_TRIGGERED
    rahu = {"op": "planet_flag", "planet": "rahu", "flag": "combust"}
    result = evaluate_doc(_rule(rahu), facts)
    assert _label(result) == "NOT_EVALUABLE(not_specified_by_source:combust.rahu)"


def test_node_dignity_is_not_specified_by_source() -> None:
    facts = chart("aries", full_placements())
    cond = {"op": "planet_dignity", "planet": "rahu", "in": ["exalted"]}
    assert evaluate_doc(_rule(cond), facts).reason is Reason.NOT_SPECIFIED_BY_SOURCE


def test_same_sign_conjunction() -> None:
    facts = chart("aries", full_placements(jupiter="leo", sun="leo", moon="virgo"))
    yes = {"op": "same_sign", "a": "jupiter", "b": "sun"}
    no = {"op": "same_sign", "a": "jupiter", "b": "moon"}
    assert evaluate_doc(_rule(yes), facts).status is Status.TRIGGERED
    assert evaluate_doc(_rule(no), facts).status is Status.NOT_TRIGGERED


def test_full_sign_aspect_present_is_definite() -> None:
    facts = chart("aries", full_placements(mars="aries", venus="libra"))  # 7th aspect
    cond = {"op": "aspected_by", "planet": "mars", "by": "venus"}
    assert evaluate_doc(_rule(cond), facts).status is Status.TRIGGERED


def test_absent_full_aspect_is_not_false_but_requires_partial_drishti() -> None:
    # Venus in Leo: Mars in Aries is its 9th, where a partial aspect may exist.
    facts = chart("aries", full_placements(mars="aries", venus="leo"))
    cond = {"op": "aspected_by", "planet": "mars", "by": "venus"}
    result = evaluate_doc(_rule(cond), facts)
    assert result.status is Status.NOT_EVALUABLE
    assert result.reason is Reason.REQUIRES_PARTIAL_DRISHTI
    unaspected = {"op": "not", "arg": cond}
    assert evaluate_doc(_rule(unaspected), facts).reason is Reason.REQUIRES_PARTIAL_DRISHTI


def test_no_aspect_at_all_is_definitely_false_where_no_partial_aspect_can_exist() -> None:
    # Venus in Gemini: Mars in Aries is its 11th, on which BPHS gives no aspect.
    facts = chart("aries", full_placements(mars="aries", venus="gemini"))
    cond = {"op": "aspected_by", "planet": "mars", "by": "venus"}
    assert _status(_rule(cond), facts) is Status.NOT_TRIGGERED
    unaspected = {"op": "not", "arg": cond}
    assert _status(_rule(unaspected), facts) is Status.TRIGGERED


def test_unaspected_is_false_when_a_full_aspect_is_present() -> None:
    facts = chart("aries", full_placements(mars="aries", venus="libra"))
    cond = {"op": "not", "arg": {"op": "aspected_by", "planet": "mars", "by": "venus"}}
    assert evaluate_doc(_rule(cond), facts).status is Status.NOT_TRIGGERED


def test_natural_nature_atom_and_mixed_mercury() -> None:
    facts = chart("aries", full_placements())
    cond = {"op": "natural_nature", "planet": "jupiter", "is": "benefic"}
    assert evaluate_doc(_rule(cond), facts).status is Status.TRIGGERED
    mixed = StubDerived(natures={"mercury": "mixed"})
    merc = {"op": "natural_nature", "planet": "mercury", "is": "benefic"}
    result = evaluate_doc(_rule(merc), facts, mixed)
    assert result.reason is Reason.READING_AMBIGUOUS


def test_sign_lord_relation_enemy_sign() -> None:
    facts = chart("aries", full_placements(jupiter="gemini"))  # lord Mercury
    cond = {"op": "sign_lord_relation", "planet": "jupiter", "basis": "natural", "kinds": ["enemy"]}
    derived = StubDerived(relations={("natural", "jupiter", "mercury"): "enemy"})
    assert evaluate_doc(_rule(cond), facts, derived).status is Status.TRIGGERED
    own = chart("aries", full_placements(jupiter="sagittarius"))
    assert evaluate_doc(_rule(cond), own, derived).status is Status.NOT_TRIGGERED


def test_distinct_signs_counts_seven_planets_by_default() -> None:
    placements = full_placements(
        sun="aries", moon="aries", mars="aries", mercury="taurus", jupiter="taurus", venus="gemini"
    )
    facts = chart("aries", {**placements, "saturn": "gemini", "rahu": "leo", "ketu": "aquarius"})
    cond = {"op": "distinct_signs", "over": {}, "count": 3}
    assert evaluate_doc(_rule(cond), facts).status is Status.TRIGGERED
    other = {"op": "distinct_signs", "over": {}, "count": 4}
    assert evaluate_doc(_rule(other), facts).status is Status.NOT_TRIGGERED


# --------------------------------------------------------------------------
# Quantifiers, node policy and missing planets
# --------------------------------------------------------------------------


def _exists(over: dict[str, Any], where: dict[str, Any]) -> dict[str, Any]:
    return {"op": "exists", "over": over, "where": where}


def _in_second_from_moon(planet: str = "$it") -> dict[str, Any]:
    return _house(planet, [2], "moon")


def test_exists_and_for_all_and_count() -> None:
    facts = chart("aries", full_placements(moon="cancer", mars="leo", sun="cancer", saturn="leo"))
    where = _in_second_from_moon()
    over = {"exclude": ["sun"]}
    assert evaluate_doc(_rule(_exists(over, where)), facts).status is Status.TRIGGERED
    every = {"op": "for_all", "over": {"bodies": ["mars", "saturn"]}, "where": where}
    assert evaluate_doc(_rule(every), facts).status is Status.TRIGGERED
    count = {
        "op": "count",
        "over": {"bodies": ["mars", "saturn", "venus"]},
        "where": where,
        "at_least": 2,
    }
    assert evaluate_doc(_rule(count), facts).status is Status.TRIGGERED
    count3 = {**count, "at_least": 3}
    assert evaluate_doc(_rule(count3), facts).status is Status.NOT_TRIGGERED


def test_count_records_observed_count_as_evidence() -> None:
    facts = chart("aries", full_placements(moon="cancer", mars="leo", saturn="leo"))
    count = {
        "op": "count",
        "over": {"bodies": ["mars", "saturn"]},
        "where": _in_second_from_moon(),
        "at_least": 1,
    }
    result = evaluate_doc(_rule(count), facts)
    assert "count = 2" in result.readings[0].evidence


def test_node_alone_in_second_from_moon_is_node_participation_unspecified() -> None:
    placements = full_placements(
        moon="cancer", rahu="leo", sun="aries", mars="aries", saturn="aries"
    )
    facts = chart("aries", placements)
    over = {"exclude": ["sun"], "nodes": "unspecified"}
    result = evaluate_doc(_rule(_exists(over, _in_second_from_moon())), facts)
    assert _label(result) == "NOT_EVALUABLE(node_participation_unspecified:nodes)"


def test_node_policy_excluded_and_included_are_definite() -> None:
    placements = full_placements(
        moon="cancer", rahu="leo", sun="aries", mars="aries", saturn="aries"
    )
    facts = chart("aries", placements)
    excluded = {"exclude": ["sun"], "nodes": "excluded"}
    included = {"exclude": ["sun"], "nodes": "included"}
    assert (
        evaluate_doc(_rule(_exists(excluded, _in_second_from_moon())), facts).status
        is Status.NOT_TRIGGERED
    )
    assert (
        evaluate_doc(_rule(_exists(included, _in_second_from_moon())), facts).status
        is Status.TRIGGERED
    )


def test_node_presence_that_does_not_change_the_result_is_not_ambiguous() -> None:
    placements = full_placements(moon="cancer", rahu="leo", mars="leo", sun="aries", saturn="aries")
    facts = chart("aries", placements)
    over = {"exclude": ["sun"], "nodes": "unspecified"}
    assert (
        evaluate_doc(_rule(_exists(over, _in_second_from_moon())), facts).status is Status.TRIGGERED
    )


def test_missing_planet_gives_missing_dependency_not_false() -> None:
    facts = chart("aries", {"moon": "cancer", "mars": "aries"})
    over = {"bodies": ["mars", "saturn"]}
    result = evaluate_doc(_rule(_exists(over, _in_second_from_moon())), facts)
    assert _label(result) == "NOT_EVALUABLE(missing_dependency:planet.saturn)"
    direct = evaluate_doc(_rule(_house("jupiter", [1])), facts)
    assert _label(direct) == "NOT_EVALUABLE(missing_dependency:planet.jupiter)"


def test_missing_planet_does_not_hide_a_definite_true() -> None:
    facts = chart("aries", {"moon": "cancer", "mars": "leo"})
    over = {"bodies": ["mars", "saturn"]}
    assert (
        evaluate_doc(_rule(_exists(over, _in_second_from_moon())), facts).status is Status.TRIGGERED
    )


def test_uncertain_natural_nature_membership_is_reading_ambiguous() -> None:
    facts = chart(
        "aries", full_placements(moon="cancer", mercury="leo", jupiter="aries", venus="aries")
    )
    over = {"nature": "benefic"}
    cond = _exists(over, _in_second_from_moon())
    derived = StubDerived(
        natures={"mercury": "mixed", "sun": "malefic", "saturn": "malefic", "mars": "malefic"}
    )
    assert evaluate_doc(_rule(cond), facts, derived).reason is Reason.READING_AMBIGUOUS


# --------------------------------------------------------------------------
# Kleene logic
# --------------------------------------------------------------------------


def test_false_beats_unknown_in_all_and_true_beats_unknown_in_any() -> None:
    facts = chart("aries", {"moon": "cancer"})
    unknown_cond = _house("saturn", [1])
    false_cond = _house("moon", [1])
    true_cond = _house("moon", [4])
    assert (
        evaluate_doc(_rule({"op": "all", "args": [unknown_cond, false_cond]}), facts).status
        is Status.NOT_TRIGGERED
    )
    assert (
        evaluate_doc(_rule({"op": "any", "args": [unknown_cond, true_cond]}), facts).status
        is Status.TRIGGERED
    )
    assert (
        evaluate_doc(_rule({"op": "all", "args": [unknown_cond, true_cond]}), facts).status
        is Status.NOT_EVALUABLE
    )
    assert (
        evaluate_doc(_rule({"op": "any", "args": [unknown_cond, false_cond]}), facts).status
        is Status.NOT_EVALUABLE
    )


# --------------------------------------------------------------------------
# Rule-level behaviour
# --------------------------------------------------------------------------


def test_exceptions_cancellations_and_dependencies() -> None:
    facts = chart("aries", full_placements(jupiter="cancer", saturn="aries"))
    base = _house("jupiter", [4])
    exception = {"exception_id": "EX1", "when": _house("saturn", [1])}
    result = evaluate_doc(_rule(base, exceptions=[exception]), facts)
    assert result.status is Status.NOT_TRIGGERED
    assert result.readings[0].exceptions_applied == ("EX1",)
    assert result.readings[0].detected_status is Status.TRIGGERED

    full = {"cancellation_id": "C_FULL", "when": _house("saturn", [1])}
    assert evaluate_doc(_rule(base, cancellations=[full]), facts).status is Status.CANCELLED
    partial = {**full, "cancellation_id": "C_PART", "effect": "partial"}
    result = evaluate_doc(_rule(base, cancellations=[partial]), facts)
    assert result.status is Status.PARTIALLY_CANCELLED
    assert result.interpretation_tags is not None
    inactive = {"cancellation_id": "C_NO", "when": _house("saturn", [7])}
    assert evaluate_doc(_rule(base, cancellations=[inactive]), facts).status is Status.TRIGGERED


def test_unknown_cancellation_makes_result_not_evaluable_never_triggered() -> None:
    facts = chart("aries", {"jupiter": "cancer"})
    base = _house("jupiter", [4])
    cancel = {"cancellation_id": "C_UNK", "when": _house("venus", [1])}
    result = evaluate_doc(_rule(base, cancellations=[cancel]), facts)
    assert _label(result) == "NOT_EVALUABLE(missing_dependency:planet.venus)"
    assert result.readings[0].detected_status is Status.TRIGGERED


def test_unresolved_dependency_blocks_a_detected_rule_and_keeps_detection() -> None:
    facts = chart("aries", full_placements(jupiter="cancer"))
    dependency = {
        "dependency_id": "PARTNER_CHART",
        "kind": "later_phase_input",
        "owner_phase": 11,
        "reason": "requires_partner_chart",
        "unresolved_effect": "not_evaluable_if_detected",
    }
    result = evaluate_doc(_rule(_house("jupiter", [4]), dependencies=[dependency]), facts)
    assert _label(result) == "NOT_EVALUABLE(requires_partner_chart:PARTNER_CHART)"
    assert result.readings[0].detected_status is Status.TRIGGERED
    assert result.interpretation_tags is None
    not_detected = evaluate_doc(_rule(_house("jupiter", [5]), dependencies=[dependency]), facts)
    assert not_detected.status is Status.NOT_TRIGGERED


def test_informational_dependency_does_not_change_the_result() -> None:
    facts = chart("aries", full_placements(jupiter="cancer"))
    dependency = {
        "dependency_id": "SHADBALA",
        "kind": "later_phase_input",
        "owner_phase": 9,
        "reason": "requires_shadbala",
    }
    result = evaluate_doc(_rule(_house("jupiter", [4]), dependencies=[dependency]), facts)
    assert result.status is Status.TRIGGERED


def _two_readings(first: dict[str, Any], second: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "reading_id": "READING_A",
            "source_id": "SRC_A",
            "basis": "translation",
            "conditions": first,
        },
        {
            "reading_id": "READING_B",
            "source_id": "SRC_B",
            "basis": "sanskrit_reading",
            "conditions": second,
        },
    ]


def test_agreeing_readings_return_the_common_result_and_keep_every_reading() -> None:
    facts = chart("aries", full_placements(mars="scorpio"))
    readings = _two_readings(_house("mars", [8]), _house("mars", [1, 8]))
    result = evaluate_doc(rule_doc(readings=readings), facts)
    assert result.status is Status.TRIGGERED
    assert result.readings_agree is True
    assert [r.reading_id for r in result.readings] == ["READING_A", "READING_B"]
    assert [r.source_id for r in result.readings] == ["SRC_A", "SRC_B"]


def test_disagreeing_readings_are_reading_ambiguous_and_all_outcomes_preserved() -> None:
    facts = chart("aries", full_placements(mars="aries"))
    readings = _two_readings(_house("mars", [8]), _house("mars", [1, 8]))
    result = evaluate_doc(rule_doc(readings=readings), facts)
    assert _label(result).startswith("NOT_EVALUABLE(reading_ambiguous")
    assert result.readings_agree is False
    assert [r.status for r in result.readings] == [Status.NOT_TRIGGERED, Status.TRIGGERED]
    assert result.interpretation_tags is None


def test_same_status_with_different_reasons_is_ambiguous() -> None:
    facts = chart("aries", {"jupiter": "cancer", "mars": "aries"})
    aspect = {"op": "aspected_by", "planet": "mars", "by": "jupiter"}
    readings = _two_readings(_house("venus", [1]), aspect)
    result = evaluate_doc(rule_doc(readings=readings), facts)
    assert result.status is Status.NOT_EVALUABLE
    assert result.reason is Reason.READING_AMBIGUOUS
    assert {r.reason for r in result.readings} == {
        Reason.MISSING_DEPENDENCY,
        Reason.REQUIRES_PARTIAL_DRISHTI,
    }


def test_common_precondition_is_anded_with_every_reading() -> None:
    facts = chart("aries", full_placements(jupiter="cancer", saturn="aries"))
    doc = rule_doc(conditions=_house("saturn", [7]))
    assert evaluate_doc(doc, facts).status is Status.NOT_TRIGGERED


def test_rule_result_dependency_reads_other_rule_outcomes() -> None:
    facts = chart("aries", full_placements())
    cond = {"op": "rule_result", "rule_id": "TEST_OTHER", "in": ["TRIGGERED"]}
    doc = _rule(cond)
    triggered = {"TEST_OTHER": RuleOutcome(Status.TRIGGERED)}
    assert evaluate_doc(doc, facts, rule_results=triggered).status is Status.TRIGGERED
    not_triggered = {"TEST_OTHER": RuleOutcome(Status.NOT_TRIGGERED)}
    assert evaluate_doc(doc, facts, rule_results=not_triggered).status is Status.NOT_TRIGGERED
    unknown_other = {
        "TEST_OTHER": RuleOutcome(Status.NOT_EVALUABLE, Reason.CONDITION_ABSENT_IN_SOURCE)
    }
    result = evaluate_doc(doc, facts, rule_results=unknown_other)
    assert result.reason is Reason.CONDITION_ABSENT_IN_SOURCE
    assert _label(evaluate_doc(doc, facts)) == "NOT_EVALUABLE(missing_dependency:rule.TEST_OTHER)"


def test_priority_is_metadata_and_never_changes_a_result() -> None:
    facts = chart("aries", full_placements(jupiter="cancer"))
    low = evaluate_doc(rule_doc(priority=0), facts)
    high = evaluate_doc(rule_doc(priority=10_000), facts)
    assert low.status is high.status is Status.TRIGGERED
    assert low.readings == high.readings
    assert (low.priority, high.priority) == (0, 10_000)


def test_not_evaluable_always_has_a_reason() -> None:
    facts = chart("aries", {})
    result = evaluate_doc(rule_doc(), facts)
    assert result.status is Status.NOT_EVALUABLE and result.reason is not None
    assert all(item.reason is not None for item in result.readings)


def test_interpretation_tags_only_attached_to_a_result_that_obtains() -> None:
    facts = chart("aries", full_placements(jupiter="cancer"))
    assert evaluate_doc(rule_doc(), facts).interpretation_tags is not None
    not_obtained = chart("aries", full_placements(jupiter="taurus"))
    assert evaluate_doc(rule_doc(), not_obtained).interpretation_tags is None
