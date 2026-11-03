"""Life-domain routing, evidence presets, the domain evidence tool and domain safety (Phase 17).

The agent does not evaluate a domain. The rule-engine's separate domain ruleset does (ADR-012);
this module holds only what the owner assigned to the agent:

* **routing**: a deterministic mapping from an intent and from keywords to one ``LifeDomain`` (no
  model is asked, an unknown request maps to no domain and the Phase 15 path runs unchanged);
* **presets**: for every domain, the evidence capabilities it asks for, as static data;
* **the evidence tool**: ``DomainAnalysisTool`` serves one already-computed
  ``DomainAnalysisResult`` as typed ``EvidenceRecord`` objects. It computes nothing and takes no
  free-form argument. Policy-blocked rules never reach the model;
* **domain safety**: request screening and claim screening for the owner decisions of 2026-10-06
  (no predictive fertility or pregnancy, no spouse-longevity or lifespan, no medical claims, no
  guaranteed or advisory finance, no moral or derogatory labelling).

Nothing here infers age or sex, calls the network or the filesystem, or reads a clock.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pandit_contracts.agent import (
    Domain,
    EvidenceCapability,
    EvidenceClass,
    EvidenceRecord,
    Intent,
)
from pandit_contracts.domain import (
    DomainAnalysisResult,
    DomainStatus,
    LifeDomain,
    PolicyClass,
)
from pandit_contracts.palm_policy import ProhibitedCategory

from pandit_agent.orchestration.policy import normalize_text
from pandit_agent.orchestration.tools import ToolResult, ToolSpec

C = EvidenceCapability
L = LifeDomain
PC = ProhibitedCategory

STATUS_RECORD_ID = "dom.status"
STATUS_KIND = "DOMAIN_STATUS"
_TEXT_CAP = 2000

# -- presets -----------------------------------------------------------------------------------

# Divisional charts of the locked mappings (owner decision 3); informational here, the ruleset
# decides. A consistency test pins every table below to the domain ruleset.
_VARGA: dict[LifeDomain, tuple[int, ...]] = {
    L.EDUCATION: (24,),
    L.CAREER: (10,),
    L.WEALTH: (2,),
    L.FINANCE: (2,),
    L.SIBLINGS: (3,),
    L.CHILDREN: (7,),
    L.MARRIAGE: (9,),
    L.SPOUSE: (9,),
    L.PARENTS: (12,),
    L.SPIRITUALITY: (20,),
}
_DASHA: frozenset[LifeDomain] = frozenset({L.MARRIAGE})
# No domain reads transit evidence: the Phaladeepika XVI bhava transit records are non-evaluating
# (RESEARCH_PENDING; the domain-to-house bridge is not owner-approved), so no preset asks for it.
_TRANSIT: frozenset[LifeDomain] = frozenset()
_PHASE6_RULES: frozenset[LifeDomain] = frozenset(
    {L.PERSONALITY, L.EDUCATION, L.CAREER, L.FINANCE, L.WEALTH, L.MARRIAGE}
)
_FINANCE_FAMILY: frozenset[LifeDomain] = frozenset({L.FINANCE, L.WEALTH, L.INCOME, L.INVESTMENTS})
_ADULT_GATED: frozenset[LifeDomain] = frozenset(
    {
        L.RELATIONSHIP,
        L.LOVE,
        L.GF_BF,
        L.MARRIAGE,
        L.SPOUSE,
        L.FAMILY,
        L.PARENTS,
        L.SIBLINGS,
        L.CHILDREN,
    }
)


@dataclass(frozen=True)
class DomainPreset:
    """What one domain asks the evidence layer for. Static data, never model output."""

    life_domain: LifeDomain
    required: tuple[EvidenceCapability, ...]
    desired: tuple[EvidenceCapability, ...]
    chart_facts: tuple[str, ...]
    house_facts: bool
    karaka_facts: bool
    varga_facts: tuple[int, ...]
    dasha: bool
    transit: bool
    rule_capabilities: tuple[EvidenceCapability, ...]
    safety: tuple[PolicyClass, ...]
    adult_confirmation_required: bool


def _safety(domain: LifeDomain) -> tuple[PolicyClass, ...]:
    classes: set[PolicyClass] = set()
    if domain in _FINANCE_FAMILY:
        classes |= {
            PolicyClass.FINANCE_INTERPRETIVE_ONLY,
            PolicyClass.PROFESSIONAL_ADVICE_DISCLAIMER,
            PolicyClass.NO_GUARANTEED_OUTCOME,
        }
    if domain is L.CHILDREN:
        classes |= {PolicyClass.CHILDREN_STRUCTURAL_ONLY, PolicyClass.FERTILITY_PREDICTION_BLOCKED}
    if domain is L.HEALTH:
        classes.add(PolicyClass.HEALTH_INTERPRETATION_ONLY)
    if domain in (L.CHILDHOOD, L.SCHOOL, L.GF_BF):
        classes.add(PolicyClass.MINORS_SENSITIVE)
    if domain in _ADULT_GATED:
        classes.add(PolicyClass.ADULT_CONFIRMATION_REQUIRED)
    if domain is L.SPOUSE:
        classes.add(PolicyClass.SEX_SPECIFIC_SOURCE)
    return tuple(sorted(classes, key=lambda p: p.value))


def _build_preset(domain: LifeDomain) -> DomainPreset:
    desired: list[EvidenceCapability] = [C.ASTRO_CHART]
    rules: tuple[EvidenceCapability, ...] = ()
    if domain in _PHASE6_RULES:
        rules = (C.ASTRO_RULES,)
        desired.append(C.ASTRO_RULES)
    if domain in _DASHA:
        desired.append(C.ASTRO_DASHA)
    if domain in _TRANSIT:
        desired.append(C.ASTRO_TRANSIT)
    return DomainPreset(
        life_domain=domain,
        required=(C.ASTRO_DOMAIN,),
        desired=tuple(desired),
        chart_facts=("lagna", "planets", "sign_lords"),
        house_facts=True,
        karaka_facts=True,
        varga_facts=_VARGA.get(domain, ()),
        dasha=domain in _DASHA,
        transit=domain in _TRANSIT,
        rule_capabilities=rules,
        safety=_safety(domain),
        adult_confirmation_required=domain in _ADULT_GATED,
    )


PRESETS: dict[LifeDomain, DomainPreset] = {d: _build_preset(d) for d in LifeDomain}


def preset_for(domain: LifeDomain) -> DomainPreset:
    return PRESETS[domain]


def capabilities_for_domain(
    domain: LifeDomain,
) -> tuple[tuple[EvidenceCapability, ...], tuple[EvidenceCapability, ...]]:
    preset = PRESETS[domain]
    return preset.required, preset.desired


# -- routing -----------------------------------------------------------------------------------

# Specific before general: the first entry wins a tie. Matched at a word start on normalized text.
_KEYWORDS: tuple[tuple[LifeDomain, tuple[str, ...]], ...] = (
    (
        L.FOREIGN_EDUCATION,
        ("study abroad", "abroad study", "foreign education", "studies abroad", "videsh padhai"),
    ),
    (
        L.FOREIGN_SETTLEMENT,
        ("settle abroad", "settlement abroad", "foreign settlement", "immigrat", "videsh basna"),
    ),
    (
        L.FOREIGN_TRAVEL,
        ("foreign travel", "travel abroad", "visit abroad", "videsh yatra", "विदेश यात्रा"),
    ),
    (L.STARTUP, ("startup", "start up")),
    (L.ENTREPRENEURSHIP, ("entrepreneur",)),
    (L.CORPORATE_LIFE, ("corporate", "office politics", "workplace")),
    (
        L.INVESTMENTS,
        ("invest", "stock market", "mutual fund", "shares", "crypto", "nivesh", "निवेश"),
    ),
    (L.INCOME, ("income", "salary", "earnings", "aamdani", "आमदनी")),
    (L.WEALTH, ("wealth", "rich", "dhan", "धन")),
    (L.FINANCE, ("finance", "financial", "money", "paisa", "paise", "पैसा")),
    (L.JOB, ("job", "naukri", "employment", "promotion", "नौकरी")),
    (L.CAREER, ("career", "profession", "करियर", "व्यवसाय")),
    (L.BUSINESS, ("business", "vyapar", "dhandha", "व्यापार")),
    (L.GF_BF, ("girlfriend", "boyfriend", " gf ", " bf ")),
    (L.SPOUSE, ("spouse", "husband", "wife", "pati", "patni", "पति", "पत्नी")),
    (L.MARRIAGE, ("marriage", "marry", "wedding", "shaadi", "shadi", "vivah", "विवाह", "शादी")),
    (L.LOVE, ("love", "romance", "crush", "pyaar", "pyar", "प्यार", "प्रेम")),
    (L.RELATIONSHIP, ("relationship", "rishta", "रिश्ता")),
    (
        L.CHILDREN,
        (
            "children",
            "child ",
            "baby",
            "babies",
            "kids",
            "bachche",
            "bachcha",
            "santan",
            "pregnan",
            "संतान",
            "बच्चे",
        ),
    ),
    (L.PARENTS, ("parents", "mother", "father", "mummy", "papa", "माता", "पिता")),
    (L.SIBLINGS, ("sibling", "brother", "sister", "bhai", "behen", "भाई", "बहन")),
    (L.FAMILY, ("family", "parivar", "परिवार")),
    (L.HIGHER_EDUCATION, ("higher education", "higher studies", "masters", "phd")),
    (L.SCHOOL, ("school",)),
    (L.COLLEGE, ("college", "university")),
    (L.SUBJECTS, ("subject", "which stream", "which course")),
    (L.EDUCATION, ("education", "study", "exam", "padhai", "shiksha", "पढ़ाई", "शिक्षा")),
    (L.CHILDHOOD, ("childhood", "bachpan", "बचपन")),
    (L.PERSONAL_LIFE, ("personal life",)),
    (L.PERSONALITY, ("personality", "my nature", "व्यक्तित्व")),
    (L.SPIRITUALITY, ("spiritual", "moksha", "meditation", "adhyatm", "आध्यात्म", "मोक्ष")),
    (L.TRAVEL, ("travel", "journey", "yatra", "trip", "यात्रा")),
    (L.HEALTH, ("health", "illness", "disease", "sehat", "bimari", "स्वास्थ्य", "बीमारी")),
    (L.MAJOR_LIFE_TRANSITIONS, ("life transition", "major life change")),
    (L.GENERAL_LIFE_PATTERNS, ("life pattern", "life patterns")),
    (L.BIRTH, ("early life",)),
)

_INTENT_DOMAIN: dict[Intent, LifeDomain] = {
    Intent.CAREER: L.CAREER,
    Intent.WEALTH: L.WEALTH,
    Intent.BUSINESS: L.BUSINESS,
    Intent.EDUCATION: L.EDUCATION,
    Intent.MARRIAGE: L.MARRIAGE,
    Intent.LOVE_RELATIONSHIP: L.RELATIONSHIP,
    Intent.TRAVEL: L.TRAVEL,
}


def domain_for_intent(intent: Intent) -> LifeDomain | None:
    """The explicit, deterministic intent-to-domain mapping (one domain per intent, or none)."""
    return _INTENT_DOMAIN.get(intent)


def classify_life_domain(text: str) -> LifeDomain | None:
    """The domain a request names, by keyword (specific first); ``None`` when none matches."""
    hay = normalize_text(text)
    best: tuple[int, int, LifeDomain] | None = None
    for rank, (domain, words) in enumerate(_KEYWORDS):
        score = sum(1 for w in words if (w if w.startswith(" ") else " " + w) in hay)
        if score and (best is None or score > best[0]):
            best = (score, rank, domain)
    return best[2] if best else None


def resolve_life_domain(
    text: str, intent: Intent, *, intent_hint: Intent | None = None
) -> LifeDomain | None:
    """An explicit intent hint wins; then keywords; then the intent's default domain."""
    if intent_hint is not None:
        return domain_for_intent(intent_hint)
    return classify_life_domain(text) or domain_for_intent(intent)


# -- domain safety -----------------------------------------------------------------------------

_FERTILITY_REQUEST = re.compile(
    r"\b(will i (?:ever )?(?:have|get|conceive)|can i (?:conceive|get pregnant)|"
    r"am i (?:going to be )?(?:infertile|pregnant)|how many (?:children|kids|babies)|"
    r"when will i (?:have|get) (?:a )?(?:baby|child|children|pregnan\w*)|"
    r"(?:pregnancy|conception|fertility|infertility) (?:prediction|timing|outcome)|"
    r"will (?:my )?(?:child|baby) be (?:born|illegitimate))\b|"
    r"\b(?:kitne bachche|bachcha kab|baby kab|garbh kab|santan kab|garbhdharan)\b|"
    r"(?:कितने बच्चे|संतान कब|गर्भ कब|बच्चा कब)",
    re.IGNORECASE,
)
_SPOUSE_LONGEVITY_REQUEST = re.compile(
    r"\b(?:how long will my (?:wife|husband|spouse|partner) live|"
    r"when will my (?:wife|husband|spouse|partner) die|"
    r"(?:wife|husband|spouse)(?:'s)? (?:death|longevity|lifespan))\b|"
    r"\b(?:pati ki umar|patni ki umar|pati ki maut|patni ki maut)\b|(?:पति की उम्र|पत्नी की उम्र)",
    re.IGNORECASE,
)
_FINANCE_ADVICE_REQUEST = re.compile(
    r"\b(?:which stocks?|should i (?:buy|sell|invest)|guarantee(?:d)? (?:profit|returns?)|"
    r"best (?:stock|crypto|share)s? to (?:buy|invest))\b",
    re.IGNORECASE,
)

# Output screens for domain narration. Each pattern is a harm class, not a style preference.
_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        (
            "fertility_outcome",
            r"\b(?:infertil\w*|sterile|sterility|barren|childless\w*|miscarr\w*|abortion|"
            r"will (?:conceive|get pregnant|have (?:a |\d+ |no )?(?:child|children|baby|babies|"
            r"son|sons|daughter|daughters))|"
            r"(?:no|without) (?:children|offspring|progeny)|number of (?:children|sons|daughters)|"
            r"loss of (?:a )?(?:child|children|son))\b",
        ),
        ("legitimacy", r"\b(?:illegitim\w*|born of (?:another|other)|bastard|paternity)\b"),
        (
            "spouse_longevity",
            r"\b(?:(?:wife|husband|spouse|partner)(?:'s)? (?:will die|death|dies|lifespan|"
            r"longevity|short[- ]lived)|loss of (?:a )?(?:wife|husband|spouse)|widow\w*)\b",
        ),
        (
            "finance_certainty",
            r"\b(?:guaranteed (?:wealth|profit|income|returns?|success)|"
            r"will (?:definitely |certainly |surely )?(?:become|get) (?:rich|wealthy)|"
            r"sure to (?:profit|gain|get rich)|"
            r"(?:buy|sell|invest in) (?:stocks?|shares|crypto|bitcoin)|"
            r"(?:risk[- ]free|no risk|cannot lose|can't lose))\b",
        ),
        (
            "medical_claim",
            r"\b(?:diagnos\w*|prescri\w*|you (?:have|will get|will develop) (?:a |an )?"
            r"(?:disease|illness|cancer|diabetes|tumou?r)|cure[sd]?|treatment (?:for|of))\b",
        ),
        (
            "moral_or_stigma_label",
            r"\b(?:hypocrit\w*|outcast|heretic\w*|wicked|sinful|cursed|unlucky person|"
            r"low[- ]born|of low morality|will go to hell|executioner|butcher)\b",
        ),
    )
)

_DOMAIN_OUTPUT_RESTRICTIONS: tuple[ProhibitedCategory, ...] = (
    PC.LIFESPAN,
    PC.DEATH,
    PC.MEDICAL_DIAGNOSIS,
    PC.DISEASE,
    PC.CRIMINALITY,
    PC.MENTAL_ILLNESS,
    PC.PATERNITY,
    PC.SEXUAL_CONDUCT,
    PC.ETHNIC_RACIAL_RANKING,
    PC.INTELLECTUAL_RANKING,
    PC.MORAL_LABELLING,
)
_DOMAIN_REQUEST_REFUSALS: tuple[ProhibitedCategory, ...] = (PC.LIFESPAN,)


def domain_output_restrictions() -> tuple[ProhibitedCategory, ...]:
    return _DOMAIN_OUTPUT_RESTRICTIONS


def domain_request_refusals() -> tuple[ProhibitedCategory, ...]:
    return _DOMAIN_REQUEST_REFUSALS


def screen_domain_request(text: str) -> tuple[str, ...]:
    """Domain-specific refusals (predictive fertility, spouse longevity, finance advice)."""
    found: list[str] = []
    if _FERTILITY_REQUEST.search(text):
        found.append("PREDICTIVE_FERTILITY")
    if _SPOUSE_LONGEVITY_REQUEST.search(text):
        found.append("SPOUSE_LONGEVITY")
    if _FINANCE_ADVICE_REQUEST.search(text):
        found.append("FINANCE_ADVICE")
    return tuple(found)


def screen_domain_claim(text: str) -> tuple[str, ...]:
    """Harm classes present in a generated domain claim or heading (empty when clean)."""
    return tuple(name for name, pattern in _CLAIM_PATTERNS if pattern.search(text))


# -- the evidence tool -------------------------------------------------------------------------


def _cap(text: str) -> str:
    return text if len(text) <= _TEXT_CAP else text[: _TEXT_CAP - 1] + "…"


def _attr_text(pairs: tuple[tuple[str, str], ...]) -> str:
    return "; ".join(f"{k}={v}" for k, v in pairs)


class DomainAnalysisTool:
    """Serves one already-computed ``DomainAnalysisResult`` (rule-engine domain ruleset).

    It re-checks nothing it was not given: the result's own hash is verified on construction by the
    contract, a request for another domain is not served, and nothing is computed here. Rules the
    policy withheld are **not** passed on (no wording and no tags exist for them); the status
    record states that some were withheld.
    """

    def __init__(self, result: DomainAnalysisResult, *, name: str | None = None) -> None:
        self._result = result
        self._spec = ToolSpec(
            name=name or f"domain.{result.domain.value.lower()}",
            domain=Domain.ASTROLOGY,
            capabilities=frozenset({C.ASTRO_DOMAIN, C.ASTRO_DASHA, C.ASTRO_TRANSIT}),
            life_domain=result.domain,
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    @property
    def result(self) -> DomainAnalysisResult:
        return self._result

    def invoke(self, capabilities: frozenset[EvidenceCapability]) -> ToolResult:
        result = self._result
        ref = result.result_hash
        version_ref = result.versions.ruleset_ref
        blocked = sum(1 for r in result.rules if r.status is DomainStatus.POLICY_BLOCKED)
        policy = ",".join(p.value for p in result.policy_flags) or "none"
        reasons = ",".join(r.code.value for r in result.reasons) or "none"
        records: list[EvidenceRecord] = [
            EvidenceRecord(
                evidence_id=STATUS_RECORD_ID,
                domain=Domain.ASTROLOGY,
                evidence_class=EvidenceClass.CONTEXT_STATUS,
                kind=STATUS_KIND,
                text=_cap(
                    f"life_domain={result.domain.value}; research_support={result.support.value}; "
                    f"status={result.status.value}; reasons={reasons}; policy={policy}; "
                    f"withheld_by_policy={blocked}; "
                    f"knowledge_version={result.versions.knowledge_version}; "
                    f"methodology={result.versions.methodology_version}"
                ),
                status=result.status.value,
                version_ref=version_ref,
                bundle_ref=ref,
            )
        ]
        if result.status in {DomainStatus.NOT_EVALUABLE, DomainStatus.POLICY_BLOCKED}:
            return ToolResult(tuple(records), provided=frozenset({C.ASTRO_DOMAIN}))
        for fact in result.facts:
            records.append(
                EvidenceRecord(
                    evidence_id=fact.fact_id,
                    domain=Domain.ASTROLOGY,
                    evidence_class=EvidenceClass.CALCULATED_FACT,
                    kind=fact.kind.value,
                    text=_cap(
                        f"life_domain={fact.domain.value}; subject={fact.subject}; "
                        f"{_attr_text(fact.attributes)}; mapping={fact.mapping_id}; "
                        f"support={fact.support.value}; "
                        f"chart_refs={','.join(fact.chart_refs) or 'none'}"
                    ),
                    source_profile=fact.source_profile,
                    source_location=fact.source_location,
                    version_ref=version_ref,
                    bundle_ref=ref,
                )
            )
        for rule in result.rules:
            if rule.status is DomainStatus.POLICY_BLOCKED:
                continue  # withheld by policy: nothing about it reaches the model
            tags = rule.interpretation
            records.append(
                EvidenceRecord(
                    evidence_id=rule.rule_id,
                    domain=Domain.ASTROLOGY,
                    evidence_class=EvidenceClass.RULE_EVALUATION,
                    kind="DOMAIN_RULE",
                    text=_cap(
                        f"rule_kind={rule.kind.value}; rule_version={rule.rule_version}; "
                        f"support={rule.support.value}; "
                        f"domain_tags={','.join(tags.domain_tags) if tags else 'none'}; "
                        "signification_tags="
                        f"{','.join(tags.signification_tags) if tags else 'none'}; "
                        f"effect_class={tags.effect_class if tags else 'none'}; "
                        f"reason={rule.reason.value if rule.reason else 'none'}; "
                        f"policy={','.join(p.value for p in rule.policy_flags) or 'none'}"
                    ),
                    status=rule.status.value,
                    source_profile=rule.source_profile,
                    source_location=rule.source_location,
                    version_ref=version_ref,
                    fact_refs=tuple(rule.fact_refs),
                    conflict_ids=tuple(rule.conflict_ids),
                    bundle_ref=ref,
                )
            )
        provided = {C.ASTRO_DOMAIN}
        if result.inputs.dasha_available:
            provided.add(C.ASTRO_DASHA)
        if result.inputs.transit_available:
            provided.add(C.ASTRO_TRANSIT)
        return ToolResult(
            tuple(records), provided=frozenset(provided & (capabilities | {C.ASTRO_DOMAIN}))
        )


__all__ = [
    "PRESETS",
    "STATUS_KIND",
    "STATUS_RECORD_ID",
    "DomainAnalysisTool",
    "DomainPreset",
    "capabilities_for_domain",
    "classify_life_domain",
    "domain_for_intent",
    "domain_output_restrictions",
    "domain_request_refusals",
    "preset_for",
    "resolve_life_domain",
    "screen_domain_claim",
    "screen_domain_request",
]
