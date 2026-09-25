"""Tarot layouts (Phase 9 WP-I; `docs/ASTROLOGY_STANDARDS.md` v1.19.0,
TA-01 to TA-10).

    TarotDrawRequest      -> TarotService.draw    -> TarotLayout  (seeded)
    TarotSelectionRequest -> TarotService.select  -> TarotLayout  (user-chosen)

A layout says which card lies in which position and whether it is
reversed. It carries no meaning: card interpretation is out of scope here
(Waite's divinatory meanings are not stored), and a layout is never a
prediction or a substitute for medical, legal, financial or safety advice.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine._version import __version__
from pandit_astro_engine.tarot.deck import (
    CARDS_BY_ID,
    DECKS,
    SPREADS,
    WAITE_SMITH_DECK_ID,
    Card,
    SpreadDef,
)
from pandit_astro_engine.tarot.draw import STREAM_ID, seed_digest, seeded_shuffle

TAROT_STANDARDS_VERSION = "1.19.0"
TAROT_SYSTEM_ID = "tarot"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DrawMethod(str, Enum):
    SEEDED_SHUFFLE = "seeded_shuffle"
    USER_SELECTED = "user_selected"


class TarotDrawRequest(_Model):
    """`allow_reversals` has no default: Waite turns some cards round before
    shuffling, but whether a product reading uses reversals is a choice the
    caller must make. `significator_card_id` is required by the Celtic
    method and must be chosen explicitly; it is never inferred (Waite picks it
    by sex and age, which Pandit Ji does not collect)."""

    spread_id: str
    seed: str = Field(..., min_length=1)
    allow_reversals: bool
    deck_id: str = WAITE_SMITH_DECK_ID
    significator_card_id: str | None = None

    @model_validator(mode="after")
    def _check(self) -> TarotDrawRequest:
        _check_spread_and_deck(self.spread_id, self.deck_id, self.significator_card_id)
        return self


class SelectedCard(_Model):
    card_id: str
    reversed: bool


class TarotSelectionRequest(_Model):
    """Cards the user picked, in position order, kept exactly as given."""

    spread_id: str
    cards: tuple[SelectedCard, ...]
    deck_id: str = WAITE_SMITH_DECK_ID
    significator_card_id: str | None = None

    @model_validator(mode="after")
    def _check(self) -> TarotSelectionRequest:
        spread = _check_spread_and_deck(self.spread_id, self.deck_id, self.significator_card_id)
        if len(self.cards) != len(spread.positions):
            raise ValueError(
                f"{self.spread_id} needs {len(spread.positions)} cards, got {len(self.cards)}"
            )
        ids = [c.card_id for c in self.cards]
        if self.significator_card_id is not None:
            ids.append(self.significator_card_id)
        unknown = [i for i in ids if i not in CARDS_BY_ID]
        if unknown:
            raise ValueError(f"unknown card ids: {unknown}")
        if len(set(ids)) != len(ids):
            raise ValueError("a card may appear only once in a layout (including the significator)")
        return self


def _check_spread_and_deck(spread_id: str, deck_id: str, significator: str | None) -> SpreadDef:
    if deck_id not in DECKS:
        raise ValueError(f"unknown deck_id {deck_id!r}; supported: {sorted(DECKS)}")
    if spread_id not in SPREADS:
        raise ValueError(f"unknown spread_id {spread_id!r}; supported: {sorted(SPREADS)}")
    spread = SPREADS[spread_id]
    if spread.uses_significator and significator is None:
        raise ValueError(f"{spread_id} needs an explicitly chosen significator_card_id")
    if not spread.uses_significator and significator is not None:
        raise ValueError(f"{spread_id} has no significator")
    if significator is not None and significator not in CARDS_BY_ID:
        raise ValueError(f"unknown significator_card_id {significator!r}")
    return spread


class PlacedCard(_Model):
    index: int
    position_id: str
    position_label: str
    card: Card
    reversed: bool


class TarotProvenance(_Model):
    item: str
    evidence_label: str
    statement: str
    source_id: str
    locator: str
    verification_level: str


_DECK_PROVENANCE = TarotProvenance(
    item=WAITE_SMITH_DECK_ID,
    evidence_label="source_supported",
    statement="78 cards: Trumps Major 0-XXI in Waite's numbering; Wands, Cups, Swords, "
    "Pentacles, King to Ace",
    source_id="SRC-WAITE-PICTORIAL-KEY-1911",
    locator="Pictorial Key, Part II trump headings; Part III suits",
    verification_level="WEB-TRANSCRIPTION-ORIGINAL-ENGLISH",
)
_STREAM_PROVENANCE = TarotProvenance(
    item=STREAM_ID,
    evidence_label="engineering_convention",
    statement="Caller-seeded SHA-256 counter stream, rejection sampling, Fisher-Yates shuffle",
    source_id="PANDIT-JI",
    locator="docs/ASTROLOGY_STANDARDS.md TA-04 to TA-06",
    verification_level="PROJECT_DERIVED",
)


def _spread_provenance(spread: SpreadDef) -> TarotProvenance:
    source = "SRC-WAITE-PICTORIAL-KEY-1911" if spread.source_locator else "PANDIT-JI"
    return TarotProvenance(
        item=spread.spread_id,
        evidence_label=spread.evidence_label,
        statement=spread.title,
        source_id=source,
        locator=spread.source_locator or "docs/ASTROLOGY_STANDARDS.md TA-03",
        verification_level="WEB-TRANSCRIPTION-ORIGINAL-ENGLISH"
        if spread.source_locator
        else "PROJECT_DERIVED",
    )


class TarotLayout(_Model):
    system: str = TAROT_SYSTEM_ID
    standards_version: str = TAROT_STANDARDS_VERSION
    engine_version: str
    deck_id: str
    spread_id: str
    draw_method: DrawMethod
    stream_id: str | None = None
    seed_sha256: str | None = None
    reversals_allowed: bool | None = None
    significator: Card | None = None
    placements: tuple[PlacedCard, ...]
    interpretation: None = None
    provenance: tuple[TarotProvenance, ...] = ()
    notice: str = (
        "A Tarot layout is a traditional practice, not a verified statement about the future, "
        "and not medical, legal, financial or safety advice."
    )


class TarotService:
    """Stateless; no ephemeris and no system randomness."""

    def draw(self, request: TarotDrawRequest) -> TarotLayout:
        spread = SPREADS[request.spread_id]
        pack = [c.card_id for c in DECKS[request.deck_id]]
        if request.significator_card_id is not None:
            pack.remove(request.significator_card_id)
        shuffled, stream = seeded_shuffle(pack, request.seed)
        placements = []
        for position, card_id in zip(spread.positions, shuffled, strict=False):
            is_reversed = bool(stream.below(2)) if request.allow_reversals else False
            placements.append(
                PlacedCard(
                    index=position.index,
                    position_id=position.position_id,
                    position_label=position.label,
                    card=CARDS_BY_ID[card_id],
                    reversed=is_reversed,
                )
            )
        return TarotLayout(
            engine_version=__version__,
            deck_id=request.deck_id,
            spread_id=spread.spread_id,
            draw_method=DrawMethod.SEEDED_SHUFFLE,
            stream_id=STREAM_ID,
            seed_sha256=seed_digest(request.seed),
            reversals_allowed=request.allow_reversals,
            significator=CARDS_BY_ID[request.significator_card_id]
            if request.significator_card_id
            else None,
            placements=tuple(placements),
            provenance=(_DECK_PROVENANCE, _spread_provenance(spread), _STREAM_PROVENANCE),
        )

    def select(self, request: TarotSelectionRequest) -> TarotLayout:
        spread = SPREADS[request.spread_id]
        return TarotLayout(
            engine_version=__version__,
            deck_id=request.deck_id,
            spread_id=spread.spread_id,
            draw_method=DrawMethod.USER_SELECTED,
            significator=CARDS_BY_ID[request.significator_card_id]
            if request.significator_card_id
            else None,
            placements=tuple(
                PlacedCard(
                    index=position.index,
                    position_id=position.position_id,
                    position_label=position.label,
                    card=CARDS_BY_ID[chosen.card_id],
                    reversed=chosen.reversed,
                )
                for position, chosen in zip(spread.positions, request.cards, strict=True)
            ),
            provenance=(_DECK_PROVENANCE, _spread_provenance(spread)),
        )
