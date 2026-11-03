"""Trusted-bundle registration (Phase 16 composition) and the regeneration loop.

The release behaviour under test is the verifier's: wrong, blocked or invalid claims -> REGENERATE;
unverifiable or insufficient claims -> strip. The loop is exercised against the real agent and the
scripted language-model double, with a controlled verifier so that every one of the seven Phase 16
statuses and every release action can be driven deterministically.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import PROFILE, make_container
from llm_double import CAREER_RULE, GOOD_TEXT, claim, narration, scripted_llm
from pandit_agent.orchestration import AgentConfig
from pandit_contracts.agent import AgentRequest, Domain
from pandit_contracts.domain import DomainStatus, LifeDomain
from pandit_contracts.llm import LLMLanguage
from pandit_contracts.verification import ReleaseAction, VerificationStatus
from pandit_verification import TrustedEvidence

from pandit_server.compose import chat as pipeline
from pandit_server.compose.trust import PinnedMethodology, TrustError, register_domain_result

S = VerificationStatus
SECOND_TEXT = "Career is traditionally linked with the tenth house of the chart."


def _kundli(year: int, month: int, day: int, hour: int) -> dict[str, Any]:
    from pandit_astro_engine import KundliCalculationService
    from pandit_astro_engine.models import (
        AstronomicalCalculationRequest,
        LocalDateTimeInput,
        Location,
    )

    return (
        KundliCalculationService()
        .calculate(
            AstronomicalCalculationRequest(
                local_datetime=LocalDateTimeInput(
                    year=year, month=month, day=day, hour=hour, minute=0, timezone="Asia/Kolkata"
                ),
                location=Location(latitude=28.6139, longitude=77.2090),
            )
        )
        .model_dump(mode="json")
    )


@pytest.fixture(scope="module")
def kundli() -> dict[str, Any]:
    return _kundli(1990, 6, 15, 10)


@pytest.fixture(scope="module")
def kundli_b() -> dict[str, Any]:
    return _kundli(1975, 11, 2, 21)


def _evidence(
    kundli: dict[str, Any], domain: LifeDomain = LifeDomain.CAREER, adult: bool | None = True
) -> pipeline.Evidence:
    return pipeline.build_evidence(
        kundli_json=kundli,
        dasha_json=None,
        message="x",
        adult_confirmed=adult,
        analysis_id="t1",
        forced_domain=domain,
    )


# ---- trusted-bundle registration ----------------------------------------------------------------


def test_a_valid_result_is_registered_with_exactly_its_own_evidence(kundli: dict[str, Any]) -> None:
    ev = _evidence(kundli)
    result = ev.domain_result
    assert result is not None and result.status is DomainStatus.EVALUATED
    bundle = ev.trusted.bundles[result.result_hash]
    withheld = {r.rule_id for r in result.rules if r.status.value == "POLICY_BLOCKED"}
    assert (
        set(bundle.items) == result.evidence_ids - withheld
    )  # a policy-withheld rule is not citable
    assert bundle.ok and bundle.knowledge_version == result.versions.knowledge_version
    assert bundle.ruleset_hash == result.versions.ruleset_hash


def test_a_tampered_result_is_refused(kundli: dict[str, Any]) -> None:
    result = _evidence(kundli).domain_result
    assert result is not None
    tampered = result.model_copy(
        update={"status": DomainStatus.NOT_EVALUABLE}
    )  # bypasses validation
    with pytest.raises(TrustError) as caught:
        register_domain_result(TrustedEvidence(), tampered, pipeline.pinned_methodology())
    assert caught.value.code == "result_hash_mismatch"


def test_version_mismatches_are_refused(kundli: dict[str, Any]) -> None:
    result = _evidence(kundli).domain_result
    assert result is not None
    pinned = pipeline.pinned_methodology()
    with pytest.raises(TrustError, match="knowledge_version_mismatch"):
        register_domain_result(
            TrustedEvidence(), result, PinnedMethodology("KV-0000000000000000", pinned.ruleset_hash)
        )
    with pytest.raises(TrustError, match="ruleset_hash_mismatch"):
        register_domain_result(
            TrustedEvidence(), result, PinnedMethodology(pinned.knowledge_version, "0" * 64)
        )


def test_a_result_cannot_be_registered_twice(kundli: dict[str, Any]) -> None:
    ev = _evidence(kundli)
    with pytest.raises(TrustError, match="bundle_already_registered"):
        register_domain_result(ev.trusted, ev.domain_result, pipeline.pinned_methodology())  # type: ignore[arg-type]


def test_policy_withheld_rules_are_never_citable(kundli: dict[str, Any]) -> None:
    ev = _evidence(kundli, LifeDomain.CHILDREN)
    result = ev.domain_result
    assert result is not None
    blocked = {r.rule_id for r in result.rules if r.status.value == "POLICY_BLOCKED"}
    assert blocked
    items = set(ev.trusted.bundles[result.result_hash].items)
    assert not blocked & items


def test_the_withheld_transit_records_register_as_not_evaluable_with_no_tags(
    kundli: dict[str, Any],
) -> None:
    ev = _evidence(kundli)
    items = ev.trusted.bundles[ev.domain_result.result_hash].items  # type: ignore[union-attr]
    records = [i for rid, i in items.items() if "PXVI31" in rid]
    assert len(records) == 1 and records[0].status == "NOT_EVALUABLE" and records[0].tags == ()


def _verify(trusted: TrustedEvidence, texts: list[str], ids: list[str]) -> Any:

    factory, _ = scripted_llm([narration(*[claim(t, ids) for t in texts])])
    return trusted, factory


def test_an_unregistered_domain_result_is_unverifiable_never_verified(
    kundli: dict[str, Any],
) -> None:
    ev = _evidence(kundli)
    bare = TrustedEvidence().add_astrology(ev.bundle)  # the domain result is NOT registered
    outcome = _run(ev, [[claim(GOOD_TEXT, [CAREER_RULE])]], trusted=bare)
    assert outcome.claims == [] and outcome.status == "failed"
    assert outcome.attempts and all(S.VERIFIED.value not in a.counts for a in outcome.attempts)


def test_evidence_of_another_chart_cannot_verify_this_charts_claim(
    kundli: dict[str, Any], kundli_b: dict[str, Any]
) -> None:
    ev_a, ev_b = _evidence(kundli), _evidence(kundli_b)
    assert ev_a.domain_result.result_hash != ev_b.domain_result.result_hash  # type: ignore[union-attr]
    # a narration produced against A, verified with only B's trusted evidence
    outcome = _run(ev_a, [[claim(GOOD_TEXT, [CAREER_RULE])]], trusted=ev_b.trusted)
    assert outcome.claims == []


# ---- the regeneration loop ----------------------------------------------------------------------


class _Fake:
    """A controlled verifier: each attempt is (statuses of the model's claims, release action)."""

    plan: list[tuple[list[S], ReleaseAction]] = []
    calls = 0

    def __init__(self, trusted: Any, config: Any = None) -> None:  # noqa: D401
        pass

    def verify(self, narration_: Any) -> Any:
        statuses, action = _Fake.plan[min(_Fake.calls, len(_Fake.plan) - 1)]
        _Fake.calls += 1
        claims = []
        index = 0
        for section in narration_.sections:
            for c in section.claims:
                if c.claim_type.value == "LIMITATION" or index >= len(statuses):
                    status = S.UNVERIFIABLE
                else:
                    status = statuses[index]
                    index += 1
                claims.append(
                    SimpleNamespace(
                        claim_id=c.claim_id,
                        status=status,
                        verified_by="fake-verifier" if status is S.VERIFIED else None,
                        claim_text_hash=hashlib.sha256(c.text.encode()).hexdigest(),
                    )
                )
        verified = [c.claim_id for c in claims if c.status is S.VERIFIED]
        return SimpleNamespace(
            claims=claims,
            release_action=action,
            report_hash="r" * 64,
            verified_claim_ids=verified,
        )


def _run(
    ev: pipeline.Evidence,
    scripts: list[list[dict[str, Any]]],
    *,
    trusted: TrustedEvidence | None = None,
    max_regen: int = 2,
    fake: list[tuple[list[S], ReleaseAction]] | None = None,
    monkeypatch: Any = None,
) -> pipeline.ChatOutcome:
    factory, _ = scripted_llm([narration(*c) for c in scripts])
    if trusted is not None:
        ev = pipeline.Evidence(ev.bundle, ev.domain_result, trusted, ev.tools, ev.life_domain)
    saved = pipeline.Verifier
    if fake is not None:
        _Fake.plan, _Fake.calls = fake, 0
        pipeline.Verifier = _Fake  # type: ignore[assignment,misc]
    try:
        return pipeline.run_verified_chat(
            llm=factory(),
            evidence=ev,
            request=AgentRequest(
                request_id="t",
                language=LLMLanguage.EN,
                user_text="Tell me about my career",
                domain=Domain.ASTROLOGY,
            ),
            max_regenerations=max_regen,
            config=AgentConfig(max_evidence_items=36),
        )
    finally:
        pipeline.Verifier = saved  # type: ignore[assignment,misc]


A = claim(GOOD_TEXT, [CAREER_RULE])
B = claim(SECOND_TEXT, [CAREER_RULE])


def test_all_verified_is_approved_in_one_attempt(kundli: dict[str, Any]) -> None:
    out = _run(
        _evidence(kundli), [[A, B]], fake=[([S.VERIFIED, S.VERIFIED], ReleaseAction.APPROVE)]
    )
    assert out.status in {"completed", "degraded"} and [c["text"] for c in out.claims] == [
        GOOD_TEXT,
        SECOND_TEXT,
    ]
    assert len(out.attempts) == 1 and out.final_action == "APPROVE"


@pytest.mark.parametrize("stripped", [S.UNVERIFIABLE, S.INSUFFICIENT_EVIDENCE])
def test_unverifiable_and_insufficient_claims_are_stripped_not_regenerated(
    kundli: dict[str, Any], stripped: S
) -> None:
    out = _run(
        _evidence(kundli),
        [[A, B]],
        fake=[([S.VERIFIED, stripped], ReleaseAction.RELEASE_VERIFIED_ONLY)],
    )
    assert [c["text"] for c in out.claims] == [GOOD_TEXT]
    assert len(out.attempts) == 1 and out.status == "degraded"  # no regeneration for a strip


@pytest.mark.parametrize(
    "wrong", [S.UNSUPPORTED, S.INVALID_REFERENCE, S.CONFLICTING_EVIDENCE, S.POLICY_BLOCKED]
)
def test_wrong_blocked_or_invalid_claims_regenerate_and_are_never_released(
    kundli: dict[str, Any], wrong: S
) -> None:
    out = _run(
        _evidence(kundli),
        [[A, B], [A, B]],
        fake=[
            ([S.VERIFIED, wrong], ReleaseAction.REGENERATE),
            ([S.VERIFIED, S.VERIFIED], ReleaseAction.APPROVE),
        ],
    )
    assert len(out.attempts) == 2 and out.attempts[0].action == "REGENERATE"
    assert [c["text"] for c in out.claims] == [
        GOOD_TEXT,
        SECOND_TEXT,
    ]  # verified claims are kept once


def test_a_claim_that_never_verifies_is_never_released_and_attempts_are_bounded(
    kundli: dict[str, Any],
) -> None:
    out = _run(
        _evidence(kundli),
        [[A, B]] * 5,
        max_regen=2,
        fake=[([S.VERIFIED, S.UNSUPPORTED], ReleaseAction.REGENERATE)],
    )
    assert len(out.attempts) == 3  # 1 + max_regenerations, then it stops
    assert [c["text"] for c in out.claims] == [
        GOOD_TEXT
    ]  # deduplicated; the wrong claim never leaves
    assert out.status == "degraded"


def test_nothing_verified_after_exhaustion_is_a_typed_failure(kundli: dict[str, Any]) -> None:
    out = _run(
        _evidence(kundli),
        [[A]] * 5,
        max_regen=1,
        fake=[([S.UNSUPPORTED], ReleaseAction.REGENERATE)],
    )
    assert out.status == "failed" and out.error_code == "no_verified_content" and out.claims == []
    assert len(out.attempts) == 2


def test_zero_regenerations_means_a_single_attempt(kundli: dict[str, Any]) -> None:
    out = _run(
        _evidence(kundli),
        [[A]] * 3,
        max_regen=0,
        fake=[([S.UNSUPPORTED], ReleaseAction.REGENERATE)],
    )
    assert len(out.attempts) == 1 and out.claims == []


def test_nothing_to_verify_stops_immediately(kundli: dict[str, Any]) -> None:
    out = _run(_evidence(kundli), [[A]] * 3, fake=[([], ReleaseAction.NOTHING_TO_VERIFY)])
    assert len(out.attempts) == 1 and out.final_action == "NOTHING_TO_VERIFY" and out.claims == []


def test_the_policy_boundary_holds_on_every_attempt(kundli: dict[str, Any]) -> None:
    """A policy refusal on any attempt ends the loop with nothing released."""
    ev = _evidence(kundli, LifeDomain.MARRIAGE, adult=None)  # adulthood not confirmed
    factory, runtime = scripted_llm([narration(A)] * 3)
    out = pipeline.run_verified_chat(
        llm=factory(),
        evidence=ev,
        request=AgentRequest(
            request_id="p",
            language=LLMLanguage.EN,
            user_text="Tell me about my marriage",
            domain=Domain.ASTROLOGY,
        ),
        max_regenerations=2,
        config=AgentConfig(max_evidence_items=36),
    )
    assert out.status == "refused" and out.claims == [] and runtime.calls == []


def test_the_real_verifier_drives_a_real_end_to_end_release(kundli: dict[str, Any]) -> None:
    out = _run(_evidence(kundli), [[A]])
    assert [c["text"] for c in out.claims] == [GOOD_TEXT]
    assert (
        out.final_action == "RELEASE_VERIFIED_ONLY" and out.attempts[0].counts.get("VERIFIED") == 1
    )
    assert all(c["verified_by"] for c in out.claims)


def test_attempt_records_hold_statuses_and_counts_never_text(kundli: dict[str, Any]) -> None:
    out = _run(_evidence(kundli), [[A]])
    assert GOOD_TEXT not in str(out.attempts) and "tenth" not in str(out.attempts)
    assert set(out.attempts[0].counts) <= {s.value for s in S}


def test_profile_fixture_is_the_documented_one() -> None:
    assert PROFILE["timezone"] == "Asia/Kolkata" and make_container is not None
