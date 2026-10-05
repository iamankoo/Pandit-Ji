"""Deterministic text analysis: a claim sentence -> checkable atoms.

This is **closed-vocabulary lexical grounding**, not natural-language entailment. The analyzer
recognises a fixed set of entities (planets, signs, house numbers, dignity words, retrograde, hand
sides, palm lines and mounts, life topics, valence words, certainty words, framing words). It
reports exactly what it recognised, so the engine can decide what the evidence supports and what
the checker could not read. Text it does not recognise is never treated as supported.

Recognition is English first, with a small Hindi/Hinglish planet and sign vocabulary. Hindi and
Hinglish coverage is a stated limitation (``CALIBRATION_REQUIRED``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# -- vocabularies --------------------------------------------------------------------------------

PLANETS: dict[str, str] = {
    "sun": "sun",
    "surya": "sun",
    "सूर्य": "sun",
    "moon": "moon",
    "chandra": "moon",
    "चंद्र": "moon",
    "चन्द्र": "moon",
    "mars": "mars",
    "mangal": "mars",
    "मंगल": "mars",
    "mercury": "mercury",
    "budh": "mercury",
    "बुध": "mercury",
    "jupiter": "jupiter",
    "guru": "jupiter",
    "brihaspati": "jupiter",
    "गुरु": "jupiter",
    "बृहस्पति": "jupiter",
    "venus": "venus",
    "shukra": "venus",
    "शुक्र": "venus",
    "saturn": "saturn",
    "shani": "saturn",
    "शनि": "saturn",
    "rahu": "rahu",
    "राहु": "rahu",
    "ketu": "ketu",
    "केतु": "ketu",
}
SIGNS: dict[str, str] = {
    "aries": "aries",
    "mesh": "aries",
    "taurus": "taurus",
    "vrishabha": "taurus",
    "vrishabh": "taurus",
    "gemini": "gemini",
    "mithun": "gemini",
    "cancer": "cancer",
    "karka": "cancer",
    "kark": "cancer",
    "leo": "leo",
    "simha": "leo",
    "virgo": "virgo",
    "kanya": "virgo",
    "libra": "libra",
    "tula": "libra",
    "scorpio": "scorpio",
    "vrischika": "scorpio",
    "vrishchik": "scorpio",
    "sagittarius": "sagittarius",
    "dhanu": "sagittarius",
    "capricorn": "capricorn",
    "makara": "capricorn",
    "makar": "capricorn",
    "aquarius": "aquarius",
    "kumbha": "aquarius",
    "kumbh": "aquarius",
    "मेष": "aries",
    "वृषभ": "taurus",
    "मिथुन": "gemini",
    "कर्क": "cancer",
    "सिंह": "leo",
    "कन्या": "virgo",
    "तुला": "libra",
    "वृश्चिक": "scorpio",
    "धनु": "sagittarius",
    "मकर": "capricorn",
    "कुंभ": "aquarius",
    "कुम्भ": "aquarius",
    "मीन": "pisces",
    "pisces": "pisces",
    "meena": "pisces",
    "meen": "pisces",
}
_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
}
DIGNITY_WORDS = {
    "exalted": "exalted",
    "exaltation": "exalted",
    "debilitated": "debilitated",
    "debilitation": "debilitated",
    "own sign": "own_sign",
}
PALM_LINES = {
    "life": "life",
    "head": "head",
    "heart": "heart",
    "fate": "fate",
    "destiny": "fate",
    "sun": "apollo",
    "apollo": "apollo",
    "mercury": "mercury",
}
PALM_MOUNTS = {
    "jupiter": "jupiter",
    "saturn": "saturn",
    "apollo": "apollo",
    "sun": "apollo",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "moon": "moon",
    "luna": "moon",
}

# Life topics. A topic may be mentioned in an interpretation only if the cited rule's tags carry it;
# a plain fact (a placement, a palm feature) carries no topic at all. Prefix matched.
TOPICS: dict[str, tuple[str, ...]] = {
    "ambition": ("ambiti",),
    "fortune": ("fortun",),
    "merit": ("merit",),
    "wealth": ("wealth", "rich", "money", "financ", "prosper", "income"),
    "career": ("career", "profession", "occupation", "job", "vocation"),
    "marriage": ("marri", "spouse", "wedding", "wedlock"),
    "relationship": ("relationship", "romanc", "partner"),
    "love": ("love",),
    "children": ("child", "offspring"),
    "education": ("educat", "scholar", "learning", "study"),
    "travel": ("travel", "abroad", "foreign", "journey"),
    "leadership": ("leader",),
    "creativity": ("creativ", "artistic"),
    "communication": ("communicat",),
    "status": ("fame", "reputation", "status"),
    "family": ("family", "mother", "father", "sibling"),
    "spiritual": ("spiritual", "devotion"),
}
_POSITIVE = (
    "favourable",
    "favorable",
    "auspicious",
    "beneficial",
    "supportive",
    "fortunate",
    "positive",
    "blessed",
    "lucky",
    "excellent",
    "successful",
    "prosperous",
    "happy",
)
_NEGATIVE = (
    "challenging",
    "difficult",
    "inauspicious",
    "harmful",
    "unfortunate",
    "negative",
    "unlucky",
    "troubled",
    "afflict",
    "malefic",
    "problematic",
    "unhappy",
    "doomed",
)
# Words that turn a stated fact into an outcome or a judgement. A fact has none of these.
_OUTCOME = (
    "strong",
    "weak",
    "good",
    "bad",
    "great",
    "powerful",
    "brings",
    "causes",
    "leads to",
    "results in",
    "therefore",
    "as a result",
    "because of this",
    "means that",
    "makes you",
    "makes the",
    "gives you",
    "you are",
    "you have",
    "you will",
    "you may become",
)
_CERTAINTY = re.compile(
    r"\b(will definitely|will certainly|will surely|definitely will|certainly will|"
    r"guarantee[sd]?|guaranteed|for sure|without (?:a )?doubt|inevitabl[ey]|"
    r"destined to|is destined|are destined|bound to|100%|"
    r"will (?:happen|occur|come true|become|marry|earn|get|achieve|succeed|die|inherit)|"
    r"is going to happen)\b",
    re.IGNORECASE,
)
_FRAMING = re.compile(
    r"\b(tradition\w*|according to|accord\w+ to|sources?|texts?|classical|regards?|regarded|"
    r"considers?|considered|treats?|treated|reads?|interprets?|interpret\w*|indicat\w+|"
    r"suggests?|signif\w+|said to|is taken|are taken|holds? that|ascribes?|attributes?|"
    r"associates?|associated|views?)\b",
    re.IGNORECASE,
)
_OBSERVATION_MARKERS = re.compile(
    r"\b(observed|seen|spotted|detected in the image|visible in the image|directly visible|"
    r"directly observed|identified in the image)\b",
    re.IGNORECASE,
)
_DERIVATION_MARKERS = re.compile(
    r"\b(derived|computed|calculated|inferred|estimated|deduced|worked out)\b", re.IGNORECASE
)

_WORD = r"(?:[^\W_]|[ऀ-ॿ])+"
_TOKEN = re.compile(_WORD + r"(?:'" + _WORD + r")?", re.UNICODE)
_SENTENCE_SPLIT = re.compile(r"[.;!?\n]+")
_HOUSE_NUM = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?[\s-]+house\b|\bhouse[\s-]+(?:no\.?\s*)?(\d{1,2})\b"
)
_HOUSE_WORD = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)"
    r"[\s-]+house\b"
)
_NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?:st|nd|rd|th)?(?![\w.])")
_RETRO_NEG = re.compile(r"\b(not retrograde|direct(?: motion)?|not in retrograde)\b")
_RETRO_POS = re.compile(r"\bretrograde\b|\bvakri\b|\bवक्री\b")


def normalize(text: str) -> str:
    """NFKC, lower case, with whitespace collapsed. Devanagari combining marks are kept."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).lower()).strip()


def alnum_only(text: str) -> str:
    """Lower case, letters and digits only; used for source-name attribution matching."""
    return "".join(ch for ch in normalize(text) if ch.isalnum())


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


# -- analysis result -----------------------------------------------------------------------------


@dataclass
class Binding:
    """What one sentence asserts about one entity (a planet, or the lagna)."""

    entity: str
    signs: set[str] = field(default_factory=set)
    houses: set[int] = field(default_factory=set)
    dignities: set[str] = field(default_factory=set)
    retrograde: set[bool] = field(default_factory=set)


@dataclass
class TextAnalysis:
    normalized: str
    planets: set[str] = field(default_factory=set)
    signs: set[str] = field(default_factory=set)
    houses: set[int] = field(default_factory=set)
    dignities: set[str] = field(default_factory=set)
    bindings: dict[str, Binding] = field(default_factory=dict)
    unbound_signs: set[str] = field(default_factory=set)
    unbound_houses: set[int] = field(default_factory=set)
    unbound_dignities: set[str] = field(default_factory=set)
    hands: set[str] = field(default_factory=set)
    lines: set[str] = field(default_factory=set)
    mounts: set[str] = field(default_factory=set)
    topics: set[str] = field(default_factory=set)
    numbers: set[str] = field(default_factory=set)
    positive: bool = False
    negative: bool = False
    outcome_words: bool = False
    certainty: bool = False
    framed: bool = False
    observation_language: bool = False
    derivation_language: bool = False
    token_count: int = 0
    recognised_count: int = 0

    @property
    def coverage_bp(self) -> int:
        if not self.token_count:
            return 0
        return min(10000, (self.recognised_count * 10000) // self.token_count)

    @property
    def checkable_atoms(self) -> int:
        return (
            len(self.planets)
            + len(self.signs)
            + len(self.houses)
            + len(self.dignities)
            + len(self.hands)
            + len(self.lines)
            + len(self.mounts)
        )


def _contains_any(text: str, stems: tuple[str, ...]) -> bool:
    return any(re.search(r"\b" + re.escape(s), text) for s in stems)


def _recognised_tokens(analysis: TextAnalysis, toks: list[str]) -> int:
    known = set(PLANETS) | set(SIGNS) | set(_ORDINALS) | set(DIGNITY_WORDS)
    count = 0
    for t in toks:
        if (
            t in known
            or t.isdigit()
            or t in {"left", "right", "house", "retrograde", "line", "mount", "mounts", "hand"}
        ):
            count += 1
        elif any(t.startswith(stem) for stems in TOPICS.values() for stem in stems):
            count += 1
    return count


def analyze(text: str) -> TextAnalysis:
    norm = normalize(text)
    toks = _TOKEN.findall(norm)
    a = TextAnalysis(normalized=norm, token_count=len(toks))

    a.positive = any(re.search(r"\b" + w, norm) for w in _POSITIVE)
    a.negative = any(re.search(r"\b" + w, norm) for w in _NEGATIVE)
    a.outcome_words = any(re.search(r"\b" + re.escape(w) + r"\b", norm) for w in _OUTCOME)
    a.certainty = bool(_CERTAINTY.search(norm))
    a.framed = bool(_FRAMING.search(norm))
    a.observation_language = bool(_OBSERVATION_MARKERS.search(norm))
    a.derivation_language = bool(_DERIVATION_MARKERS.search(norm))
    for topic, stems in TOPICS.items():
        if _contains_any(norm, stems):
            a.topics.add(topic)

    for hand in ("left", "right"):
        if re.search(rf"\b{hand}[\s-]+(?:hand|palm)\b|\b(?:hand|palm) is {hand}\b", norm):
            a.hands.add(hand.upper())
    for pattern in (r"\b([a-z]+)\s+line\b", r"\bline of\s+([a-z]+)\b"):
        for m in re.finditer(pattern, norm):
            name = PALM_LINES.get(m.group(1))
            if name:
                a.lines.add(name)
    for pattern in (r"\bmounts?\s+(?:of\s+)?([a-z]+)\b", r"\b([a-z]+)\s+mount\b"):
        for m in re.finditer(pattern, norm):
            name = PALM_MOUNTS.get(m.group(1))
            if name:
                a.mounts.add(name)

    house_numbers: set[int] = set()
    for sentence in _SENTENCE_SPLIT.split(norm):
        sentence = sentence.strip()
        if not sentence:
            continue
        _analyze_sentence(a, sentence, house_numbers)

    # numbers that are not house numbers (those are checked as placements)
    for m in _NUMBER.finditer(norm):
        raw = m.group(1)
        if raw.isdigit() and int(raw) in house_numbers:
            continue
        a.numbers.add(raw)
    a.recognised_count = _recognised_tokens(a, toks)
    return a


def _analyze_sentence(a: TextAnalysis, sentence: str, house_numbers: set[int]) -> None:
    # ordered events: (position, kind, value)
    events: list[tuple[int, str, object]] = []
    for m in re.finditer(_WORD, sentence, re.UNICODE):
        word = m.group(0)
        if word in PLANETS:
            events.append((m.start(), "planet", PLANETS[word]))
        elif word in SIGNS:
            events.append((m.start(), "sign", SIGNS[word]))
        elif word in {"lagna", "ascendant", "लग्न"}:
            events.append((m.start(), "planet", "lagna"))
    for m in _HOUSE_NUM.finditer(sentence):
        number = int(m.group(1) or m.group(2))
        if 1 <= number <= 12:
            house_numbers.add(number)
            events.append((m.start(), "house", number))
    for m in _HOUSE_WORD.finditer(sentence):
        events.append((m.start(), "house", _ORDINALS[m.group(1)]))
    for phrase, dignity in DIGNITY_WORDS.items():
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", sentence):
            events.append((m.start(), "dignity", dignity))
    for m in _RETRO_NEG.finditer(sentence):
        events.append((m.start(), "retro", False))
    for m in _RETRO_POS.finditer(sentence):
        negated = any(n.start() <= m.start() < n.end() + 1 for n in _RETRO_NEG.finditer(sentence))
        if not negated:
            events.append((m.start(), "retro", True))
    events.sort(key=lambda e: e[0])

    current: str | None = None
    for _, kind, value in events:
        if kind == "planet":
            assert isinstance(value, str)
            current = value
            a.planets.add(value)
            a.bindings.setdefault(value, Binding(value))
            continue
        if kind == "sign":
            assert isinstance(value, str)
            a.signs.add(value)
            if current is None:
                a.unbound_signs.add(value)
            else:
                a.bindings[current].signs.add(value)
        elif kind == "house":
            assert isinstance(value, int)
            a.houses.add(value)
            if current is None:
                a.unbound_houses.add(value)
            else:
                a.bindings[current].houses.add(value)
        elif kind == "dignity":
            assert isinstance(value, str)
            a.dignities.add(value)
            if current is None:
                a.unbound_dignities.add(value)
            else:
                a.bindings[current].dignities.add(value)
        elif kind == "retro" and current is not None:
            assert isinstance(value, bool)
            a.bindings[current].retrograde.add(value)
