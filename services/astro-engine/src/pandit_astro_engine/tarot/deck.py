"""Tarot deck and spread registries (Phase 9 WP-I; `docs/ASTROLOGY_STANDARDS.md`
v1.19.0, TA-01 to TA-10; sources in `research/ASTROLOGY_SOURCES.md` Group 20).

Deck `TAROT_DECK_WAITE_SMITH_1910`: A. E. Waite, *The Pictorial Key to the
Tarot* (1910/1911; public domain; English Wikisource transcription): 22
Trumps Major numbered 0 (The Fool) to XXI with Strength VIII and Justice XI
("this card has been interchanged with that of Justice, which is usually
numbered eight"), and 56 Lesser Arcana in the suits Wands, Cups, Swords and
Pentacles, King to Ace. Only names and numbers are held; no meanings, no
images.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Arcana(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


class Suit(str, Enum):
    WANDS = "wands"
    CUPS = "cups"
    SWORDS = "swords"
    PENTACLES = "pentacles"


class Rank(str, Enum):
    ACE = "ace"
    TWO = "two"
    THREE = "three"
    FOUR = "four"
    FIVE = "five"
    SIX = "six"
    SEVEN = "seven"
    EIGHT = "eight"
    NINE = "nine"
    TEN = "ten"
    PAGE = "page"
    KNIGHT = "knight"
    QUEEN = "queen"
    KING = "king"


class Card(_Model):
    card_id: str
    name: str
    arcana: Arcana
    number: int | None = None
    suit: Suit | None = None
    rank: Rank | None = None


WAITE_SMITH_DECK_ID = "TAROT_DECK_WAITE_SMITH_1910"

#: Waite, Pictorial Key Part II headings, in Waite's numbering.
_TRUMPS: tuple[tuple[int, str, str], ...] = (
    (0, "fool", "The Fool"),
    (1, "magician", "The Magician"),
    (2, "high_priestess", "The High Priestess"),
    (3, "empress", "The Empress"),
    (4, "emperor", "The Emperor"),
    (5, "hierophant", "The Hierophant"),
    (6, "lovers", "The Lovers"),
    (7, "chariot", "The Chariot"),
    (8, "strength", "Strength"),
    (9, "hermit", "The Hermit"),
    (10, "wheel_of_fortune", "Wheel of Fortune"),
    (11, "justice", "Justice"),
    (12, "hanged_man", "The Hanged Man"),
    (13, "death", "Death"),
    (14, "temperance", "Temperance"),
    (15, "devil", "The Devil"),
    (16, "tower", "The Tower"),
    (17, "star", "The Star"),
    (18, "moon", "The Moon"),
    (19, "sun", "The Sun"),
    (20, "last_judgment", "The Last Judgment"),
    (21, "world", "The World"),
)


def _build_deck() -> tuple[Card, ...]:
    cards = [
        Card(
            card_id=f"major_{n:02d}_{slug}",
            name=name,
            arcana=Arcana.MAJOR,
            number=n,
        )
        for n, slug, name in _TRUMPS
    ]
    for suit in Suit:
        for rank in Rank:
            cards.append(
                Card(
                    card_id=f"{suit.value}_{rank.value}",
                    name=f"{rank.value.title()} of {suit.value.title()}",
                    arcana=Arcana.MINOR,
                    suit=suit,
                    rank=rank,
                )
            )
    return tuple(cards)


WAITE_SMITH_DECK: tuple[Card, ...] = _build_deck()
CARDS_BY_ID: dict[str, Card] = {c.card_id: c for c in WAITE_SMITH_DECK}
DECKS: dict[str, tuple[Card, ...]] = {WAITE_SMITH_DECK_ID: WAITE_SMITH_DECK}


class SpreadPosition(_Model):
    index: int
    position_id: str
    label: str


class SpreadDef(_Model):
    spread_id: str
    title: str
    evidence_label: str
    source_locator: str
    positions: tuple[SpreadPosition, ...]
    uses_significator: bool = False


CELTIC_CROSS_ID = "TAROT_SPREAD_WAITE_CELTIC_METHOD_1910"
SINGLE_CARD_ID = "TAROT_SPREAD_SINGLE_CARD"
THREE_CARD_ID = "TAROT_SPREAD_THREE_CARD_UNLABELLED"

_CELTIC_LABELS: tuple[tuple[str, str], ...] = (
    ("covers", "This covers him"),
    ("crosses", "This crosses him"),
    ("crowns", "This crowns him"),
    ("beneath", "This is beneath him"),
    ("behind", "This is behind him"),
    ("before", "This is before him"),
    ("himself", "Himself"),
    ("his_house", "His house"),
    ("hopes_or_fears", "His hopes or fears"),
    ("what_will_come", "What will come"),
)

SPREADS: dict[str, SpreadDef] = {
    CELTIC_CROSS_ID: SpreadDef(
        spread_id=CELTIC_CROSS_ID,
        title="An Ancient Celtic Method of Divination (Waite), ten cards around a Significator",
        evidence_label="source_supported",
        source_locator="Pictorial Key, Part III, 'An Ancient Celtic Method of Divination'",
        positions=tuple(
            SpreadPosition(index=i + 1, position_id=pid, label=label)
            for i, (pid, label) in enumerate(_CELTIC_LABELS)
        ),
        uses_significator=True,
    ),
    SINGLE_CARD_ID: SpreadDef(
        spread_id=SINGLE_CARD_ID,
        title="One card (Pandit Ji engineering convention; no source spread)",
        evidence_label="engineering_convention",
        source_locator="",
        positions=(SpreadPosition(index=1, position_id="card_1", label="Card 1"),),
    ),
    THREE_CARD_ID: SpreadDef(
        spread_id=THREE_CARD_ID,
        title=(
            "Three cards with no assigned position meanings (Pandit Ji engineering convention; "
            "the popular past/present/future labels are not sourced and not used)"
        ),
        evidence_label="engineering_convention",
        source_locator="",
        positions=tuple(
            SpreadPosition(index=i, position_id=f"card_{i}", label=f"Card {i}") for i in (1, 2, 3)
        ),
    ),
}
