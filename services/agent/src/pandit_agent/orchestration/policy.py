"""Agent safety policy: domain restrictions, request screening, prompt-injection detection.

Three controls, none of which is a guarantee on its own:

1. **Request screening** before any evidence is gathered or any model is called: a request that asks
   for a prohibited reading is refused with a typed result, and a request that tries to override
   the agent's instructions is refused as a prompt-injection attempt.
2. **Structural restrictions**: the restricted categories travel as typed values into the Phase 14
   request (the model's prompt names them and the Phase 14 scan checks its output).
3. **Claim screening** (``screen_claim_text``): every narrated claim and heading is scanned again by
   the agent, with the Phase 13 English lexicon plus the Hindi and Hinglish supplement below.

Limits, stated plainly: word lists are a safety net, not proof that a text is acceptable; the
Hindi and Hinglish supplement is small and partial (`CALIBRATION_REQUIRED`,
`LEGAL_REVIEW_REQUIRED`);
the injection patterns catch common attempts, not all of them. The real protections are structural:
user text only ever reaches the user message, evidence is typed, and every claim must cite evidence
ids that exist in the context.

Domain scope (OWNER-LOCKED 2026-10-03, ``docs/ARCHITECTURE.md`` section 37, ADR-010; do not merge
the two policies for symmetry and do not weaken the palmistry list):

* PALMISTRY: every Phase 13 prohibited category is restricted (PM-13, PM-25).
* ASTROLOGY: ``PRODUCT_POLICIES.md`` allows contextual traditional interpretation of high-impact
  topics (with a professional-advice disclaimer) and prohibits lifespan outputs (the Ayurdaya
  exclusion), so lifespan and death-timing requests are refused and lifespan is the restricted
  output category.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from pandit_contracts.agent import DisclaimerCode, Domain, Intent
from pandit_contracts.palm_policy import ProhibitedCategory, find_prohibited

POLICY_VERSION = "pj-agent-policy-1"

PC = ProhibitedCategory


@dataclass(frozen=True)
class DomainPolicy:
    domain: Domain
    output_restrictions: tuple[ProhibitedCategory, ...]
    request_refusals: tuple[ProhibitedCategory, ...]
    base_disclaimers: tuple[DisclaimerCode, ...]


PALM_POLICY = DomainPolicy(
    domain=Domain.PALMISTRY,
    output_restrictions=tuple(ProhibitedCategory),
    # Asking a palm reading to "predict" is not itself a prohibited reading: the narration simply
    # cannot predict events (the category stays restricted for output).
    request_refusals=tuple(c for c in ProhibitedCategory if c is not PC.EVENT_PREDICTION),
    base_disclaimers=(DisclaimerCode.TRADITIONAL_INTERPRETIVE,),
)
ASTROLOGY_POLICY = DomainPolicy(
    domain=Domain.ASTROLOGY,
    output_restrictions=(PC.LIFESPAN,),
    request_refusals=(PC.LIFESPAN,),
    base_disclaimers=(DisclaimerCode.NO_GUARANTEED_OUTCOME,),
)
_POLICIES = {Domain.PALMISTRY: PALM_POLICY, Domain.ASTROLOGY: ASTROLOGY_POLICY}


def policy_for(domain: Domain) -> DomainPolicy:
    return _POLICIES[domain]


# -- Hindi and Hinglish supplement (partial; matched at a word start, lower case) ---------
_SUPPLEMENT: dict[ProhibitedCategory, tuple[str, ...]] = {
    PC.MEDICAL_DIAGNOSIS: ("sehat", "ilaj", "स्वास्थ्य", "सेहत", "इलाज"),
    PC.DISEASE: ("bimari", "beemari", "rog ", "cancer", "बीमारी", "रोग", "कैंसर"),
    PC.DEATH: (
        "maut",
        "mrityu",
        "marna",
        "marunga",
        "when will i die",
        "when i will die",
        "मृत्यु",
        "मौत",
        "मरूँगा",
        "मरूंगा",
    ),
    PC.LIFESPAN: (
        # death-timing phrasings: locked as lifespan requests (refused in astrology as well)
        "when will i die",
        "when i will die",
        "when am i going to die",
        "when will i pass away",
        "how long will i live",
        "how long do i have to live",
        "how many years will i live",
        "how old will i live",
        "date of my death",
        "umar",
        "ayu ",
        "kitna jiyega",
        "kitna jiyunga",
        "kitne saal jiyunga",
        "kab marunga",
        "maut kab",
        "उम्र",
        "आयु",
        "कितना जीऊंगा",
        "कितना जिऊंगा",
        "मृत्यु कब",
    ),
    PC.CRIMINALITY: ("jail", "apradh", "chor", "जेल", "अपराध", "चोर"),
    PC.MENTAL_ILLNESS: ("pagal", "pagalpan", "mansik rog", "पागल", "मानसिक रोग"),
    PC.FERTILITY: ("santan", "bachche", "bachcha", "garbh", "संतान", "बच्चे", "गर्भ"),
    PC.PATERNITY: ("baap kaun", "पितृत्व"),
    PC.SEXUAL_CONDUCT: ("vyabhichar", "व्यभिचार"),
    PC.ETHNIC_RACIAL_RANKING: ("nasl", "नस्ल"),
    PC.INTELLECTUAL_RANKING: ("bewakoof", "buddhiman", "बेवकूफ", "बुद्धिमान"),
    PC.MORAL_LABELLING: (
        "charitra",
        "imaandar",
        "beimaan",
        "bura insaan",
        "achha insaan",
        "paap",
        "चरित्र",
        "ईमानदार",
        "बेईमान",
        "पाप",
    ),
}

_INJECTION: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        (
            "override_instructions",
            r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(instructions?|rules?|prompt|"
            r"polic(?:y|ies)|restrictions?|guidelines?)\b",
        ),
        (
            "reveal_prompt",
            r"\b(reveal|show|print|repeat|display|leak|tell me|what (?:is|are))\b.{0,30}"
            r"\b(system|hidden|initial|secret)\b.{0,15}\b(prompt|instructions?|message)\b",
        ),
        (
            "role_play_override",
            r"\b(you are now|pretend (?:to be|you are)|developer mode|jailbreak)\b",
        ),
        ("fake_role_marker", r"(^|\n)\s*(system|assistant|developer)\s*:"),
        ("control_tokens", r"<\|[a-z_]+\|>|</?(?:think|evidence|tool_call)>"),
        (
            "claim_verified",
            r"\b(mark|say|state|claim|report|label)\b.{0,30}\b(verified|verification passed|"
            r"fact[- ]checked)\b",
        ),
        (
            "alter_evidence",
            r"\b(change|modify|edit|alter|falsify|fabricate|invent|make up)\b.{0,30}"
            r"\b(evidence|facts?|rules?|sources?|citations?|provenance)\b",
        ),
        (
            "ignore_provenance",
            r"\b(ignore|skip|without)\b.{0,20}\b(evidence|provenance|sources?)\b",
        ),
        (
            "hinglish_override",
            r"\b(pichle|purane|saare|sabhi)\b.{0,30}\b(instructions?|niyam|rules?)\b.{0,20}"
            r"\b(ignore|bhool|bhul|mat maano)\b",
        ),
        ("hinglish_reveal", r"\bsystem prompt\b.{0,20}\b(dikhao|batao|bataiye|likho)\b"),
        ("hindi_override", r"(पिछले|सभी|सारे).{0,30}(निर्देश|नियम).{0,20}(अनदेखा|भूल|न मानो)"),
        ("hindi_reveal", r"सिस्टम\s*प्रॉम्प्ट|(छिपे|गुप्त)\s*निर्देश"),
    )
)

# The topics PRODUCT_POLICIES.md names as high-impact: health, finance, legal, relationships,
# pregnancy, death. Relationships are covered by the intents (love, marriage) in disclaimers_for.
_HIGH_IMPACT = re.compile(
    r"\b(health|disease|illness|medical|doctor|surgery|pregnan\w*|lawsuit|legal|court|"
    r"invest\w*|loan|debt|stock|death|dead|dying|mortality|sehat|bimari|kanoon|nivesh|karz|"
    r"maut|mrityu)\b|"
    r"(स्वास्थ्य|बीमारी|कानूनी|निवेश|कर्ज|गर्भ|मृत्यु|मौत)",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    """Lower case; every run of non-letter, non-digit, non-combining characters becomes a space.

    Combining marks are kept so Devanagari words stay whole. The result is padded with spaces so a
    word-start match is a simple ``" " + term in haystack`` test.
    """
    out: list[str] = []
    for ch in text.lower():
        out.append(ch if ch.isalnum() or unicodedata.category(ch).startswith("M") else " ")
    return " " + re.sub(r"\s+", " ", "".join(out)).strip() + " "


def _supplement_hits(text: str) -> set[ProhibitedCategory]:
    hay = normalize_text(text)
    hits: set[ProhibitedCategory] = set()
    for category, terms in _SUPPLEMENT.items():
        for term in terms:
            needle = " " + term.strip()
            # a term written with a trailing space must match a whole word
            if (needle + " " in hay) if term.endswith(" ") else (needle in hay):
                hits.add(category)
    return hits


def prohibited_categories_in(text: str) -> set[ProhibitedCategory]:
    """Phase 13 English lexicon plus the Hindi and Hinglish supplement."""
    return {m.category for m in find_prohibited(text)} | _supplement_hits(text)


@dataclass(frozen=True)
class RequestScreen:
    refused_categories: tuple[ProhibitedCategory, ...]
    injection_hits: tuple[str, ...]

    @property
    def unsafe(self) -> bool:
        return bool(self.refused_categories)

    @property
    def injection(self) -> bool:
        return bool(self.injection_hits)


def screen_request(user_text: str, policy: DomainPolicy) -> RequestScreen:
    found = prohibited_categories_in(user_text) & set(policy.request_refusals)
    hits = tuple(name for name, pattern in _INJECTION if pattern.search(user_text))
    return RequestScreen(
        refused_categories=tuple(sorted(found, key=lambda c: c.value)),
        injection_hits=hits,
    )


def screen_claim_text(text: str, policy: DomainPolicy) -> tuple[ProhibitedCategory, ...]:
    """Restricted categories present in a generated claim or heading (empty when clean)."""
    found = prohibited_categories_in(text) & set(policy.output_restrictions)
    return tuple(sorted(found, key=lambda c: c.value))


_VERIFICATION_CLAIM = re.compile(
    r"\b(verified|independently verified|fact[- ]checked|verification (?:passed|completed?))\b"
    r"|सत्यापित",
    re.IGNORECASE,
)


def claims_verification(text: str) -> bool:
    """True if generated text asserts it was verified. Only Phase 16 may say that."""
    return bool(_VERIFICATION_CLAIM.search(text))


def disclaimers_for(
    policy: DomainPolicy, intent: Intent, user_text: str, *, evidence_not_production_ready: bool
) -> tuple[DisclaimerCode, ...]:
    codes: list[DisclaimerCode] = list(policy.base_disclaimers)
    if policy.domain is Domain.ASTROLOGY and (
        intent in {Intent.WEALTH, Intent.BUSINESS, Intent.LOVE_RELATIONSHIP, Intent.MARRIAGE}
        or _HIGH_IMPACT.search(user_text)
    ):
        codes.append(DisclaimerCode.NOT_PROFESSIONAL_ADVICE)
    if evidence_not_production_ready:
        codes.append(DisclaimerCode.EVIDENCE_NOT_PRODUCTION_READY)
    codes.append(DisclaimerCode.PENDING_VERIFICATION)
    return tuple(dict.fromkeys(codes))
