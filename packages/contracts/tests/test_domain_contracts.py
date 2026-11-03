"""Phase 17 life-domain contracts: taxonomy, one status vocabulary, no sex field, invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pandit_contracts.agent import EvidenceCapability
from pandit_contracts.domain import (
    EXTENSION_DOMAINS,
    PHASES_MD_DOMAINS,
    DomainAnalysisRequest,
    DomainAnalysisResult,
    DomainFact,
    DomainFactKind,
    DomainInputs,
    DomainInterpretation,
    DomainReason,
    DomainReasonRecord,
    DomainRuleKind,
    DomainRuleResult,
    DomainStatus,
    DomainSupport,
    DomainVersions,
    LifeDomain,
    PolicyClass,
    domain_result_hash,
    with_hash,
)
from pandit_contracts.verification import VerificationStatus

H = "a" * 64


def _versions() -> DomainVersions:
    return DomainVersions(
        knowledge_version="KV-0000000000000000",
        methodology_version="DOMAIN_METHODOLOGY_P17_1",
        ruleset_id="PANDIT_JI_DOMAIN_PHASE17",
        ruleset_version="1.0.0",
        ruleset_hash=H,
        evaluator_version="1.0.0",
    )


def _fact(domain: LifeDomain = LifeDomain.CAREER, **over: object) -> DomainFact:
    base: dict[str, object] = dict(
        fact_id="dom.career.house10.state",
        kind=DomainFactKind.HOUSE_STATE,
        domain=domain,
        mapping_id="MAP.CAREER.HOUSE.10.P11",
        subject="house:10",
        attributes=(("house", "10"), ("lord", "saturn")),
        chart_refs=("astro.lagna",),
        house_refs=(10,),
        source_profile="KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        source_location="Ch. 11 v. 2-13",
        support=DomainSupport.SOURCE_SUPPORTED,
    )
    base.update(over)
    return DomainFact(**base)  # type: ignore[arg-type]


def _rule(**over: object) -> DomainRuleResult:
    base: dict[str, object] = dict(
        rule_id="DOM_CAREER_HOUSE_10_P11",
        rule_version="1",
        kind=DomainRuleKind.HOUSE_RELEVANCE,
        status=DomainStatus.TRIGGERED,
        source_profile="KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        source_id="BPHS_SANTHANAM_1984",
        source_location="Ch. 11 v. 2-13",
        verification_level="IMAGE-TRANSLATION",
        support=DomainSupport.SOURCE_SUPPORTED,
        fact_refs=("dom.career.house10.state",),
        interpretation=DomainInterpretation(
            domain_tags=("career",), signification_tags=("career.house10.profession_livelihood",)
        ),
    )
    base.update(over)
    return DomainRuleResult(**base)  # type: ignore[arg-type]


def _result(**over: object) -> DomainAnalysisResult:
    fields: dict[str, object] = dict(
        analysis_id="a1",
        domain=LifeDomain.CAREER,
        parent_domain=None,
        support=DomainSupport.SOURCE_SUPPORTED,
        status=DomainStatus.EVALUATED,
        facts=(_fact(),),
        rules=(_rule(),),
        versions=_versions(),
    )
    fields.update(over)
    return with_hash(**fields)


# ---- taxonomy ---------------------------------------------------------------------------------


def test_the_27_phases_md_domains_are_exactly_the_roadmap_ones_in_order() -> None:
    assert [d.value for d in PHASES_MD_DOMAINS] == [
        "BIRTH", "PERSONALITY", "CHILDHOOD", "SCHOOL", "COLLEGE", "SUBJECTS", "EDUCATION",
        "CAREER", "JOB", "CORPORATE_LIFE", "BUSINESS", "STARTUP", "FINANCE", "WEALTH", "LOVE",
        "GF_BF", "RELATIONSHIP", "MARRIAGE", "SPOUSE", "FAMILY", "CHILDREN", "TRAVEL",
        "FOREIGN_TRAVEL", "FOREIGN_EDUCATION", "FOREIGN_SETTLEMENT", "PERSONAL_LIFE",
        "SPIRITUALITY",
    ]  # fmt: skip
    assert len(PHASES_MD_DOMAINS) == 27


def test_the_features_md_concepts_are_extensions_not_top_level_duplicates() -> None:
    assert {d.value for d in EXTENSION_DOMAINS} == {
        "PARENTS", "SIBLINGS", "INCOME", "INVESTMENTS", "ENTREPRENEURSHIP", "HIGHER_EDUCATION",
        "MAJOR_LIFE_TRANSITIONS", "GENERAL_LIFE_PATTERNS", "HEALTH",
    }  # fmt: skip
    assert set(PHASES_MD_DOMAINS).isdisjoint(EXTENSION_DOMAINS)
    assert len(LifeDomain) == 36


# ---- one status vocabulary --------------------------------------------------------------------


def test_the_domain_status_reuses_existing_names_and_adds_no_parallel_scheme() -> None:
    from_phase16 = {s.value for s in VerificationStatus}
    phase6 = {"TRIGGERED", "NOT_TRIGGERED", "CANCELLED", "PARTIALLY_CANCELLED", "NOT_EVALUABLE"}
    local = {"EVALUATED"}  # the only name that does not exist elsewhere: a successful analysis
    for status in DomainStatus:
        assert status.value in from_phase16 | phase6 | local, status
    assert {"INSUFFICIENT_EVIDENCE", "POLICY_BLOCKED", "CONFLICTING_EVIDENCE"} <= {
        s.value for s in DomainStatus
    }


def test_the_domain_status_can_never_be_verified() -> None:
    assert "VERIFIED" not in {s.value for s in DomainStatus}
    assert "VERIFIED" not in DomainAnalysisResult.model_fields


def test_the_agent_gains_only_the_additive_domain_capability() -> None:
    assert EvidenceCapability.ASTRO_DOMAIN.value == "ASTRO_DOMAIN"
    assert {c.value for c in EvidenceCapability} >= {"ASTRO_CHART", "ASTRO_RULES", "PALM_FACTS"}


# ---- the request: no sex, no inferred age -----------------------------------------------------


def test_the_request_has_no_sex_or_age_field_and_forbids_extras() -> None:
    fields = set(DomainAnalysisRequest.model_fields)
    for forbidden in ("sex", "gender", "age", "birth_date", "date_of_birth", "dob", "name"):
        assert forbidden not in fields
    with pytest.raises(ValidationError):
        DomainAnalysisRequest(analysis_id="a1", domain=LifeDomain.MARRIAGE, sex="F")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        DomainAnalysisRequest(analysis_id="a1", domain=LifeDomain.MARRIAGE, age=30)  # type: ignore[call-arg]


def test_adulthood_is_an_explicit_statement_never_a_default() -> None:
    request = DomainAnalysisRequest(analysis_id="a1", domain=LifeDomain.MARRIAGE)
    assert request.subject_adult_confirmed is None  # not confirmed unless the caller says so


def test_the_request_validates_ids_and_the_instant() -> None:
    with pytest.raises(ValidationError):
        DomainAnalysisRequest(analysis_id="bad id!", domain=LifeDomain.CAREER)
    with pytest.raises(ValidationError):
        DomainAnalysisRequest(analysis_id="a1", domain=LifeDomain.CAREER, as_of_utc="tomorrow")
    ok = DomainAnalysisRequest(
        analysis_id="a1", domain=LifeDomain.CAREER, as_of_utc="2026-09-21T12:00:00Z"
    )
    assert ok.as_of_utc == "2026-09-21T12:00:00Z"


# ---- facts and rule results -------------------------------------------------------------------


def test_a_fact_cannot_rest_on_a_not_evaluable_mapping() -> None:
    with pytest.raises(ValidationError):
        _fact(support=DomainSupport.NOT_EVALUABLE)


def test_fact_attributes_are_sorted_so_equal_inputs_give_equal_bytes() -> None:
    with pytest.raises(ValidationError):
        _fact(attributes=(("z", "1"), ("a", "2")))


def test_a_failed_rule_states_a_reason_and_a_triggered_one_does_not() -> None:
    with pytest.raises(ValidationError):
        _rule(status=DomainStatus.INSUFFICIENT_EVIDENCE)
    ok = _rule(
        status=DomainStatus.INSUFFICIENT_EVIDENCE,
        reason=DomainReason.MISSING_VARGA_EVIDENCE,
        interpretation=None,
        fact_refs=(),
    )
    assert ok.reason is DomainReason.MISSING_VARGA_EVIDENCE
    with pytest.raises(ValidationError):
        _rule(reason=DomainReason.MISSING_FACT)


def test_interpretation_tags_exist_only_on_a_triggered_rule() -> None:
    with pytest.raises(ValidationError):
        _rule(status=DomainStatus.NOT_TRIGGERED)


def test_a_policy_blocked_rule_exposes_no_tags_and_no_facts() -> None:
    with pytest.raises(ValidationError):
        _rule(status=DomainStatus.POLICY_BLOCKED, reason=DomainReason.POLICY_BLOCKED)
    blocked = _rule(
        status=DomainStatus.POLICY_BLOCKED,
        reason=DomainReason.SPOUSE_LONGEVITY_BLOCKED,
        interpretation=None,
        fact_refs=(),
    )
    assert blocked.interpretation is None and blocked.fact_refs == ()


def test_interpretation_tags_are_structured_not_prose() -> None:
    with pytest.raises(ValidationError):
        DomainInterpretation(domain_tags=("A Free Text Sentence.",))


# ---- the result ---------------------------------------------------------------------------------


def test_the_result_hash_covers_everything_except_itself_and_is_checked() -> None:
    result = _result()
    assert result.result_hash == domain_result_hash(result)
    other = _result(analysis_id="a2")
    assert other.result_hash != result.result_hash
    with pytest.raises(ValidationError):
        DomainAnalysisResult(**{**result.model_dump(), "result_hash": H})


def test_an_evaluated_analysis_needs_a_supported_domain_and_evidence() -> None:
    with pytest.raises(ValidationError):
        _result(support=DomainSupport.NOT_EVALUABLE)
    with pytest.raises(ValidationError):
        _result(facts=(), rules=())


def test_a_non_evaluated_analysis_states_its_reasons() -> None:
    with pytest.raises(ValidationError):
        _result(status=DomainStatus.NOT_EVALUABLE, facts=(), rules=())
    ok = _result(
        domain=LifeDomain.BIRTH,
        support=DomainSupport.NOT_EVALUABLE,
        status=DomainStatus.NOT_EVALUABLE,
        reasons=(DomainReasonRecord(code=DomainReason.UNDEFINED_DOMAIN),),
        facts=(),
        rules=(),
    )
    assert ok.status is DomainStatus.NOT_EVALUABLE


def test_a_not_evaluable_or_blocked_analysis_carries_no_facts_and_applies_no_rule() -> None:
    for status in (DomainStatus.NOT_EVALUABLE, DomainStatus.POLICY_BLOCKED):
        with pytest.raises(ValidationError):
            _result(
                status=status,
                reasons=(DomainReasonRecord(code=DomainReason.POLICY_BLOCKED),),
            )  # the default facts and rules are present


def test_duplicate_ids_dangling_references_and_foreign_facts_are_refused() -> None:
    with pytest.raises(ValidationError):
        _result(facts=(_fact(), _fact()))
    with pytest.raises(ValidationError):
        _result(rules=(_rule(fact_refs=("nope",)),))
    with pytest.raises(ValidationError):
        _result(facts=(_fact(domain=LifeDomain.EDUCATION),))


def test_a_non_analysis_status_cannot_be_an_analysis_status() -> None:
    with pytest.raises(ValidationError):
        _result(status=DomainStatus.TRIGGERED)


def test_evidence_ids_are_the_fact_and_rule_ids() -> None:
    assert _result().evidence_ids == {"dom.career.house10.state", "DOM_CAREER_HOUSE_10_P11"}


def test_versions_carry_the_methodology_and_the_ruleset_pin() -> None:
    v = _versions()
    assert v.ruleset_ref == "PANDIT_JI_DOMAIN_PHASE17@1.0.0+KV-0000000000000000"
    with pytest.raises(ValidationError):
        DomainVersions(**{**v.model_dump(), "ruleset_hash": "xyz"})


def test_inputs_and_policy_classes_are_closed_vocabularies() -> None:
    assert DomainInputs().varga_available is False
    assert {p.value for p in PolicyClass} >= {
        "FERTILITY_PREDICTION_BLOCKED",
        "LIFESPAN_BLOCKED",
        "ADULT_CONFIRMATION_REQUIRED",
        "FEAR_OR_STIGMA_TRANSFORMED",
    }
    assert DomainFactKind.HOUSE_STATE.value == "HOUSE_STATE"
