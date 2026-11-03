"""Life-domain intelligence contracts (Phase 17; ADR-012, standards LD-01 to LD-27).

A ``DomainAnalysisResult`` is the structured, deterministic, verification-ready output of the
Phase 17 domain layer for one life domain and one chart. It is produced by the rule-engine's
separate domain ruleset from facts that already exist (the D1 chart, optional divisional charts,
optional dasha and transit sections of a supplied bundle) and from the source-backed methodology
the knowledge service owns. The agent turns it into evidence records for narration (Phase 15); the
verifier checks claims against it (Phase 16).

Invariants carried by these types:

* **No invented support.** Every domain carries its own research status; a domain without a
  source-backed methodology is ``NOT_EVALUABLE`` with a typed reason. A sub-domain never inherits
  its parent's support.
* **One status vocabulary.** ``DomainStatus`` reuses names that already exist: the Phase 6 and
  Phase 12 ``NOT_EVALUABLE`` and the Phase 16 ``INSUFFICIENT_EVIDENCE``, ``POLICY_BLOCKED`` and
  ``CONFLICTING_EVIDENCE``; there is no parallel scheme (a test pins this).
* **Provenance on everything.** Facts and rule results name the source profile, location, support
  status, knowledge version and ruleset version they rest on. Conflicting source profiles stay
  separate; nothing is merged.
* **Policy is data.** Policy classes travel with the evidence; policy-blocked content is withheld
  (no text, no tags) and is never produced for the user.
* **No sex, no age.** The request carries no sex field and never infers age; adulthood is an
  explicit caller statement (``subject_adult_confirmed``), never derived.
* **Deterministic.** There is no clock; the result hash covers everything except itself.
* **Not verified.** Nothing here is ``VERIFIED``; only Phase 16 may set that.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

DOMAIN_CONTRACT_VERSION = "1.0.0"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TAG_RE = re.compile(r"^[a-z0-9_.]+$")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


class LifeDomain(str, Enum):
    """The 27 ``Phases.md`` Phase 17 domains, then the ``features.md`` extensions (LD-03, LD-25)."""

    BIRTH = "BIRTH"
    PERSONALITY = "PERSONALITY"
    CHILDHOOD = "CHILDHOOD"
    SCHOOL = "SCHOOL"
    COLLEGE = "COLLEGE"
    SUBJECTS = "SUBJECTS"
    EDUCATION = "EDUCATION"
    CAREER = "CAREER"
    JOB = "JOB"
    CORPORATE_LIFE = "CORPORATE_LIFE"
    BUSINESS = "BUSINESS"
    STARTUP = "STARTUP"
    FINANCE = "FINANCE"
    WEALTH = "WEALTH"
    LOVE = "LOVE"
    GF_BF = "GF_BF"
    RELATIONSHIP = "RELATIONSHIP"
    MARRIAGE = "MARRIAGE"
    SPOUSE = "SPOUSE"
    FAMILY = "FAMILY"
    CHILDREN = "CHILDREN"
    TRAVEL = "TRAVEL"
    FOREIGN_TRAVEL = "FOREIGN_TRAVEL"
    FOREIGN_EDUCATION = "FOREIGN_EDUCATION"
    FOREIGN_SETTLEMENT = "FOREIGN_SETTLEMENT"
    PERSONAL_LIFE = "PERSONAL_LIFE"
    SPIRITUALITY = "SPIRITUALITY"
    # features.md extensions (explicit sub-domains or extensions, never top-level duplicates)
    PARENTS = "PARENTS"
    SIBLINGS = "SIBLINGS"
    INCOME = "INCOME"
    INVESTMENTS = "INVESTMENTS"
    ENTREPRENEURSHIP = "ENTREPRENEURSHIP"
    HIGHER_EDUCATION = "HIGHER_EDUCATION"
    MAJOR_LIFE_TRANSITIONS = "MAJOR_LIFE_TRANSITIONS"
    GENERAL_LIFE_PATTERNS = "GENERAL_LIFE_PATTERNS"
    HEALTH = "HEALTH"


#: The 27 Phase 17 domains of ``Phases.md``, in roadmap order.
PHASES_MD_DOMAINS: tuple[LifeDomain, ...] = tuple(LifeDomain)[:27]
#: The ``features.md`` concepts that are extensions of the 27.
EXTENSION_DOMAINS: tuple[LifeDomain, ...] = tuple(LifeDomain)[27:]


class DomainSupport(str, Enum):
    """The research status of a domain/mapping (never upgraded without new primary evidence)."""

    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class DomainStatus(str, Enum):
    """The outcome of an analysis or of one rule. Every name besides ``EVALUATED`` and
    ``TRIGGERED`` already exists in the Phase 6 or Phase 16 vocabulary."""

    EVALUATED = "EVALUATED"  # an analysis produced source-backed evidence
    TRIGGERED = "TRIGGERED"  # a rule applies (Phase 6 name)
    NOT_TRIGGERED = "NOT_TRIGGERED"  # a rule does not apply (Phase 6 name)
    NOT_EVALUABLE = "NOT_EVALUABLE"  # no valid methodology (Phase 6, Phase 12 name)
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # a required input is absent (Phase 16 name)
    POLICY_BLOCKED = "POLICY_BLOCKED"  # withheld by policy (Phase 16 name)
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"  # source profiles disagree (Phase 16 name)


_ANALYSIS_STATUSES = frozenset(
    {
        DomainStatus.EVALUATED,
        DomainStatus.NOT_EVALUABLE,
        DomainStatus.INSUFFICIENT_EVIDENCE,
        DomainStatus.POLICY_BLOCKED,
        DomainStatus.CONFLICTING_EVIDENCE,
    }
)
_RULE_STATUSES = frozenset(
    {
        DomainStatus.TRIGGERED,
        DomainStatus.NOT_TRIGGERED,
        DomainStatus.NOT_EVALUABLE,
        DomainStatus.INSUFFICIENT_EVIDENCE,
        DomainStatus.POLICY_BLOCKED,
        DomainStatus.CONFLICTING_EVIDENCE,
    }
)


class DomainReason(str, Enum):
    """Typed reasons (standards LD-19 plus the specific cases of the owner decisions)."""

    NO_SOURCE_READ = "NO_SOURCE_READ"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    MISSING_FACT = "MISSING_FACT"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    PHASE_18_DEPENDENCY = "PHASE_18_DEPENDENCY"
    UNDEFINED_DOMAIN = "UNDEFINED_DOMAIN"
    UNREAD_SOURCE = "UNREAD_SOURCE"
    RESEARCH_PENDING = "RESEARCH_PENDING"
    MISSING_VARGA_EVIDENCE = "MISSING_VARGA_EVIDENCE"
    MISSING_DASHA_EVIDENCE = "MISSING_DASHA_EVIDENCE"
    MISSING_TRANSIT_EVIDENCE = "MISSING_TRANSIT_EVIDENCE"
    ADULT_CONFIRMATION_REQUIRED = "ADULT_CONFIRMATION_REQUIRED"
    MINORS_POLICY_UNRESOLVED = "MINORS_POLICY_UNRESOLVED"
    SEX_SPECIFIC_METHOD = "SEX_SPECIFIC_METHOD"
    PREDICTIVE_FERTILITY_BLOCKED = "PREDICTIVE_FERTILITY_BLOCKED"
    SPOUSE_LONGEVITY_BLOCKED = "SPOUSE_LONGEVITY_BLOCKED"
    HISTORICAL_STATEMENT_WITHHELD = "HISTORICAL_STATEMENT_WITHHELD"
    METHODOLOGY_NOT_APPROVED = "METHODOLOGY_NOT_APPROVED"
    KNOWLEDGE_VERSION_MISMATCH = "KNOWLEDGE_VERSION_MISMATCH"
    RULESET_VERSION_MISMATCH = "RULESET_VERSION_MISMATCH"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"


class PolicyClass(str, Enum):
    """Policy metadata attached to a domain, a mapping or a fact (LD-20, LD-26)."""

    FINANCE_INTERPRETIVE_ONLY = "FINANCE_INTERPRETIVE_ONLY"
    HEALTH_INTERPRETATION_ONLY = "HEALTH_INTERPRETATION_ONLY"
    MINORS_SENSITIVE = "MINORS_SENSITIVE"
    ADULT_CONFIRMATION_REQUIRED = "ADULT_CONFIRMATION_REQUIRED"
    CHILDREN_STRUCTURAL_ONLY = "CHILDREN_STRUCTURAL_ONLY"
    FERTILITY_PREDICTION_BLOCKED = "FERTILITY_PREDICTION_BLOCKED"
    LIFESPAN_BLOCKED = "LIFESPAN_BLOCKED"
    SEX_SPECIFIC_SOURCE = "SEX_SPECIFIC_SOURCE"
    FEAR_OR_STIGMA_TRANSFORMED = "FEAR_OR_STIGMA_TRANSFORMED"
    PROFESSIONAL_ADVICE_DISCLAIMER = "PROFESSIONAL_ADVICE_DISCLAIMER"
    NO_GUARANTEED_OUTCOME = "NO_GUARANTEED_OUTCOME"


class DomainFactKind(str, Enum):
    HOUSE_STATE = "HOUSE_STATE"  # the structural state of a source-assigned house
    KARAKA_STATE = "KARAKA_STATE"  # the structural state of a source-assigned karaka
    VARGA_PLACEMENT = "VARGA_PLACEMENT"  # a placement in a divisional chart the source assigns
    DASHA_RELATION = "DASHA_RELATION"  # a dasha lord's relation to a house (marriage method)
    TRANSIT_RELATION = "TRANSIT_RELATION"  # a transit relation of the researched bhava method
    SUBJECT_ASSOCIATION = "SUBJECT_ASSOCIATION"  # the 2nd lord's association (subjects)


class DomainRuleKind(str, Enum):
    HOUSE_RELEVANCE = "HOUSE_RELEVANCE"
    KARAKA_RELEVANCE = "KARAKA_RELEVANCE"
    VARGA_RELEVANCE = "VARGA_RELEVANCE"
    PHASE6_RULE_APPLICABILITY = "PHASE6_RULE_APPLICABILITY"
    MARRIAGE_DASHA_METHOD = "MARRIAGE_DASHA_METHOD"
    SUBJECT_PROFICIENCY = "SUBJECT_PROFICIENCY"
    POLICY_WITHHELD = "POLICY_WITHHELD"


EffectClass = Literal["supportive", "challenging", "mixed", "neutral", "context_dependent"]


class DomainVersions(_Frozen):
    """Everything that identifies the methodology a result came from."""

    knowledge_version: str  # the Phase 17 knowledge version the ruleset was built against
    methodology_version: str  # the domain methodology data version
    ruleset_id: str
    ruleset_version: str
    ruleset_hash: str
    evaluator_version: str

    @model_validator(mode="after")
    def _hash(self) -> DomainVersions:
        if not _SHA256_RE.match(self.ruleset_hash):
            raise ValueError("ruleset_hash must be a lower-case SHA-256")
        return self

    @property
    def ruleset_ref(self) -> str:
        return f"{self.ruleset_id}@{self.ruleset_version}+{self.knowledge_version}"


class DomainAnalysisRequest(_Frozen):
    """The caller's request for one domain's analysis. There is no sex field and no birth data.

    ``subject_adult_confirmed`` is an explicit statement by the caller; the domain layer never
    infers age. ``as_of_utc`` is the explicit instant for selecting the current dasha period (the
    domain layer reads no clock). The expected versions let a caller pin the methodology.
    """

    analysis_id: str
    domain: LifeDomain
    subject_adult_confirmed: bool | None = None
    as_of_utc: str | None = None
    chart_bundle_ref: str | None = None
    expected_knowledge_version: str | None = None
    expected_ruleset_hash: str | None = None

    @model_validator(mode="after")
    def _ids(self) -> DomainAnalysisRequest:
        if not _ID_RE.match(self.analysis_id):
            raise ValueError("analysis_id must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        if self.as_of_utc is not None and not re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$", self.as_of_utc
        ):
            raise ValueError("as_of_utc must be an ISO-8601 UTC instant")
        return self


class DomainInterpretation(_Frozen):
    """Structured tags only (LD-16); wording belongs to the knowledge store and the agent."""

    domain_tags: tuple[str, ...] = ()
    signification_tags: tuple[str, ...] = ()
    effect_class: EffectClass = "neutral"

    @model_validator(mode="after")
    def _tags(self) -> DomainInterpretation:
        for tag in (*self.domain_tags, *self.signification_tags):
            if not _TAG_RE.match(tag):
                raise ValueError(f"tag must be lower_snake/dot, got {tag!r}")
        return self


class DomainFact(_Frozen):
    """A deterministic, structural fact that the methodology says is relevant to the domain.

    ``attributes`` is a sorted tuple of (name, value) string pairs, so equal inputs give equal
    bytes. A fact never states an effect or a prediction.
    """

    fact_id: str
    kind: DomainFactKind
    domain: LifeDomain
    mapping_id: str
    subject: str
    attributes: tuple[tuple[str, str], ...] = ()
    chart_refs: tuple[str, ...] = ()
    house_refs: tuple[int, ...] = ()
    karaka_refs: tuple[str, ...] = ()
    varga_refs: tuple[int, ...] = ()
    dasha_refs: tuple[str, ...] = ()
    transit_refs: tuple[str, ...] = ()
    source_profile: str
    source_location: str
    support: DomainSupport
    policy_flags: tuple[PolicyClass, ...] = ()

    @model_validator(mode="after")
    def _checks(self) -> DomainFact:
        if not _ID_RE.match(self.fact_id):
            raise ValueError("fact_id must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        if list(self.attributes) != sorted(self.attributes):
            raise ValueError("attributes must be sorted")
        if self.support in {DomainSupport.NOT_EVALUABLE}:
            raise ValueError("a fact cannot rest on a NOT_EVALUABLE mapping")
        return self


class DomainRuleResult(_Frozen):
    """The outcome of one source-backed domain rule (never a prediction)."""

    rule_id: str
    rule_version: str
    kind: DomainRuleKind
    status: DomainStatus
    reason: DomainReason | None = None
    source_profile: str
    source_id: str
    source_location: str
    verification_level: str
    support: DomainSupport
    fact_refs: tuple[str, ...] = ()
    interpretation: DomainInterpretation | None = None
    phase6_rule_id: str | None = None
    phase6_status: str | None = None
    conflict_ids: tuple[str, ...] = ()
    policy_flags: tuple[PolicyClass, ...] = ()
    detail: str | None = None

    @model_validator(mode="after")
    def _checks(self) -> DomainRuleResult:
        if self.status not in _RULE_STATUSES:
            raise ValueError("a rule result status must be a rule status")
        failed = self.status in {
            DomainStatus.NOT_EVALUABLE,
            DomainStatus.INSUFFICIENT_EVIDENCE,
            DomainStatus.POLICY_BLOCKED,
            DomainStatus.CONFLICTING_EVIDENCE,
        }
        if failed != (self.reason is not None):
            raise ValueError("a reason is required exactly for a non-applied rule status")
        if self.interpretation is not None and self.status is not DomainStatus.TRIGGERED:
            raise ValueError("interpretation tags exist only on a TRIGGERED rule")
        if self.status is DomainStatus.POLICY_BLOCKED and (self.interpretation or self.fact_refs):
            raise ValueError("a policy-blocked result exposes no tags and no facts")
        return self


class DomainReasonRecord(_Frozen):
    code: DomainReason
    detail: str | None = None


class DomainInputs(_Frozen):
    """Which optional evidence sections were supplied (content-free)."""

    varga_available: bool = False
    dasha_available: bool = False
    transit_available: bool = False
    phase6_results_available: bool = False
    varga_facts_hash: str | None = None
    dasha_facts_hash: str | None = None
    transit_facts_hash: str | None = None
    phase6_bundle_ref: str | None = None


class DomainAnalysisResult(_Frozen):
    """Structured domain reasoning for one domain and one chart (verification-ready)."""

    schema_version: str = DOMAIN_CONTRACT_VERSION
    analysis_id: str
    domain: LifeDomain
    parent_domain: LifeDomain | None = None
    support: DomainSupport
    status: DomainStatus
    reasons: tuple[DomainReasonRecord, ...] = ()
    facts: tuple[DomainFact, ...] = ()
    rules: tuple[DomainRuleResult, ...] = ()
    policy_flags: tuple[PolicyClass, ...] = ()
    versions: DomainVersions
    inputs: DomainInputs = DomainInputs()
    result_hash: str

    @model_validator(mode="after")
    def _checks(self) -> DomainAnalysisResult:
        if self.status not in _ANALYSIS_STATUSES:
            raise ValueError("an analysis status must be an analysis status")
        if not _ID_RE.match(self.analysis_id):
            raise ValueError("analysis_id must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        fact_ids = [f.fact_id for f in self.facts]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("duplicate fact id")
        rule_ids = [r.rule_id for r in self.rules]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("duplicate rule id")
        known = set(fact_ids)
        for rule in self.rules:
            if not set(rule.fact_refs) <= known:
                raise ValueError(f"{rule.rule_id}: a fact reference does not resolve")
        if any(f.domain is not self.domain for f in self.facts):
            raise ValueError("a fact belongs to another domain")
        if self.status is DomainStatus.EVALUATED:
            if self.support not in {
                DomainSupport.SOURCE_SUPPORTED,
                DomainSupport.PARTIALLY_SUPPORTED,
            }:
                raise ValueError("only a supported domain can be EVALUATED")
            if not self.facts and not self.rules:
                raise ValueError("an EVALUATED analysis carries evidence")
        else:
            if not self.reasons:
                raise ValueError("a non-EVALUATED analysis states its reasons")
            if (
                self.status in {DomainStatus.NOT_EVALUABLE, DomainStatus.POLICY_BLOCKED}
                and self.facts
            ):
                raise ValueError("a NOT_EVALUABLE or POLICY_BLOCKED analysis carries no facts")
            if self.status in {DomainStatus.NOT_EVALUABLE, DomainStatus.POLICY_BLOCKED} and any(
                r.status in {DomainStatus.TRIGGERED, DomainStatus.NOT_TRIGGERED} for r in self.rules
            ):
                raise ValueError("a NOT_EVALUABLE or POLICY_BLOCKED analysis applies no rule")
        if self.result_hash != domain_result_hash(self):
            raise ValueError("result_hash does not match the result content")
        return self

    @property
    def evidence_ids(self) -> frozenset[str]:
        return frozenset({f.fact_id for f in self.facts} | {r.rule_id for r in self.rules})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def domain_result_hash(result: DomainAnalysisResult) -> str:
    content = result.model_dump(mode="json")
    content.pop("result_hash", None)
    return hashlib.sha256(_canonical(content).encode("utf-8")).hexdigest()


def with_hash(**fields: Any) -> DomainAnalysisResult:
    """Build a result and stamp its own content hash (used by the domain evaluator)."""
    unsigned = DomainAnalysisResult.model_construct(result_hash="", **fields)
    digest = domain_result_hash(unsigned)
    return DomainAnalysisResult(**fields, result_hash=digest)
