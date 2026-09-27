"""Numerology constants (Phase 11; `docs/ASTROLOGY_STANDARDS.md` v1.25.0,
NU-01 to NU-16; sources in `research/ASTROLOGY_SOURCES.md` Group 24).

Two separate profiles, never mixed: the Chaldean table of Cheiro's *Book of
Numbers* (1926; the default, owner decision) and the Pythagorean table of
L. Dow Balliett's *The Philosophy of Numbers* (1908). Both are modern
numerology traditions, not established facts.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Final

NUMEROLOGY_STANDARDS_VERSION: Final = "1.25.0"


class NumerologySystem(str, Enum):
    CHALDEAN = "chaldean"
    PYTHAGOREAN = "pythagorean"


class NumerologyProfileId(str, Enum):
    CHALDEAN_CHEIRO_1926 = "NUMEROLOGY_CHALDEAN_CHEIRO_1926_V1"
    PYTHAGOREAN_BALLIETT_1908 = "NUMEROLOGY_PYTHAGOREAN_BALLIETT_1908_V1"


#: Owner decision (Phase 11): Chaldean is the default system.
DEFAULT_PROFILE: Final = NumerologyProfileId.CHALDEAN_CHEIRO_1926

PROFILE_SYSTEM: Final = MappingProxyType(
    {
        NumerologyProfileId.CHALDEAN_CHEIRO_1926: NumerologySystem.CHALDEAN,
        NumerologyProfileId.PYTHAGOREAN_BALLIETT_1908: NumerologySystem.PYTHAGOREAN,
    }
)

#: Every profile's methodology version (NU-15).
METHODOLOGY_VERSION: Final = MappingProxyType(
    {
        NumerologyProfileId.CHALDEAN_CHEIRO_1926: "1.0.0",
        NumerologyProfileId.PYTHAGOREAN_BALLIETT_1908: "1.0.0",
    }
)


class MasterNumberPolicy(str, Enum):
    """Whether 11 and 22 stop a reduction (NU-06). Cheiro reduces every
    number to one digit, so the Chaldean profile allows only `none`;
    Balliett keeps 11 and 22, but the Pythagorean profile still takes the
    policy as an explicit request field with no default."""

    NONE = "none"
    RETAIN_11_22 = "retain_11_22"


RETAINED: Final = MappingProxyType(
    {
        MasterNumberPolicy.NONE: frozenset[int](),
        MasterNumberPolicy.RETAIN_11_22: frozenset({11, 22}),
    }
)


class ItemStatus(str, Enum):
    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"
    DEFERRED = "deferred"


class ItemReason(str, Enum):
    NAME_NOT_SUPPLIED = "name_not_supplied"
    DATE_OF_BIRTH_NOT_SUPPLIED = "date_of_birth_not_supplied"
    NAME_EMPTY = "name_empty"
    NON_LATIN_SCRIPT = "non_latin_script_requires_explicit_latin_spelling"
    UNSUPPORTED_CHARACTER = "unsupported_character"
    CHEIRO_MONTH_NUMBER_BASIS_UNCLEAR = "cheiro_month_number_basis_unclear"
    NO_SOURCE_RULE_READ = "no_source_rule_read"
    INTERPRETATION_DEFERRED_TO_KNOWLEDGE_PHASE = "interpretation_deferred_to_knowledge_phase"


#: Cheiro, *Book of Numbers*, Ch. XII, printed p. 70 (page image): the
#: "ancient Chaldean and Hebrew alphabet". No letter has the value 9.
CHEIRO_LETTER_VALUES: Final = MappingProxyType(
    {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 8,
        "G": 3,
        "H": 5,
        "I": 1,
        "J": 1,
        "K": 2,
        "L": 3,
        "M": 4,
        "N": 5,
        "O": 7,
        "P": 8,
        "Q": 1,
        "R": 2,
        "S": 3,
        "T": 4,
        "U": 6,
        "V": 6,
        "W": 6,
        "X": 5,
        "Y": 1,
        "Z": 7,
    }
)

#: Balliett, *The Philosophy of Numbers* (1908), p. 18: the alphabet divided
#: into nine parts (a-i = 1-9, j-r = 1-9, s-z = 1-8); reproduced by her
#: worked example on pp. 19-20 (Henry = 34, Elder = 26).
BALLIETT_LETTER_VALUES: Final = MappingProxyType(
    {letter: (index % 9) + 1 for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
)

LETTER_VALUES: Final = MappingProxyType(
    {
        NumerologyProfileId.CHALDEAN_CHEIRO_1926: CHEIRO_LETTER_VALUES,
        NumerologyProfileId.PYTHAGOREAN_BALLIETT_1908: BALLIETT_LETTER_VALUES,
    }
)

#: Cheiro's "interchangeable" numbers for each Birth number (Ch. III-XI).
#: Number 5: only its own series is named ("their best friends are those who
#: are born under their own number"). Number 6: the 3, 6, 9 series.
CHEIRO_INTERCHANGEABLE: Final = MappingProxyType(
    {
        1: (2, 4, 7),
        2: (1, 4, 7),
        3: (6, 9),
        4: (1, 2, 7),
        5: (),
        6: (3, 9),
        7: (1, 2, 4),
        8: (4,),
        9: (3, 6),
    }
)

#: Where Cheiro describes each Birth number (chapter, printed page).
CHEIRO_BIRTH_NUMBER_CHAPTER: Final = MappingProxyType(
    {
        1: "Ch. III, pp. 37-39",
        2: "Ch. IV, pp. 40-42",
        3: "Ch. V, pp. 43-45",
        4: "Ch. VI, pp. 46-48",
        5: "Ch. VII, pp. 49-51",
        6: "Ch. VIII, pp. 52-54",
        7: "Ch. IX, pp. 55-57",
        8: "Ch. X, pp. 58-63",
        9: "Ch. XI, pp. 64-68",
    }
)

CHEIRO_COMPOUND_CHAPTER: Final = "Ch. XIII, pp. 78-86 (compound numbers 10-52)"

#: Characters that are dropped without comment inside a Latin name (NU-09):
#: they are punctuation, not letters, in both tables.
IGNORED_PUNCTUATION: Final = frozenset({"-", "'", "’", ".", "‐", "‑"})
