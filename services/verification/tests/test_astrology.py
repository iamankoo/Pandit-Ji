"""Astrology verification over the structure of the Phase 6 EvidenceBundle (Phase 16)."""

from __future__ import annotations

from conftest import Judge, assert_status
from helpers import World, make_claim
from pandit_contracts.agent import ClaimType
from pandit_contracts.verification import ReasonCode as R
from pandit_contracts.verification import VerificationStatus as S

FACT = ClaimType.CALCULATION_FACT
INT = ClaimType.TRADITIONAL_INTERPRETATION


def _fact(world: World, text: str, *ids: str):
    return make_claim(world, "C1", text, FACT, list(ids))


def _interp(world: World, text: str, *ids: str):
    return make_claim(world, "C1", text, INT, list(ids))


# -- calculated facts ----------------------------------------------------------------------------


def test_a_valid_calculated_placement_is_verified(judge: Judge, world: World) -> None:
    result = judge(
        _fact(
            world,
            "Mars is placed in Aries in the first house, in its own sign.",
            "astro.planet.mars",
        )
    )
    assert_status(result, S.VERIFIED)


def test_retrograde_and_dignity_are_checked(judge: Judge, world: World) -> None:
    ok = judge(
        _fact(world, "Saturn is retrograde in Capricorn in the tenth house.", "astro.planet.saturn")
    )
    assert_status(ok, S.VERIFIED)
    wrong = judge(_fact(world, "Saturn is not retrograde.", "astro.planet.saturn"))
    assert_status(wrong, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)
    dignity = judge(_fact(world, "Saturn is debilitated in Capricorn.", "astro.planet.saturn"))
    assert_status(dignity, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)


def test_a_wrong_sign_or_house_contradicts_the_chart(judge: Judge, world: World) -> None:
    assert_status(
        judge(_fact(world, "Mars is placed in Leo.", "astro.planet.mars")),
        S.CONFLICTING_EVIDENCE,
        R.CONTRADICTS_EVIDENCE,
    )
    assert_status(
        judge(_fact(world, "Venus is in the 5th house.", "astro.planet.venus")),
        S.CONFLICTING_EVIDENCE,
        R.CONTRADICTS_EVIDENCE,
    )


def test_p_a_self_contradicting_claim_is_rejected(judge: Judge, world: World) -> None:
    result = judge(_fact(world, "Mars is in Aries. Mars is in Leo.", "astro.planet.mars"))
    assert_status(result, S.CONFLICTING_EVIDENCE, R.SELF_CONTRADICTION)


def test_o_an_unsupported_natural_language_claim_is_not_verified(
    judge: Judge, world: World
) -> None:
    result = judge(_fact(world, "Mars is in Aries and will make you rich.", "astro.planet.mars"))
    assert_status(result, S.UNSUPPORTED)
    assert {R.OVERSTATED_CERTAINTY, R.UNSUPPORTED_ASSERTION, R.TOPIC_NOT_IN_EVIDENCE} & {
        r.code for r in result.reasons
    }


def test_a_planet_the_claim_did_not_cite_is_ungrounded(judge: Judge, world: World) -> None:
    result = judge(_fact(world, "Venus is in Libra.", "astro.planet.mars"))
    assert_status(result, S.UNSUPPORTED, R.UNGROUNDED_ENTITY)


def test_a_claim_with_no_recognised_placement_is_unverifiable(judge: Judge, world: World) -> None:
    result = judge(_fact(world, "A placement was calculated.", "astro.planet.mars"))
    assert_status(result, S.UNVERIFIABLE, R.NO_CHECKABLE_CONTENT)


def test_the_lagna_is_checked(judge: Judge, world: World) -> None:
    assert_status(
        judge(_fact(world, "The lagna is Cancer.", "astro.lagna")),
        S.VERIFIED,
    )
    assert_status(
        judge(_fact(world, "The ascendant is Leo.", "astro.lagna")),
        S.CONFLICTING_EVIDENCE,
        R.CONTRADICTS_EVIDENCE,
    )


def test_a_hindi_placement_is_checked_with_the_small_vocabulary(judge: Judge, world: World) -> None:
    assert_status(judge(_fact(world, "मंगल मेष राशि में है", "astro.planet.mars")), S.VERIFIED)
    assert_status(
        judge(_fact(world, "मंगल सिंह राशि में है", "astro.planet.mars")),
        S.CONFLICTING_EVIDENCE,
    )
    assert_status(
        judge(_fact(world, "Mangal Mesh rashi mein hai", "astro.planet.mars")), S.VERIFIED
    )


def test_an_astrology_fact_claim_cannot_cite_a_rule(judge: Judge, world: World) -> None:
    result = judge(_fact(world, "Mars is placed in Aries.", "ASTRO_DOSHA"))
    assert_status(result, S.UNSUPPORTED, R.SEMANTIC_CLASS_MISMATCH)


def test_an_observed_palm_claim_type_does_not_belong_to_astrology(
    judge: Judge, world: World
) -> None:
    claim = make_claim(
        world, "C1", "Mars is placed in Aries.", ClaimType.OBSERVED_FEATURE, ["astro.planet.mars"]
    )
    assert_status(judge(claim), S.UNSUPPORTED, R.SEMANTIC_CLASS_MISMATCH)


# -- rules ---------------------------------------------------------------------------------------


def test_a_triggered_rule_supports_a_traditional_interpretation(judge: Judge, world: World) -> None:
    result = judge(
        _interp(
            world, "Kuja dosha is traditionally read as challenging for marriage.", "ASTRO_DOSHA"
        )
    )
    assert_status(result, S.VERIFIED)
    assert result.rule_refs == ("ASTRO_DOSHA",)
    assert result.provenance.rule_versions == ("ASTRO_DOSHA@1",)
    assert result.provenance.ruleset_hashes == (world.astro.versions.ruleset_content_hash,)
    assert result.provenance.source_ids == ("BPHS_KAPOOR_1987",)


def test_a_rule_that_was_not_triggered_cannot_back_a_claim(judge: Judge, world: World) -> None:
    result = judge(_interp(world, "Tradition reads this as significant.", "ASTRO_NOTTRIG"))
    assert_status(result, S.UNSUPPORTED, R.RULE_NOT_TRIGGERED)


def test_a_cancelled_rule_cannot_back_a_claim(judge: Judge, world: World) -> None:
    result = judge(_interp(world, "Tradition reads this as significant.", "ASTRO_CANCELLED"))
    assert_status(result, S.UNSUPPORTED, R.RULE_NOT_TRIGGERED)


def test_a_not_evaluable_rule_is_insufficient_evidence(judge: Judge, world: World) -> None:
    result = judge(_interp(world, "Tradition reads this as significant.", "ASTRO_NE"))
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.RULE_NOT_EVALUABLE)


def test_a_triggered_rule_with_unresolved_dependencies_is_not_verified(
    judge: Judge, world: World
) -> None:
    result = judge(
        _interp(world, "Dhana yoga is traditionally read as supportive of wealth.", "ASTRO_DEPS")
    )
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.MISSING_REQUIRED_FACT)


def test_a_valence_that_contradicts_the_effect_class_is_a_conflict(
    judge: Judge, world: World
) -> None:
    result = judge(
        _interp(
            world, "Kuja dosha is traditionally read as favourable for marriage.", "ASTRO_DOSHA"
        )
    )
    assert_status(result, S.CONFLICTING_EVIDENCE, R.VALENCE_CONTRADICTS_EFFECT_CLASS)


def test_a_valence_the_rule_does_not_carry_is_unsupported(judge: Judge, world: World) -> None:
    result = judge(
        _interp(world, "Sunapha yoga is traditionally read as favourable.", "ASTRO_MIXED")
    )
    assert_status(result, S.UNSUPPORTED, R.VALENCE_NOT_IN_EVIDENCE)
    neutral = judge(
        _interp(world, "Sunapha yoga is traditionally read as context dependent.", "ASTRO_MIXED")
    )
    assert_status(neutral, S.VERIFIED)


def test_a_topic_the_rule_does_not_carry_is_unsupported(judge: Judge, world: World) -> None:
    result = judge(
        _interp(world, "Kuja dosha is traditionally read as challenging for wealth.", "ASTRO_DOSHA")
    )
    assert_status(result, S.UNSUPPORTED, R.TOPIC_NOT_IN_EVIDENCE)


def test_an_interpretation_stated_as_a_plain_fact_is_unsupported(
    judge: Judge, world: World
) -> None:
    result = judge(_interp(world, "Kuja dosha makes marriage challenging.", "ASTRO_DOSHA"))
    assert_status(result, S.UNSUPPORTED, R.INTERPRETATION_PRESENTED_AS_FACT)


def test_an_interpretation_asserting_a_wrong_placement_contradicts_the_chart(
    judge: Judge, world: World
) -> None:
    result = judge(
        _interp(
            world,
            "Kuja dosha, with Mars in the seventh house, is traditionally read as challenging for marriage.",
            "ASTRO_DOSHA",
        )
    )
    assert_status(result, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)
    right = judge(
        _interp(
            world,
            "Kuja dosha, with Mars in the first house, is traditionally read as challenging for marriage.",
            "ASTRO_DOSHA",
        )
    )
    assert_status(right, S.VERIFIED)


def test_astrology_source_conflicts_are_not_merged(judge: Judge, world: World) -> None:
    merged = judge(
        _interp(
            world,
            "Raja yoga is traditionally read as supportive of career.",
            "ASTRO_RAJA",
            "ASTRO_PHAL",
        )
    )
    assert_status(merged, S.CONFLICTING_EVIDENCE, R.CONFLICTING_PROFILES_MERGED)
    unnamed = judge(
        _interp(world, "Raja yoga is traditionally read as supportive of career.", "ASTRO_RAJA")
    )
    assert_status(unnamed, S.CONFLICTING_EVIDENCE, R.CONFLICT_PROFILE_NOT_NAMED)
    named = judge(
        _interp(
            world, "According to BPHS, Raja yoga is read as supportive of career.", "ASTRO_RAJA"
        )
    )
    assert_status(named, S.VERIFIED)


def test_a_single_rule_ambiguity_group_is_not_a_source_conflict(judge: Judge, world: World) -> None:
    result = judge(
        _interp(world, "Sunapha yoga is traditionally read as context dependent.", "ASTRO_MIXED")
    )
    assert_status(result, S.VERIFIED)
    assert not world.item("ASTRO_MIXED").conflict_ids


# -- references ----------------------------------------------------------------------------------


def test_an_invalid_rule_reference_is_rejected(judge: Judge, world: World) -> None:
    claim = _interp(
        world, "Kuja dosha is traditionally read as challenging for marriage.", "ASTRO_DOSHA"
    )
    ref = claim.references[0].model_copy(update={"evidence_id": "ASTRO_NO_SUCH_RULE"})
    result = judge(claim.model_copy(update={"references": (ref,)}))
    assert_status(result, S.INVALID_REFERENCE, R.EVIDENCE_NOT_FOUND)


# -- policy --------------------------------------------------------------------------------------


def test_a_lifespan_claim_is_policy_blocked(judge: Judge, world: World) -> None:
    result = judge(
        _fact(world, "Saturn in the tenth house shows a short lifespan.", "astro.planet.saturn")
    )
    assert_status(result, S.POLICY_BLOCKED, R.PROHIBITED_CATEGORY)


def test_a_death_timing_claim_is_policy_blocked(judge: Judge, world: World) -> None:
    for text in (
        "Death will occur at age 60 during the Saturn period.",
        "In the Saturn dasha the native will die.",
        "Saturn shows when death comes, before age 70.",
    ):
        assert_status(
            judge(_fact(world, text, "astro.planet.saturn")),
            S.POLICY_BLOCKED,
            R.PROHIBITED_CATEGORY,
        )


def test_a_non_prohibited_high_impact_topic_is_not_blocked_by_verification(
    judge: Judge, world: World
) -> None:
    # Astrology keeps its own policy: marriage and wealth are interpreted with a disclaimer, which
    # is the agent's concern. Verification neither widens nor narrows it.
    result = judge(
        _interp(
            world, "Kuja dosha is traditionally read as challenging for marriage.", "ASTRO_DOSHA"
        )
    )
    assert result.status is S.VERIFIED
