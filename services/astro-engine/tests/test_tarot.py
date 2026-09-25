"""Tarot foundation (Phase 9 WP-I, TA-01 to TA-10): deck integrity against
Waite's Pictorial Key (Part II trump headings, Part III suits and the Celtic
method), determinism and isolation of randomness, user-selected layouts and
validation."""

from __future__ import annotations

import ast
import hashlib
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from pandit_astro_engine.tarot import (
    CARDS_BY_ID,
    CELTIC_CROSS_ID,
    SINGLE_CARD_ID,
    SPREADS,
    THREE_CARD_ID,
    WAITE_SMITH_DECK,
    Arcana,
    DrawMethod,
    SelectedCard,
    Suit,
    TarotDrawRequest,
    TarotSelectionRequest,
    TarotService,
)
from pandit_astro_engine.tarot.draw import _SeededStream, seeded_shuffle

SRC = Path(__file__).parents[1] / "src" / "pandit_astro_engine" / "tarot"
SERVICE = TarotService()

#: Waite, Pictorial Key Part II, trump headings in his numbering (0 = The Fool).
WAITE_TRUMPS = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance", "The Devil",
    "The Tower", "The Star", "The Moon", "The Sun", "The Last Judgment", "The World",
]  # fmt: skip


def test_deck_has_78_unique_cards() -> None:
    assert len(WAITE_SMITH_DECK) == 78
    assert len({c.card_id for c in WAITE_SMITH_DECK}) == 78
    assert len(CARDS_BY_ID) == 78


def test_trumps_follow_waite_numbering() -> None:
    majors = [c for c in WAITE_SMITH_DECK if c.arcana is Arcana.MAJOR]
    assert [c.number for c in majors] == list(range(22))
    assert [c.name for c in majors] == WAITE_TRUMPS
    by_name = {c.name: c.number for c in majors}
    assert by_name["Strength"] == 8 and by_name["Justice"] == 11


def test_minor_arcana() -> None:
    minors = [c for c in WAITE_SMITH_DECK if c.arcana is Arcana.MINOR]
    assert len(minors) == 56
    assert Counter(c.suit for c in minors) == {s: 14 for s in Suit}
    assert CARDS_BY_ID["pentacles_king"].name == "King of Pentacles"
    assert CARDS_BY_ID["wands_ace"].name == "Ace of Wands"


def test_celtic_method_positions_follow_waite() -> None:
    spread = SPREADS[CELTIC_CROSS_ID]
    assert spread.uses_significator
    assert [p.label for p in spread.positions] == [
        "This covers him",
        "This crosses him",
        "This crowns him",
        "This is beneath him",
        "This is behind him",
        "This is before him",
        "Himself",
        "His house",
        "His hopes or fears",
        "What will come",
    ]
    assert [p.index for p in spread.positions] == list(range(1, 11))


def _draw(seed: str, spread: str = SINGLE_CARD_ID, reversals: bool = True, sig: str | None = None):  # type: ignore[no-untyped-def]
    return SERVICE.draw(
        TarotDrawRequest(
            spread_id=spread, seed=seed, allow_reversals=reversals, significator_card_id=sig
        )
    )


def test_draw_is_deterministic_and_seed_sensitive() -> None:
    a = _draw("session-42", CELTIC_CROSS_ID, sig="major_00_fool")
    b = _draw("session-42", CELTIC_CROSS_ID, sig="major_00_fool")
    c = _draw("session-43", CELTIC_CROSS_ID, sig="major_00_fool")
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
    assert [p.card.card_id for p in a.placements] != [p.card.card_id for p in c.placements]
    assert a.draw_method is DrawMethod.SEEDED_SHUFFLE
    assert a.seed_sha256 == hashlib.sha256(b"session-42").hexdigest()
    assert "session-42" not in a.model_dump_json()


def test_layout_has_no_duplicates_and_excludes_the_significator() -> None:
    for k in range(50):
        layout = _draw(f"s{k}", CELTIC_CROSS_ID, sig="cups_queen")
        ids = [p.card.card_id for p in layout.placements]
        assert len(ids) == 10 == len(set(ids))
        assert "cups_queen" not in ids
        assert layout.significator is not None and layout.significator.card_id == "cups_queen"


def test_stream_matches_sha256_counter_definition() -> None:
    stream = _SeededStream("abc")
    key = hashlib.sha256(b"pandit-tarot|abc").digest()
    block = hashlib.sha256(key + (0).to_bytes(8, "big")).digest()
    first = int.from_bytes(block[:4], "big")
    limit = (2**32 // 78) * 78
    assert first < limit  # this seed's first word is accepted
    assert stream.below(78) == first % 78


def test_shuffle_is_a_permutation_and_roughly_uniform() -> None:
    items = [c.card_id for c in WAITE_SMITH_DECK]
    counts: Counter[str] = Counter()
    for k in range(7800):
        shuffled, _ = seeded_shuffle(items, f"u{k}")
        assert sorted(shuffled) == sorted(items)
        counts[shuffled[0]] += 1
    # Expected 100 per card; a loose band that a correct shuffle passes with overwhelming
    # probability and a biased one (for example modulo bias or a fixed card) fails.
    assert len(counts) == 78
    assert all(55 <= n <= 150 for n in counts.values())


def test_reversals() -> None:
    upright = [_draw(f"r{k}", THREE_CARD_ID, reversals=False) for k in range(20)]
    assert not any(p.reversed for layout in upright for p in layout.placements)
    mixed = [p.reversed for k in range(400) for p in _draw(f"r{k}", THREE_CARD_ID).placements]
    assert 480 <= sum(mixed) <= 720  # 1200 flips, expected 600


def test_user_selection_is_preserved() -> None:
    chosen = (
        SelectedCard(card_id="swords_three", reversed=True),
        SelectedCard(card_id="major_17_star", reversed=False),
        SelectedCard(card_id="wands_page", reversed=False),
    )
    layout = SERVICE.select(TarotSelectionRequest(spread_id=THREE_CARD_ID, cards=chosen))
    assert layout.draw_method is DrawMethod.USER_SELECTED
    assert [(p.card.card_id, p.reversed) for p in layout.placements] == [
        (c.card_id, c.reversed) for c in chosen
    ]
    assert layout.seed_sha256 is None and layout.interpretation is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"spread_id": "TAROT_SPREAD_UNKNOWN"},
        {"deck_id": "TAROT_DECK_MARSEILLE"},
        {"spread_id": CELTIC_CROSS_ID},  # no significator
        {"significator_card_id": "major_00_fool"},  # single card has none
        {"seed": ""},
    ],
)
def test_draw_validation(kwargs: dict[str, object]) -> None:
    base: dict[str, object] = {"spread_id": SINGLE_CARD_ID, "seed": "x", "allow_reversals": True}
    base.update(kwargs)
    with pytest.raises(ValidationError):
        TarotDrawRequest(**base)  # type: ignore[arg-type]


def test_reversals_have_no_default() -> None:
    with pytest.raises(ValidationError):
        TarotDrawRequest(spread_id=SINGLE_CARD_ID, seed="x")  # type: ignore[call-arg]


def test_selection_validation() -> None:
    card = SelectedCard(card_id="cups_ace", reversed=False)
    with pytest.raises(ValidationError):  # wrong count
        TarotSelectionRequest(spread_id=THREE_CARD_ID, cards=(card,))
    with pytest.raises(ValidationError):  # duplicate
        TarotSelectionRequest(spread_id=THREE_CARD_ID, cards=(card, card, card))
    with pytest.raises(ValidationError):  # unknown card
        TarotSelectionRequest(
            spread_id=SINGLE_CARD_ID, cards=(SelectedCard(card_id="cups_zero", reversed=False),)
        )
    with pytest.raises(ValidationError):  # significator repeated in the layout
        TarotSelectionRequest(
            spread_id=CELTIC_CROSS_ID,
            cards=tuple(
                SelectedCard(card_id=c.card_id, reversed=False) for c in WAITE_SMITH_DECK[:10]
            ),
            significator_card_id=WAITE_SMITH_DECK[0].card_id,
        )


def test_no_system_randomness_or_clock() -> None:
    forbidden = {"random", "secrets", "os", "time", "datetime", "uuid", "numpy"}
    for path in SRC.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            assert not (set(names) & forbidden), (path.name, names)


def test_layouts_carry_provenance() -> None:
    drawn = _draw("prov", CELTIC_CROSS_ID, sig="major_00_fool")
    assert [p.item for p in drawn.provenance] == [
        "TAROT_DECK_WAITE_SMITH_1910",
        CELTIC_CROSS_ID,
        "SHA256_COUNTER_REJECTION_V1",
    ]
    assert drawn.provenance[0].source_id == "SRC-WAITE-PICTORIAL-KEY-1911"
    single = _draw("prov")
    assert single.provenance[1].evidence_label == "engineering_convention"
    chosen = SERVICE.select(
        TarotSelectionRequest(
            spread_id=SINGLE_CARD_ID, cards=(SelectedCard(card_id="cups_ace", reversed=False),)
        )
    )
    assert [p.item for p in chosen.provenance] == ["TAROT_DECK_WAITE_SMITH_1910", SINGLE_CARD_ID]
