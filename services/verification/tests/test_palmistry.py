"""Palmistry verification over a real (synthetic) PalmEvidenceBundle (Phase 16)."""

from __future__ import annotations

from conftest import Judge, assert_status
from helpers import World, flags, make_claim, make_response
from pandit_contracts.agent import ClaimType, UncertaintyFlag
from pandit_contracts.verification import ReasonCode as R
from pandit_contracts.verification import VerificationStatus as S

from pandit_verification import TrustedEvidence, Verifier, VerifierConfig

OBS = ClaimType.OBSERVED_FEATURE
DER = ClaimType.DERIVED_FEATURE
INT = ClaimType.TRADITIONAL_INTERPRETATION
LIM = ClaimType.LIMITATION


def _claim(world: World, text: str, ctype: ClaimType, *ids: str, **kw: object):
    return make_claim(world, "C1", text, ctype, [world.palm.ids.get(i, i) for i in ids], **kw)


# -- facts: OBSERVED and DERIVED -----------------------------------------------------------------


def test_an_observed_fact_is_verified(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "The right hand was observed.", OBS, "hand"))
    assert_status(result, S.VERIFIED, R.SUPPORTED)
    assert result.provenance.version_refs == ("KV-a21c2c040abe9663",)
    # the verifier reports the uncertainty it computed, whatever the claim said
    assert UncertaintyFlag.UNCALIBRATED_CONFIDENCE in result.uncertainty
    assert UncertaintyFlag.BUNDLE_NOT_PRODUCTION_READY in result.uncertainty
    assert R.UNCERTAINTY_UNDERSTATED in {r.code for r in result.reasons}


def test_a_claim_that_states_its_uncertainty_is_not_flagged_as_understating(
    judge: Judge, world: World
) -> None:
    claim = _claim(
        world,
        "The right hand was observed.",
        OBS,
        "hand",
        uncertainty=flags("UNCALIBRATED_CONFIDENCE", "BUNDLE_NOT_PRODUCTION_READY"),
    )
    result = judge(claim)
    assert_status(result, S.VERIFIED)
    assert R.UNCERTAINTY_UNDERSTATED not in {r.code for r in result.reasons}


def test_a_derived_fact_is_verified_as_derived(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "The mount of Jupiter was derived from the hand landmarks.", DER, "jupiter")
    )
    assert_status(result, S.VERIFIED)


def test_k_a_derived_fact_cannot_be_claimed_as_an_observed_feature(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "The mount of Jupiter was observed.", OBS, "jupiter"))
    assert_status(result, S.UNSUPPORTED, R.SEMANTIC_CLASS_MISMATCH)


def test_k2_an_observed_fact_cannot_be_claimed_as_derived(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "The right hand was derived.", DER, "hand"))
    assert_status(result, S.UNSUPPORTED, R.SEMANTIC_CLASS_MISMATCH)


def test_k3_a_derived_fact_described_as_observed_in_the_text_is_misrepresented(
    judge: Judge, world: World
) -> None:
    result = judge(
        _claim(world, "The mount of Jupiter was directly observed in the image.", DER, "jupiter")
    )
    assert_status(result, S.UNSUPPORTED, R.CLASS_MISREPRESENTED)


def test_k4_an_observation_described_as_derived_in_the_text_is_misrepresented(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "The right hand was calculated from other facts.", OBS, "hand"))
    assert_status(result, S.UNSUPPORTED, R.CLASS_MISREPRESENTED)


def test_l_a_not_evaluable_fact_cannot_support_a_definitive_claim(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "The life line role was derived.", DER, "life"))
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.EVIDENCE_NOT_EVALUABLE)
    assert UncertaintyFlag.NOT_EVALUABLE in result.uncertainty


def test_m_uncertain_evidence_cannot_verify(judge: Judge, world: World) -> None:
    partial = judge(_claim(world, "The heart line was observed.", OBS, "heart"))
    assert_status(partial, S.INSUFFICIENT_EVIDENCE, R.EVIDENCE_NOT_VISIBLE)
    assert UncertaintyFlag.NOT_VISIBLE in partial.uncertainty


def test_m2_a_confidence_floor_is_enforced_when_configured(judge: Judge, world: World) -> None:
    claim = _claim(world, "The mount of Saturn was derived from the landmarks.", DER, "weak")
    assert_status(judge(claim), S.VERIFIED)  # no floor invented by default
    result = judge(claim, VerifierConfig(min_confidence_bp=5000))
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.CONFIDENCE_BELOW_THRESHOLD)


def test_m3_calibrated_confidence_can_be_required(judge: Judge, world: World) -> None:
    claim = _claim(world, "The right hand was observed.", OBS, "hand")
    result = judge(claim, VerifierConfig(require_calibrated_confidence=True))
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.CONFIDENCE_UNCALIBRATED)


def test_m4_production_readiness_can_be_required(judge: Judge, world: World) -> None:
    claim = _claim(world, "The right hand was observed.", OBS, "hand")
    result = judge(claim, VerifierConfig(require_production_ready=True))
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.BUNDLE_NOT_PRODUCTION_READY)


def test_a_fact_claim_with_the_wrong_hand_contradicts_the_evidence(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "The left hand was observed.", OBS, "hand"))
    assert_status(result, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)


def test_a_fact_claim_about_an_uncited_line_is_ungrounded(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "The head line was observed.", OBS, "hand"))
    assert_status(result, S.UNSUPPORTED, R.UNGROUNDED_ENTITY)


def test_a_fact_claim_naming_the_wrong_mount_contradicts_the_evidence(
    judge: Judge, world: World
) -> None:
    result = judge(
        _claim(world, "The mount of Venus was derived from the landmarks.", DER, "jupiter")
    )
    assert_status(result, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)


def test_a_fact_claim_with_no_recognised_palm_entity_is_unverifiable(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "A feature was observed.", OBS, "hand"))
    assert_status(result, S.UNVERIFIABLE, R.NO_CHECKABLE_CONTENT)


def test_a_fact_claim_with_an_unexplained_number_is_unsupported(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "The right hand was observed with 37 degrees.", OBS, "hand"))
    assert_status(result, S.UNSUPPORTED, R.UNGROUNDED_NUMBER)


def test_a_palm_fact_cannot_carry_a_judgement_or_a_life_topic(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "The right hand was observed and it is a good sign for career.", OBS, "hand")
    )
    assert_status(result, S.UNSUPPORTED, R.UNSUPPORTED_ASSERTION, R.TOPIC_NOT_IN_EVIDENCE)


# -- rules and interpretations -------------------------------------------------------------------


def test_a_triggered_rule_supports_a_framed_interpretation(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "One tradition reads this as indicating ambition.", INT, "trig"))
    assert_status(result, S.VERIFIED)
    assert result.rule_refs == ("PALMR_TRIG",)
    assert result.provenance.rule_versions == ("PALMR_TRIG@1",)
    assert result.provenance.source_ids == ("SRC-HERONALLEN-CHEIROSOPHY",)


def test_i_an_untriggered_rule_cannot_support_an_interpretation(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "One tradition reads this as indicating ambition.", INT, "nottrig")
    )
    assert_status(result, S.UNSUPPORTED, R.RULE_NOT_TRIGGERED)
    assert UncertaintyFlag.NOT_TRIGGERED in result.uncertainty


def test_a_not_evaluable_rule_is_insufficient_evidence(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "One tradition reads this as indicating ambition.", INT, "ne"))
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.RULE_NOT_EVALUABLE)


def test_j_a_rule_whose_required_fact_is_missing_is_not_verified(world: World) -> None:
    evidence = TrustedEvidence().add_palm(world.palm.bundle)
    item = evidence.bundle(world.palm_ref).items["PALMR_TRIG"]  # type: ignore[union-attr]
    item.missing_basis = ("PF-0000000000000000",)  # as if the bundle lacked a required fact
    claim = _claim(world, "One tradition reads this as indicating ambition.", INT, "trig")
    result = Verifier(evidence).verify(make_response(claim)).claims[0]
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.MISSING_REQUIRED_FACT)


def test_j2_a_rule_over_a_partial_fact_is_not_verified(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "One tradition reads this as indicating ambition.", INT, "on_partial")
    )
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.EVIDENCE_NOT_VISIBLE)


def test_j3_a_rule_over_a_not_evaluable_fact_is_not_verified(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "One tradition reads this as indicating ambition.", INT, "on_unevaluable")
    )
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.EVIDENCE_NOT_EVALUABLE)


def test_a_rule_without_a_fact_basis_is_not_verified(world: World) -> None:
    evidence = TrustedEvidence().add_palm(world.palm.bundle)
    item = evidence.bundle(world.palm_ref).items["PALMR_TRIG"]  # type: ignore[union-attr]
    item.fact_refs = ()
    claim = _claim(world, "One tradition reads this as indicating ambition.", INT, "trig")
    result = Verifier(evidence).verify(make_response(claim)).claims[0]
    assert_status(result, S.INSUFFICIENT_EVIDENCE, R.RULE_WITHOUT_FACT_BASIS)


def test_an_interpretation_must_rest_on_a_rule(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "One tradition reads this as indicating ambition.", INT, "hand"))
    assert_status(result, S.UNSUPPORTED, R.INTERPRETATION_WITHOUT_RULE)


def test_an_interpretation_presented_as_a_plain_fact_is_unsupported(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "You have strong ambition.", INT, "trig"))
    assert_status(result, S.UNSUPPORTED, R.INTERPRETATION_PRESENTED_AS_FACT)


def test_an_interpretation_naming_a_topic_the_rule_does_not_carry_is_unsupported(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "One tradition reads this as indicating wealth.", INT, "trig"))
    assert_status(result, S.UNSUPPORTED, R.TOPIC_NOT_IN_EVIDENCE)


def test_an_interpretation_that_reflects_no_cited_tag_is_unverifiable(
    judge: Judge, world: World
) -> None:
    result = judge(
        _claim(world, "One tradition reads something about this hand feature.", INT, "trig")
    )
    assert_status(result, S.UNVERIFIABLE, R.NO_CHECKABLE_CONTENT)


def test_palm_tags_carry_no_valence(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "One tradition reads this as a favourable sign of ambition.", INT, "trig")
    )
    assert_status(result, S.UNSUPPORTED, R.VALENCE_NOT_IN_EVIDENCE)


def test_an_interpretation_naming_the_wrong_hand_contradicts_the_rule(
    judge: Judge, world: World
) -> None:
    wrong = judge(
        _claim(
            world,
            "One tradition reads the right hand as showing inherited tendencies.",
            INT,
            "left_hand",
        )
    )
    assert_status(wrong, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)
    right = judge(
        _claim(
            world,
            "One tradition reads the left hand as showing inherited tendencies.",
            INT,
            "left_hand",
        )
    )
    assert_status(right, S.VERIFIED)


def test_certainty_is_never_supported(judge: Judge, world: World) -> None:
    result = judge(
        _claim(world, "Tradition says this ambition will definitely come true.", INT, "trig")
    )
    assert_status(result, S.UNSUPPORTED, R.OVERSTATED_CERTAINTY)


# -- source profiles -----------------------------------------------------------------------------


def test_n_conflicting_source_profiles_are_not_merged(judge: Judge, world: World) -> None:
    claim = _claim(
        world,
        "Tradition reads the right hand as altered and as developed.",
        INT,
        "benham",
        "cheiro",
    )
    result = judge(claim)
    assert_status(result, S.CONFLICTING_EVIDENCE, R.CONFLICTING_PROFILES_MERGED)
    assert UncertaintyFlag.CONFLICTING_PROFILES in result.uncertainty


def test_n2_a_conflicted_source_must_be_named(judge: Judge, world: World) -> None:
    unnamed = judge(
        _claim(
            world,
            "One tradition reads the right hand as showing how the map was altered.",
            INT,
            "benham",
        )
    )
    assert_status(unnamed, S.CONFLICTING_EVIDENCE, R.CONFLICT_PROFILE_NOT_NAMED)
    named = judge(
        _claim(
            world,
            "According to Benham, the right hand shows how the map was altered.",
            INT,
            "benham",
        )
    )
    assert_status(named, S.VERIFIED)
    assert UncertaintyFlag.CONFLICTING_PROFILES in named.uncertainty  # the conflict stays visible
    assert named.provenance.source_profiles == ("PALM_BE_HANDS_359",)


def test_n3_naming_the_wrong_source_does_not_satisfy_the_attribution(
    judge: Judge, world: World
) -> None:
    result = judge(
        _claim(
            world,
            "According to Cheiro, the right hand shows how the map was altered.",
            INT,
            "benham",
        )
    )
    assert_status(result, S.CONFLICTING_EVIDENCE, R.CONFLICT_PROFILE_NOT_NAMED)


def test_the_other_profile_can_be_verified_on_its_own_terms(judge: Judge, world: World) -> None:
    result = judge(
        _claim(
            world, "According to Cheiro, the right hand shows developed qualities.", INT, "cheiro"
        )
    )
    assert_status(result, S.VERIFIED)
    assert result.provenance.source_profiles == ("PALM_CH_LINES_PART1",)


# -- limitations ---------------------------------------------------------------------------------


def test_a_limitation_about_a_not_evaluable_fact_is_supported(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "The life line could not be evaluated.", LIM, "life"))
    assert_status(result, S.VERIFIED, R.LIMITATION_SUPPORTED)


def test_a_limitation_about_evidence_that_shows_no_gap_is_unsupported(
    judge: Judge, world: World
) -> None:
    result = judge(_claim(world, "The mount of Saturn could not be evaluated.", LIM, "hand"))
    assert_status(result, S.UNSUPPORTED, R.NO_LIMITATION_BASIS)


def test_a_limitation_about_a_conflicted_rule_is_supported(judge: Judge, world: World) -> None:
    result = judge(_claim(world, "Two sources disagree about the hands.", LIM, "benham"))
    assert_status(result, S.VERIFIED, R.LIMITATION_SUPPORTED)


def test_the_bundle_status_record_supports_a_not_ready_limitation(
    judge: Judge, world: World
) -> None:
    status_id = f"bundle.{world.palm.bundle.analysis_id}"
    claim = make_claim(world, "C1", "This reading is not production ready.", LIM, [status_id])
    assert_status(judge(claim), S.VERIFIED, R.LIMITATION_SUPPORTED)
