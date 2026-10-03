"""Deterministic intent and domain detection over a fixed taxonomy.

A keyword classifier (English, Hinglish, Hindi) with a fixed tie-break order. It is deliberately not
an LLM call: the plan must be reproducible and bounded. Its accuracy is **not measured**
(`CALIBRATION_REQUIRED`); an explicit ``intent_hint`` from the caller always wins, and an unknown
question becomes ``GENERAL`` rather than a guess.
"""

from __future__ import annotations

from dataclasses import dataclass

from pandit_contracts.agent import AgentRequest, Domain, Intent

from pandit_agent.orchestration.memory import MemorySnapshot
from pandit_agent.orchestration.policy import normalize_text

# Ordered: earlier intents win ties.
_KEYWORDS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        Intent.DASHA,
        ("dasha", "mahadasha", "antardasha", "vimshottari", "दशा", "महादशा", "अंतर्दशा"),
    ),
    (
        Intent.TRANSIT,
        ("transit", "gochar", "gochara", "saturn return", "sade sati", "गोचर", "साढ़े साती"),
    ),
    (
        Intent.COMPATIBILITY,
        ("compatib", "kundli matching", "gun milan", "match", "milan", "मिलान", "गुण मिलान"),
    ),
    (
        Intent.MARRIAGE,
        ("marriage", "marry", "wedding", "spouse", "vivah", "shaadi", "shadi", "विवाह", "शादी"),
    ),
    (
        Intent.LOVE_RELATIONSHIP,
        ("love", "relationship", "partner", "romance", "pyaar", "pyar", "prem", "प्रेम", "प्यार"),
    ),
    (
        Intent.CAREER,
        (
            "career",
            "job",
            "profession",
            "promotion",
            "work",
            "naukri",
            "karyakshetra",
            "नौकरी",
            "करियर",
            "व्यवसाय",
        ),
    ),
    (
        Intent.BUSINESS,
        ("business", "startup", "entrepreneur", "vyapar", "dhandha", "व्यापार", "धंधा"),
    ),
    (
        Intent.WEALTH,
        (
            "wealth",
            "money",
            "finance",
            "income",
            "savings",
            "paisa",
            "paise",
            "dhan",
            "धन",
            "पैसा",
            "आमदनी",
        ),
    ),
    (
        Intent.EDUCATION,
        (
            "education",
            "study",
            "exam",
            "college",
            "degree",
            "padhai",
            "shiksha",
            "पढ़ाई",
            "शिक्षा",
            "परीक्षा",
        ),
    ),
    (
        Intent.TRAVEL,
        ("travel", "abroad", "foreign", "visa", "relocat", "videsh", "yatra", "विदेश", "यात्रा"),
    ),
    (
        Intent.DAILY_GUIDANCE,
        ("today", "daily", "horoscope", "this week", "rashifal", "aaj", "आज", "राशिफल"),
    ),
    (Intent.LIFE_ANALYSIS, ("life analysis", "overall", "my life", "jeevan", "जीवन")),
)

_PALM_WORDS = (
    "palm",
    "hand line",
    "life line",
    "head line",
    "heart line",
    "fate line",
    "chirolog",
    "cheiro",
    "hastrekha",
    "hast rekha",
    "hatheli",
    "हस्तरेखा",
    "हथेली",
)

# A short message with no topic of its own is treated as a follow-up (uses memory, never evidence).
_FOLLOW_UP_MAX_WORDS = 12


@dataclass(frozen=True)
class Resolved:
    domain: Domain
    intent: Intent
    from_memory: bool = False
    from_hint: bool = False


class IntentError(ValueError):
    """The request is internally inconsistent (for example a career hint on a palm request)."""


def infer_domain(text: str) -> Domain:
    hay = normalize_text(text)
    return Domain.PALMISTRY if any(" " + w in hay for w in _PALM_WORDS) else Domain.ASTROLOGY


def classify(text: str) -> Intent | None:
    hay = normalize_text(text)
    best: tuple[int, int, Intent] | None = None
    for rank, (intent, words) in enumerate(_KEYWORDS):
        score = sum(1 for w in words if " " + w in hay)
        if score and (best is None or score > best[0]):
            best = (score, rank, intent)
    return best[2] if best else None


def resolve(request: AgentRequest, memory: MemorySnapshot | None) -> Resolved:
    domain = request.domain or infer_domain(request.user_text)
    if domain is Domain.PALMISTRY:
        if request.intent_hint not in (None, Intent.PALM_OVERVIEW, Intent.GENERAL):
            raise IntentError("this intent is not available for the palmistry domain")
        return Resolved(domain, Intent.PALM_OVERVIEW, from_hint=request.intent_hint is not None)
    if request.intent_hint is not None:
        if request.intent_hint is Intent.PALM_OVERVIEW:
            raise IntentError("PALM_OVERVIEW is not an astrology intent")
        return Resolved(domain, request.intent_hint, from_hint=True)
    found = classify(request.user_text)
    if found is not None:
        return Resolved(domain, found)
    words = len(request.user_text.split())
    if (
        memory is not None
        and memory.last_intent is not None
        and memory.last_domain is domain
        and words <= _FOLLOW_UP_MAX_WORDS
    ):
        return Resolved(domain, memory.last_intent, from_memory=True)
    return Resolved(domain, Intent.GENERAL)
