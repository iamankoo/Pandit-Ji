"""Phase 11 numerology (`docs/ASTROLOGY_STANDARDS.md` v1.25.0, NU-01 to NU-16):
source tables and worked examples, reduction, master numbers, profile
separation, name normalisation (no transliteration), associated numbers,
deferred interpretation, validation and determinism."""

from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

import pytest
from pydantic import ValidationError

from pandit_astro_engine.numerology import (
    BALLIETT_LETTER_VALUES,
    CHEIRO_LETTER_VALUES,
    DEFAULT_PROFILE,
    ItemReason,
    ItemStatus,
    MasterNumberPolicy,
    NameInput,
    NumerologyFacts,
    NumerologyProfileId,
    NumerologyRequest,
    NumerologySystem,
    calculate_numerology,
    reduce_number,
)
from pandit_astro_engine.numerology.calculator import name_number
from pandit_astro_engine.numerology.constants import RETAINED

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "phase11_source_tables.json").read_text("utf-8")
)
CHALDEAN = NumerologyProfileId.CHALDEAN_CHEIRO_1926
PYTHAGOREAN = NumerologyProfileId.PYTHAGOREAN_BALLIETT_1908
NONE = frozenset[int]()
KEEP = RETAINED[MasterNumberPolicy.RETAIN_11_22]


def _pyth(**kwargs: object) -> NumerologyRequest:
    kwargs.setdefault("master_number_policy", MasterNumberPolicy.NONE)
    return NumerologyRequest(profile=PYTHAGOREAN, **kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def test_cheiro_table_matches_the_printed_page() -> None:
    printed = {
        "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 8, "G": 3, "H": 5, "I": 1, "J": 1,
        "K": 2, "L": 3, "M": 4, "N": 5, "O": 7, "P": 8, "Q": 1, "R": 2, "S": 3, "T": 4,
        "U": 6, "V": 6, "W": 6, "X": 5, "Y": 1, "Z": 7,
    }  # fmt: skip
    assert dict(CHEIRO_LETTER_VALUES) == printed
    assert 9 not in CHEIRO_LETTER_VALUES.values()


def test_balliett_table_is_the_alphabet_in_nine_parts() -> None:
    assert [BALLIETT_LETTER_VALUES[c] for c in "AIJRSZ"] == [1, 9, 1, 9, 1, 8]
    assert len(BALLIETT_LETTER_VALUES) == 26


@pytest.mark.parametrize("word,total", FIXTURE["cheiro_examples"]["words"].items())
def test_cheiro_word_totals(word: str, total: int) -> None:
    assert sum(CHEIRO_LETTER_VALUES[c] for c in word) == total


@pytest.mark.parametrize("name,expected", FIXTURE["cheiro_examples"]["names"].items())
def test_cheiro_name_examples(name: str, expected: list[int]) -> None:
    result = name_number(NameInput(latin_spelling=name), CHALDEAN, NONE)
    assert result.reduction is not None
    assert [result.reduction.chain[0], result.reduction.value] == expected


@pytest.mark.parametrize("word,total", FIXTURE["balliett_examples"]["words"].items())
def test_balliett_word_totals(word: str, total: int) -> None:
    assert sum(BALLIETT_LETTER_VALUES[c] for c in word) == total


def test_balliett_worked_example() -> None:
    example = FIXTURE["balliett_examples"]
    facts = calculate_numerology(
        _pyth(date_of_birth=dt.date(1872, 1, 17), name=NameInput(latin_spelling="Henry Elder"))
    )
    assert facts.name_number.reduction is not None
    assert [facts.name_number.reduction.chain[0], facts.name_number.reduction.value] == example[
        "name_henry_elder"
    ]
    birth = facts.date_numbers[0]
    birth_example = example["birth_17_january_1872"]
    assert birth.item_id == "balliett_birth_number"
    assert birth.inputs == {"month_digit": 1, "day_digit": 8, "year_digit": 9}
    assert birth.reduction is not None
    assert birth.reduction.chain == (birth_example["total"], birth_example["value"])


@pytest.mark.parametrize("word,value", FIXTURE["balliett_examples"]["retained"].items())
def test_balliett_master_numbers_are_kept_only_under_the_retain_policy(
    word: str, value: int
) -> None:
    kept = name_number(NameInput(latin_spelling=word), PYTHAGOREAN, KEEP)
    plain = name_number(NameInput(latin_spelling=word), PYTHAGOREAN, NONE)
    assert kept.reduction is not None and plain.reduction is not None
    assert kept.reduction.value == value and kept.reduction.master_retained
    assert (
        plain.reduction.value == reduce_number(value).value and not plain.reduction.master_retained
    )


# --------------------------------------------------------------------------
# Reduction, Moolank, Bhagyank
# --------------------------------------------------------------------------


def test_reduction_chain_and_compound() -> None:
    assert reduce_number(7).chain == (7,) and reduce_number(7).compound is None
    assert reduce_number(28).chain == (28, 10, 1)
    assert reduce_number(99).chain == (99, 18, 9)
    assert reduce_number(29, KEEP).chain == (29, 11)
    assert reduce_number(22, KEEP).value == 22 and reduce_number(22).value == 4
    with pytest.raises(ValueError):
        reduce_number(0)


@pytest.mark.parametrize("day", [1, 10, 19, 28])
def test_cheiro_birth_number_series(day: int) -> None:
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2000, 1, day)))
    assert facts.moolank.reduction is not None and facts.moolank.reduction.value == 1


def test_moolank_range_and_master_days() -> None:
    for day in range(1, 32):
        facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2001, 1, day)))
        assert facts.moolank.reduction is not None
        assert 1 <= facts.moolank.reduction.value <= 9
    kept = calculate_numerology(
        _pyth(date_of_birth=dt.date(2001, 1, 29), master_number_policy="retain_11_22")
    )
    assert kept.moolank.reduction is not None and kept.moolank.reduction.value == 11


def test_bhagyank_follows_the_phase1_standard() -> None:
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(1990, 6, 15)))
    assert facts.bhagyank.inputs == {"digits": "15061990"}
    assert facts.bhagyank.reduction is not None
    assert facts.bhagyank.reduction.chain == (31, 4)
    assert facts.bhagyank.label.value == "phase1_locked_standard"


def test_boundary_dates() -> None:
    first = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(1, 1, 1)))
    last = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(9999, 12, 31)))
    assert first.bhagyank.reduction is not None and first.bhagyank.reduction.value == 3
    assert last.bhagyank.reduction is not None and last.bhagyank.reduction.chain == (43, 7)
    leap = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2024, 2, 29)))
    assert leap.moolank.reduction is not None and leap.moolank.reduction.value == 2


def test_invalid_dates_are_rejected() -> None:
    with pytest.raises(ValidationError):
        NumerologyRequest.model_validate({"date_of_birth": "2023-02-29"})
    with pytest.raises(ValidationError):
        NumerologyRequest.model_validate({"date_of_birth": "1990-13-01"})


def test_bhagyank_digit_equals_balliett_digit_without_master_numbers() -> None:
    rng = random.Random(11)
    for _ in range(500):
        day = dt.date(1900, 1, 1) + dt.timedelta(days=rng.randrange(0, 73000))
        facts = calculate_numerology(_pyth(date_of_birth=day))
        assert facts.bhagyank.reduction is not None
        assert facts.date_numbers[0].reduction is not None
        assert facts.bhagyank.reduction.value == facts.date_numbers[0].reduction.value


def test_cheiro_separate_date_numbers() -> None:
    example = FIXTURE["cheiro_examples"]["date_numbers_6_june_1866"]
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(1866, 6, 6)))
    day, month, year = facts.date_numbers
    assert day.reduction is not None and day.reduction.value == example["day"]
    assert month.status is ItemStatus.NOT_EVALUABLE
    assert month.reason is ItemReason.CHEIRO_MONTH_NUMBER_BASIS_UNCLEAR
    assert year.reduction is not None
    assert year.reduction.chain == (example["year_total"], example["year"])


# --------------------------------------------------------------------------
# Profiles and master-number policy
# --------------------------------------------------------------------------


def test_default_profile_is_chaldean() -> None:
    assert DEFAULT_PROFILE is CHALDEAN
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2000, 1, 1)))
    assert facts.system is NumerologySystem.CHALDEAN
    assert facts.master_number_policy is MasterNumberPolicy.NONE
    assert facts.methodology_version == "1.0.0" and facts.standards_version == "1.25.0"


def test_master_number_policy_rules() -> None:
    with pytest.raises(ValidationError, match="Chaldean"):
        NumerologyRequest(date_of_birth=dt.date(2000, 1, 1), master_number_policy="retain_11_22")
    with pytest.raises(ValidationError, match="explicit"):
        NumerologyRequest(profile=PYTHAGOREAN, date_of_birth=dt.date(2000, 1, 1))
    with pytest.raises(ValidationError):
        NumerologyRequest(profile=PYTHAGOREAN, master_number_policy="retain_11_22_33")


def test_profiles_are_never_mixed() -> None:
    name = NameInput(latin_spelling="Aniket Raj")
    chaldean = calculate_numerology(NumerologyRequest(name=name))
    pythagorean = calculate_numerology(_pyth(name=name))
    assert [w.letter_values for w in chaldean.name_number.words][0] == (1, 5, 1, 2, 5, 4)
    assert [w.letter_values for w in pythagorean.name_number.words][0] == (1, 5, 9, 2, 5, 2)
    assert chaldean.date_numbers == () and pythagorean.date_numbers == ()
    assert {p.entry_id for p in chaldean.provenance}.isdisjoint(
        {"prov.balliett.letters", "prov.balliett.birth"}
    )
    assert {p.entry_id for p in pythagorean.provenance}.isdisjoint({"prov.cheiro.letters"})


def test_a_request_needs_a_date_or_a_name() -> None:
    with pytest.raises(ValidationError):
        NumerologyRequest()


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------


def test_latin_name_normalisation() -> None:
    result = name_number(NameInput(latin_spelling="  José  O'Brien-Smith "), CHALDEAN, NONE)
    assert result.status is ItemStatus.EVALUATED
    assert result.normalized_words == ("JOSE", "OBRIENSMITH")
    assert any("diacritic" in note for note in result.normalization_notes)
    assert result.input_spelling == "  José  O'Brien-Smith "


def test_initials_count_as_words() -> None:
    result = name_number(NameInput(latin_spelling="J. Smith"), CHALDEAN, NONE)
    assert result.normalized_words == ("J", "SMITH")


@pytest.mark.parametrize("spelling", ["राम शर्मा", "Aniket राज", "Анна"])
def test_non_latin_scripts_are_not_transliterated(spelling: str) -> None:
    result = name_number(NameInput(latin_spelling=spelling), CHALDEAN, NONE)
    assert result.status is ItemStatus.NOT_EVALUABLE
    assert result.reason is ItemReason.NON_LATIN_SCRIPT
    assert result.reduction is None and result.words == ()


@pytest.mark.parametrize("spelling", ["R2D2", "Ann@", "Straße"])
def test_unsupported_characters(spelling: str) -> None:
    result = name_number(NameInput(latin_spelling=spelling), CHALDEAN, NONE)
    assert result.reason is ItemReason.UNSUPPORTED_CHARACTER


def test_empty_and_missing_names() -> None:
    assert name_number(NameInput(latin_spelling=" -. "), CHALDEAN, NONE).reason is (
        ItemReason.NAME_EMPTY
    )
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2000, 1, 1)))
    assert facts.name_number.reason is ItemReason.NAME_NOT_SUPPLIED


def test_hinglish_written_in_latin_letters_is_just_a_latin_spelling() -> None:
    result = name_number(NameInput(latin_spelling="Pooja Kumari"), CHALDEAN, NONE)
    assert result.status is ItemStatus.EVALUATED


# --------------------------------------------------------------------------
# Associated numbers and interpretation
# --------------------------------------------------------------------------


def test_cheiro_associated_numbers() -> None:
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2000, 1, 19)))
    associated = facts.associated_numbers
    assert associated.status is ItemStatus.EVALUATED
    assert associated.own_series_dates == (1, 10, 19, 28)
    assert associated.interchangeable_numbers == (2, 4, 7)
    five = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2000, 1, 14)))
    assert five.associated_numbers.interchangeable_numbers == ()
    assert five.associated_numbers.own_series_dates == (5, 14, 23)


def test_associated_numbers_need_a_date_and_are_deferred_for_pythagorean() -> None:
    no_date = calculate_numerology(NumerologyRequest(name=NameInput(latin_spelling="Ann")))
    assert no_date.associated_numbers.reason is ItemReason.DATE_OF_BIRTH_NOT_SUPPLIED
    pyth = calculate_numerology(_pyth(date_of_birth=dt.date(2000, 1, 1)))
    assert pyth.associated_numbers.status is ItemStatus.DEFERRED


def test_interpretation_is_deferred_with_source_references_only() -> None:
    facts = calculate_numerology(NumerologyRequest(date_of_birth=dt.date(2000, 1, 3)))
    assert facts.interpretation.status is ItemStatus.DEFERRED
    assert [r.locator for r in facts.interpretation.references][0].startswith("Ch. V")
    dumped = facts.model_dump_json()
    for word in ("lucky number is", "personality", "you will"):
        assert word not in dumped


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------


def test_deterministic_and_round_trips() -> None:
    request = NumerologyRequest(
        date_of_birth=dt.date(1995, 8, 23), name=NameInput(latin_spelling="Meera Nair")
    )
    first, second = calculate_numerology(request), calculate_numerology(request)
    assert first == second
    assert NumerologyFacts.model_validate_json(first.model_dump_json()) == first
