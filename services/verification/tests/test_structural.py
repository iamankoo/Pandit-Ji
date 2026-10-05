"""Structural verification: references, bundles, versions, provenance, forgery (Phase 16)."""

from __future__ import annotations

from conftest import Judge, assert_status
from helpers import World, make_astro_bundle, make_claim, make_response
from pandit_contracts.agent import (
    ClaimType,
    Domain,
    EvidenceReference,
    NarrationSection,
    ReferenceKind,
    VerificationState,
)
from pandit_contracts.verification import ReasonCode as R
from pandit_contracts.verification import VerificationStatus as S

from pandit_verification import TrustedEvidence, Verifier, VerifierConfig, verifier_identity

OK_TEXT = "Mars is placed in Aries in the first house."


def _astro(world: World, cid: str = "C1", text: str = OK_TEXT, **kw: object):
    return make_claim(world, cid, text, ClaimType.CALCULATION_FACT, ["astro.planet.mars"], **kw)


def test_a_valid_claim_is_verified_by_the_phase_16_verifier(judge: Judge, world: World) -> None:
    result = judge(_astro(world))
    assert_status(result, S.VERIFIED, R.SUPPORTED)
    assert result.verified_by == verifier_identity()
    assert result.verifier_version
    assert result.provenance.bundle_refs == (world.astro_ref,)
    assert result.provenance.version_refs == ("PANDIT_JI_VEDIC@1.0.0",)
    assert result.claim_text_hash and len(result.claim_text_hash) == 64
    assert "text_grounding" in result.checks_run and "reference_resolution" in result.checks_run


def test_b_a_missing_fact_is_an_invalid_reference(judge: Judge, world: World) -> None:
    claim = make_claim(
        world, "C1", OK_TEXT, ClaimType.CALCULATION_FACT, ["astro.planet.mars"]
    ).model_copy(
        update={
            "references": (
                EvidenceReference(
                    evidence_id="astro.planet.pluto",
                    domain=Domain.ASTROLOGY,
                    kind=ReferenceKind.FACT,
                    bundle_ref=world.astro_ref,
                ),
            )
        }
    )
    assert_status(judge(claim), S.INVALID_REFERENCE, R.EVIDENCE_NOT_FOUND)


def test_c_a_missing_rule_is_an_invalid_reference(judge: Judge, world: World) -> None:
    claim = make_claim(
        world,
        "C1",
        "Tradition reads this as supportive.",
        ClaimType.TRADITIONAL_INTERPRETATION,
        ["ASTRO_MIXED"],
    ).model_copy(
        update={
            "references": (
                EvidenceReference(
                    evidence_id="ASTRO_INVENTED",
                    domain=Domain.ASTROLOGY,
                    kind=ReferenceKind.RULE,
                    bundle_ref=world.astro_ref,
                ),
            )
        }
    )
    assert_status(judge(claim), S.INVALID_REFERENCE, R.EVIDENCE_NOT_FOUND)


def test_d_a_malformed_evidence_id_is_invalid(judge: Judge, world: World) -> None:
    ref = EvidenceReference.model_construct(
        evidence_id="../etc/passwd",
        domain=Domain.ASTROLOGY,
        kind=ReferenceKind.FACT,
        bundle_ref=world.astro_ref,
    )
    claim = _astro(world).model_copy(update={"references": (ref,)})
    assert_status(judge(claim), S.INVALID_REFERENCE, R.MALFORMED_CLAIM)


def test_e_a_wrong_bundle_id_is_invalid(judge: Judge, world: World) -> None:
    claim = _astro(world)
    bad = claim.references[0].model_copy(update={"bundle_ref": "f" * 64})
    assert_status(
        judge(claim.model_copy(update={"references": (bad,)})),
        S.INVALID_REFERENCE,
        R.BUNDLE_MISMATCH,
    )


def test_e2_an_id_taken_from_another_bundle_is_invalid(judge: Judge, world: World) -> None:
    claim = _astro(world)
    swapped = claim.references[0].model_copy(update={"bundle_ref": world.palm_ref})
    result = judge(claim.model_copy(update={"references": (swapped,)}))
    assert result.status is S.INVALID_REFERENCE  # a palm bundle for an astrology claim


def test_f_a_wrong_domain_is_invalid(judge: Judge, world: World) -> None:
    claim = make_claim(
        world,
        "C1",
        "The right hand was observed.",
        ClaimType.OBSERVED_FEATURE,
        [world.palm.ids["hand"]],
    )
    # the same palm evidence presented as an astrology claim
    ref = claim.references[0].model_copy(update={"domain": Domain.ASTROLOGY})
    forged = claim.model_copy(update={"domain": Domain.ASTROLOGY, "references": (ref,)})
    assert_status(judge(forged), S.INVALID_REFERENCE, R.DOMAIN_MISMATCH)


def test_f2_a_reference_kind_that_the_evidence_does_not_have_is_invalid(
    judge: Judge, world: World
) -> None:
    claim = _astro(world)
    ref = claim.references[0].model_copy(update={"kind": ReferenceKind.RULE})
    assert_status(
        judge(claim.model_copy(update={"references": (ref,)})),
        S.INVALID_REFERENCE,
        R.REFERENCE_KIND_MISMATCH,
    )


def test_g_a_wrong_knowledge_version_is_invalid(judge: Judge, world: World) -> None:
    claim = _astro(world, version_refs=("KV-deadbeefdeadbeef",))
    assert_status(judge(claim), S.INVALID_REFERENCE, R.KNOWLEDGE_VERSION_MISMATCH)


def test_g2_a_knowledge_version_outside_the_pinned_set_is_invalid(
    judge: Judge, world: World
) -> None:
    config = VerifierConfig(expected_knowledge_versions=frozenset({"KV-other"}))
    assert_status(judge(_astro(world), config), S.INVALID_REFERENCE, R.KNOWLEDGE_VERSION_MISMATCH)


def test_h_a_wrong_rule_version_is_invalid(judge: Judge, world: World) -> None:
    claim = make_claim(
        world,
        "C1",
        "Kuja dosha is traditionally read as challenging for marriage.",
        ClaimType.TRADITIONAL_INTERPRETATION,
        ["ASTRO_DOSHA"],
    )
    config = VerifierConfig(pinned_rule_versions={"ASTRO_DOSHA": "2"})
    assert_status(judge(claim, config), S.INVALID_REFERENCE, R.RULE_VERSION_MISMATCH)
    # the same claim without the pin verifies, so the pin was the cause
    assert_status(judge(claim), S.VERIFIED)


def test_s_a_forged_verified_by_is_blocked_and_never_trusted(judge: Judge, world: World) -> None:
    claim = _astro(world).model_copy(
        update={
            "verification": VerificationState.VERIFIED,
            "verified_by": "pandit-verification@0.2.0",
        }
    )
    result = judge(claim)
    assert_status(result, S.POLICY_BLOCKED, R.FORGED_VERIFICATION)
    assert result.verified_by is None


def test_s2_an_unverified_claim_with_only_a_verified_by_string_is_blocked(
    judge: Judge, world: World
) -> None:
    claim = _astro(world).model_copy(update={"verified_by": "anything"})
    assert_status(judge(claim), S.POLICY_BLOCKED, R.FORGED_VERIFICATION)


def test_r_a_response_the_agent_marked_verified_is_flagged_and_regenerated(
    world: World,
) -> None:
    response = make_response(_astro(world)).model_copy(
        update={"verification": VerificationState.VERIFIED, "verified_by": "agent"}
    )
    report = world.verifier().verify(response)
    assert report.trace.input_forgery_detected is True
    assert report.release_action.value == "REGENERATE"


def test_t_forged_provenance_is_invalid(judge: Judge, world: World) -> None:
    profile = make_claim(
        world,
        "C1",
        "Tradition reads this as indicating ambition.",
        ClaimType.TRADITIONAL_INTERPRETATION,
        [world.palm.ids["trig"]],
        source_profiles=("PALM_FAKE_PROFILE",),
    )
    assert_status(judge(profile), S.INVALID_REFERENCE, R.PROVENANCE_MISMATCH)
    location = _astro(world, source_locations=("a made-up page",))
    assert_status(judge(location), S.INVALID_REFERENCE, R.PROVENANCE_MISMATCH)


def test_t2_an_overstated_confidence_is_invalid(judge: Judge, world: World) -> None:
    claim = make_claim(
        world,
        "C1",
        "The right hand was observed.",
        ClaimType.OBSERVED_FEATURE,
        [world.palm.ids["hand"]],
        min_confidence_bp=10000,
    )
    assert_status(judge(claim), S.INVALID_REFERENCE, R.PROVENANCE_MISMATCH)
    honest = make_claim(
        world,
        "C1",
        "The right hand was observed.",
        ClaimType.OBSERVED_FEATURE,
        [world.palm.ids["hand"]],
    )
    assert_status(judge(honest), S.VERIFIED)


def test_a_non_limitation_claim_without_a_reference_is_invalid(world: World) -> None:
    claim = _astro(world).model_copy(update={"references": ()})  # bypasses the claim contract
    section = NarrationSection.model_construct(heading="h", claims=(claim,))
    response = make_response(_astro(world)).model_copy(update={"sections": (section,)})
    result = world.verifier().verify(response).claims[0]
    assert_status(result, S.INVALID_REFERENCE, R.MISSING_REFERENCE)


def test_a_tampered_palm_bundle_makes_its_claims_invalid(world: World) -> None:
    tampered = world.palm.bundle.model_copy(update={"production_ready": True})
    evidence = TrustedEvidence().add_palm(tampered)
    claim = make_claim(
        world,
        "C1",
        "The right hand was observed.",
        ClaimType.OBSERVED_FEATURE,
        [world.palm.ids["hand"]],
    ).model_copy(update={})
    result = Verifier(evidence).verify(make_response(claim)).claims[0]
    # the tampered bundle has a different identity, so the reference no longer resolves, and
    # presenting the tampered bundle under its own (now wrong) hash reports the integrity failure
    assert result.status is S.INVALID_REFERENCE
    bundle = next(iter(evidence.bundles.values()))
    assert not bundle.ok and "bundle_hash" in bundle.problems[0]
    swapped = claim.references[0].model_copy(update={"bundle_ref": bundle.bundle_ref})
    again = Verifier(evidence).verify(
        make_response(claim.model_copy(update={"references": (swapped,)}))
    )
    assert_status(again.claims[0], S.INVALID_REFERENCE, R.BUNDLE_INTEGRITY_FAILURE)


def test_a_tampered_astrology_bundle_is_untrusted(world: World) -> None:
    sealed = make_astro_bundle()
    tampered = sealed.model_copy(update={"chart": sealed.chart.model_copy(update={})})
    assert TrustedEvidence().add_astrology(tampered).bundle(tampered.bundle_hash).ok  # control
    other = make_astro_bundle(mars_sign="leo")
    forged = other.model_copy(update={"bundle_hash": sealed.bundle_hash})
    evidence = TrustedEvidence().add_astrology(forged)
    bundle = evidence.bundle(forged.bundle_hash)
    assert bundle is not None and not bundle.ok
    claim = _astro(world)
    result = Verifier(evidence).verify(make_response(claim)).claims[0]
    assert_status(result, S.INVALID_REFERENCE, R.BUNDLE_INTEGRITY_FAILURE)


def test_a_ruleset_hash_mismatch_is_invalid(judge: Judge, world: World) -> None:
    config = VerifierConfig(expected_ruleset_hashes=frozenset({"0" * 64}))
    assert_status(judge(_astro(world), config), S.INVALID_REFERENCE, R.RULESET_HASH_MISMATCH)
    pinned = VerifierConfig(
        expected_ruleset_hashes=frozenset({world.astro.versions.ruleset_content_hash})
    )
    assert_status(judge(_astro(world), pinned), S.VERIFIED)


def test_an_independent_recomputation_that_disagrees_untrusts_the_bundle(world: World) -> None:
    evidence = TrustedEvidence().add_palm(world.palm.bundle, recompute=lambda fact_set, kv: ())
    bundle = evidence.bundle(world.palm_ref)
    assert bundle is not None and not bundle.ok
    assert "not reproducible" in bundle.problems[0]
    crashing = TrustedEvidence().add_palm(
        world.palm.bundle, recompute=lambda fact_set, kv: (_ for _ in ()).throw(RuntimeError("x"))
    )
    again = crashing.bundle(world.palm_ref)
    assert again is not None and not again.ok


def test_a_reproducing_recomputation_keeps_the_bundle_trusted(world: World) -> None:
    rules = world.palm.bundle.rule_evaluations
    evidence = TrustedEvidence().add_palm(world.palm.bundle, recompute=lambda fact_set, kv: rules)
    bundle = evidence.bundle(world.palm_ref)
    assert bundle is not None and bundle.ok
    astro = TrustedEvidence().add_astrology(world.astro, recompute=lambda: world.astro)
    assert astro.bundle(world.astro_ref).ok  # type: ignore[union-attr]


def test_evidence_that_was_never_supplied_is_unverifiable_not_invalid(world: World) -> None:
    only_astro = TrustedEvidence().add_astrology(world.astro)
    claim = make_claim(
        world,
        "C1",
        "The right hand was observed.",
        ClaimType.OBSERVED_FEATURE,
        [world.palm.ids["hand"]],
    )
    result = Verifier(only_astro).verify(make_response(claim)).claims[0]
    assert_status(result, S.UNVERIFIABLE, R.EVIDENCE_UNAVAILABLE)


def test_the_verifier_resolves_evidence_itself_and_ignores_agent_text(
    judge: Judge, world: World
) -> None:
    # The claim cannot carry evidence: only ids. The same ids give the same result however the
    # claim text describes the evidence.
    ok = judge(_astro(world))
    assert ok.status is S.VERIFIED
    liar = judge(_astro(world, text="Mars is placed in Leo."))
    assert_status(liar, S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE)
