"""Tarot foundation (Phase 9 WP-I; `docs/ASTROLOGY_STANDARDS.md` v1.19.0,
"Tarot standards", TA-01 to TA-10).

The Waite-Smith 78-card deck (names and Waite's numbering only), three
spread definitions, seeded deterministic draws and user-selected layouts.
Not an astronomical calculation and not astrology: it lives in astro-engine
because this is the deterministic-computation service and the Phase 9
systems are kept together as isolated modules. No card meanings, no
interpretation, no system randomness.
"""

from pandit_astro_engine.tarot.deck import (
    CARDS_BY_ID,
    CELTIC_CROSS_ID,
    SINGLE_CARD_ID,
    SPREADS,
    THREE_CARD_ID,
    WAITE_SMITH_DECK,
    WAITE_SMITH_DECK_ID,
    Arcana,
    Card,
    Rank,
    SpreadDef,
    SpreadPosition,
    Suit,
)
from pandit_astro_engine.tarot.service import (
    TAROT_STANDARDS_VERSION,
    TAROT_SYSTEM_ID,
    DrawMethod,
    PlacedCard,
    SelectedCard,
    TarotDrawRequest,
    TarotLayout,
    TarotSelectionRequest,
    TarotService,
)

__all__ = [
    "CARDS_BY_ID",
    "CELTIC_CROSS_ID",
    "SINGLE_CARD_ID",
    "SPREADS",
    "TAROT_STANDARDS_VERSION",
    "TAROT_SYSTEM_ID",
    "THREE_CARD_ID",
    "WAITE_SMITH_DECK",
    "WAITE_SMITH_DECK_ID",
    "Arcana",
    "Card",
    "DrawMethod",
    "PlacedCard",
    "Rank",
    "SelectedCard",
    "SpreadDef",
    "SpreadPosition",
    "Suit",
    "TarotDrawRequest",
    "TarotLayout",
    "TarotSelectionRequest",
    "TarotService",
]
