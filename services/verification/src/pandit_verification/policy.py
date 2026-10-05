"""Verification-side safety screens.

Phase 16 must never become a safety bypass. Whatever reached it, a claim that touches a prohibited
category, claims verification for itself, embeds evidence or authority, or tries to instruct the
system is ``POLICY_BLOCKED`` and is never verified.

The verifier does not import the agent (ADR-006: the verification layer is independent of the layer
it checks), so it carries its own copy of the Hindi and Hinglish supplement. A repository test
(``tests/integration/test_verification_phase16.py``) asserts the copy equals the agent's list, so
the two cannot drift apart silently.

Domain scoping follows the owner decision of 2026-10-03 (ADR-010):

* PALMISTRY: the complete Phase 13 prohibited-category list, never weakened.
* ASTROLOGY: lifespan and death timing are blocked; the professional-advice disclaimer for
  high-impact topics is the agent's concern, not a verification block.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from pandit_contracts.agent import Domain
from pandit_contracts.palm_policy import ProhibitedCategory, find_prohibited

POLICY_VERSION = "pj-verification-policy-1"

PC = ProhibitedCategory

PALM_RESTRICTED: tuple[ProhibitedCategory, ...] = tuple(ProhibitedCategory)
ASTROLOGY_RESTRICTED: tuple[ProhibitedCategory, ...] = (PC.LIFESPAN,)

SUPPLEMENT: dict[ProhibitedCategory, tuple[str, ...]] = {
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

# Death timing in output. Astrology restricts lifespan; a statement of when death occurs is a
# lifespan statement (the locked wording: lifespan and death-timing are refused).
_DEATH_TIMING = re.compile(
    r"\b(?:die|dies|death|dead|demise|pass(?:es|ing)? away|end of (?:your |his |her )?life)\b"
    r".{0,60}\b(?:age|aged|year|years|in \d{2,4}|by \d{2,4}|at \d{2}|during|dasha|period|when|"
    r"before|after)\b"
    r"|\b(?:age|aged|year|years|in \d{2,4}|by \d{2,4}|at \d{2}|during|dasha|period|when|before)\b"
    r".{0,60}\b(?:die|dies|death|dead|demise|pass(?:es|ing)? away|"
    r"end of (?:your |his |her )?life)\b",
    re.IGNORECASE,
)

_AUTHORITY = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        (
            "override_instructions",
            r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(instructions?|rules?|prompt|"
            r"polic(?:y|ies)|restrictions?|guidelines?|verification)\b",
        ),
        (
            "mark_verified",
            r"\b(mark|set|label|flag|treat|consider|approve|accept)\b.{0,30}"
            r"\b(verified|approved)\b",
        ),
        ("authority_field", r"\b(verified_by|verification_state|verification|bundle_ref)\s*[:=]"),
        (
            "embedded_evidence",
            r"[\"']?\b(evidence_id|rule_id|fact_id|bundle_hash|knowledge_version|"
            r"ruleset_content_hash|source_profile)\b[\"']?\s*[:=]",
        ),
        ("embedded_json", r"\{\s*[\"'][a-z_]{3,40}[\"']\s*:"),
        (
            "tool_instruction",
            r"\b(call|invoke|run|execute|use)\b.{0,20}\b(tool|function|command|"
            r"shell|script|query|sql)\b",
        ),
        ("control_tokens", r"<\|[a-z_]+\|>|</?(?:think|evidence|tool_call|system)>"),
        ("fake_role_marker", r"\b(system|assistant|developer)\s*:"),
        (
            "set_verification_state",
            r"\bverification\b.{0,25}\b(passed|approved|complete[d]?|ok|granted)\b",
        ),
        ("role_play_override", r"\b(you are now|pretend (?:to be|you are)|developer mode)\b"),
        (
            "file_or_db_write",
            r"\b(write|modify|delete|drop|update|insert)\b.{0,25}\b(file|database|"
            r"table|record|evidence|ruleset)\b",
        ),
    )
)
_VERIFICATION_CLAIM = re.compile(
    r"\b(verified|independently verified|fact[- ]checked|verification (?:passed|completed?)|"
    r"officially confirmed)\b|सत्यापित",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TextScreen:
    prohibited: tuple[ProhibitedCategory, ...] = ()
    death_timing: bool = False
    authority_hits: tuple[str, ...] = ()
    claims_verification: bool = False

    @property
    def blocked(self) -> bool:
        return bool(
            self.prohibited or self.death_timing or self.authority_hits or self.claims_verification
        )


def _normalize(text: str) -> str:
    out: list[str] = []
    for ch in text.lower():
        out.append(ch if ch.isalnum() or unicodedata.category(ch).startswith("M") else " ")
    return " " + re.sub(r"\s+", " ", "".join(out)).strip() + " "


def _supplement_hits(text: str) -> set[ProhibitedCategory]:
    hay = _normalize(text)
    hits: set[ProhibitedCategory] = set()
    for category, terms in SUPPLEMENT.items():
        for term in terms:
            needle = " " + term.strip()
            if (needle + " " in hay) if term.endswith(" ") else (needle in hay):
                hits.add(category)
    return hits


def restricted_for(domain: Domain) -> tuple[ProhibitedCategory, ...]:
    return PALM_RESTRICTED if domain is Domain.PALMISTRY else ASTROLOGY_RESTRICTED


def screen_text(text: str, domain: Domain) -> TextScreen:
    found = {m.category for m in find_prohibited(text)} | _supplement_hits(text)
    prohibited = tuple(
        sorted(found & set(restricted_for(domain)), key=lambda category: category.value)
    )
    death_timing = domain is Domain.ASTROLOGY and bool(_DEATH_TIMING.search(text))
    hits = tuple(name for name, pattern in _AUTHORITY if pattern.search(text))
    return TextScreen(
        prohibited=prohibited,
        death_timing=death_timing,
        authority_hits=hits,
        claims_verification=bool(_VERIFICATION_CLAIM.search(text)),
    )
