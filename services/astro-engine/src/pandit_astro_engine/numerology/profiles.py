"""Numerology profiles and provenance (Phase 11; `docs/ASTROLOGY_STANDARDS.md`
v1.25.0, NU-01 to NU-16; `research/ASTROLOGY_SOURCES.md` Group 24).

Every statement says what the source supports and what is a Pandit Ji
convention. Numerology is recorded as a modern tradition: nothing here
claims that a number has an effect.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.numerology.constants import NumerologyProfileId


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Same vocabulary as the other phase modules' own copies, plus
    `phase1_locked_standard` for the owner-locked Phase 1 arithmetic that no
    Phase 11 source states."""

    SOURCE_SUPPORTED = "source_supported"
    TRANSLATOR_NOTE = "translator_note"
    INFERENCE = "inference"
    ENGINEERING_CONVENTION = "engineering_convention"
    DERIVED_CALCULATION = "derived_calculation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    MODERN_TRADITION = "modern_tradition"
    ENGINEERING_EVIDENCE = "engineering_evidence"
    PHASE1_LOCKED_STANDARD = "phase1_locked_standard"


class SourceReference(_Model):
    source_id: str
    locator: str
    verification_level: str
    note: str = ""


class ProvenanceDef(_Model):
    entry_id: str
    item: str
    label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...]


CHEIRO = "SRC-CHEIRO-BOOK-OF-NUMBERS-1926"
BALLIETT = "SRC-BALLIETT-PHILOSOPHY-OF-NUMBERS-1908"
STANDARDS = "PANDIT-JI-ASTROLOGY-STANDARDS"

_CHEIRO_TABLE = SourceReference(
    source_id=CHEIRO,
    locator="Ch. XII, printed p. 70 (alphabet table)",
    verification_level="IMAGE-ORIGINAL-ENGLISH",
    note=(
        "Reproduces Cheiro's own examples: Baldwin 22, Lloyd 18, George 25, David 16, "
        "John 18, Smith 17."
    ),
)
_BALLIETT_TABLE = SourceReference(
    source_id=BALLIETT,
    locator="Ch. II, printed pp. 18-20 (alphabet in nine parts; Henry Elder example)",
    verification_level="OCR-ORIGINAL-ENGLISH",
    note="Reproduces the worked example: Henry 34 = 7, Elder 26 = 8, name 15 = 6.",
)
_PHASE1 = SourceReference(
    source_id=STANDARDS,
    locator="docs/ASTROLOGY_STANDARDS.md, 'Numerology standards' (Phase 1)",
    verification_level="OWNER-LOCKED",
    note="Owner-locked Phase 1 arithmetic; no Phase 11 source states it.",
)

_COMMON: tuple[ProvenanceDef, ...] = (
    ProvenanceDef(
        entry_id="prov.numerology.tradition",
        item="Status of numerology",
        label=EvidenceLabel.MODERN_TRADITION,
        statement=(
            "Numerology is a modern tradition. Pandit Ji reports the numbers each profile's "
            "source defines; it makes no claim that a number has an effect."
        ),
        references=(),
    ),
    ProvenanceDef(
        entry_id="prov.numerology.bhagyank",
        item="Bhagyank",
        label=EvidenceLabel.PHASE1_LOCKED_STANDARD,
        statement=(
            "Bhagyank sums every digit of the day, month and year and reduces the total "
            "(Phase 1 standard). The single digit equals the reduction of any other grouping "
            "of the same digits (all are congruent modulo 9); only the intermediate compound "
            "number and master-number retention can differ between groupings."
        ),
        references=(_PHASE1,),
    ),
    ProvenanceDef(
        entry_id="prov.numerology.name_input",
        item="Name input",
        label=EvidenceLabel.ENGINEERING_CONVENTION,
        statement=(
            "The name is the Latin spelling the caller supplies, recorded exactly. Letters with "
            "diacritics are reduced to their base letter; hyphens, apostrophes and full stops "
            "are ignored; words are separated by white space. Devanagari or any other script is "
            "not transliterated: it is not evaluable until a Latin spelling is supplied."
        ),
        references=(),
    ),
)

PROVENANCE: dict[NumerologyProfileId, tuple[ProvenanceDef, ...]] = {
    NumerologyProfileId.CHALDEAN_CHEIRO_1926: _COMMON
    + (
        ProvenanceDef(
            entry_id="prov.cheiro.letters",
            item="Letter values",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement="Cheiro's Chaldean table; no letter is valued 9.",
            references=(_CHEIRO_TABLE,),
        ),
        ProvenanceDef(
            entry_id="prov.cheiro.birth_number",
            item="Moolank (Cheiro's Birth number)",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "The day of the month reduced by 'natural addition' to one digit (the 1st, "
                "10th, 19th and 28th are all 1)."
            ),
            references=(
                SourceReference(
                    source_id=CHEIRO,
                    locator="Ch. II, p. 35; Ch. III, p. 37",
                    verification_level="OCR-ORIGINAL-ENGLISH",
                ),
            ),
        ),
        ProvenanceDef(
            entry_id="prov.cheiro.reduction",
            item="Reduction and master numbers",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "Every number reduces to one digit; 11 and 22 are compound numbers with their "
                "own meanings (Ch. XIII), not retained master numbers. The Chaldean profile "
                "therefore allows only the master-number policy 'none'."
            ),
            references=(
                SourceReference(
                    source_id=CHEIRO,
                    locator="Ch. II, p. 35; Ch. XII, p. 72 (Baldwin: 22 = 4)",
                    verification_level="OCR-ORIGINAL-ENGLISH",
                ),
            ),
        ),
        ProvenanceDef(
            entry_id="prov.cheiro.name",
            item="Name number",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "Each name word's letters are added; for one word the compound is that total "
                "(Baldwin 22); for several words each word is reduced to a digit and the digits "
                "are added (Lloyd George 9 + 7 = 16; David Lloyd George 23; John Smith 17). The "
                "name used is the one most in use, which only the caller can supply."
            ),
            references=(
                SourceReference(
                    source_id=CHEIRO,
                    locator="Ch. XII, pp. 71-73; Ch. XIII, p. 86 (John Smith)",
                    verification_level="OCR-ORIGINAL-ENGLISH",
                ),
            ),
        ),
        ProvenanceDef(
            entry_id="prov.cheiro.date_numbers",
            item="Cheiro's separate date numbers",
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            statement=(
                "Cheiro treats the day, month and year numbers as 'separate and distinct and not "
                "added together', which differs from the Phase 1 Bhagyank. Both are reported. "
                "His month number is not the calendar month (6 June is 'June = 5'); its basis "
                "is not stated, so it is not evaluable."
            ),
            references=(
                SourceReference(
                    source_id=CHEIRO,
                    locator="Ch. XV, p. 93 (6 June 1866 example)",
                    verification_level="OCR-ORIGINAL-ENGLISH",
                ),
                _PHASE1,
            ),
        ),
        ProvenanceDef(
            entry_id="prov.cheiro.associated",
            item="Associated ('lucky') numbers",
            label=EvidenceLabel.MODERN_TRADITION,
            statement=(
                "Cheiro names, for each Birth number, the dates of its own series and its "
                "'interchangeable' numbers, and calls them favourable. Pandit Ji reports these "
                "associations as the source's statements, with no claim of effect."
            ),
            references=(
                SourceReference(
                    source_id=CHEIRO,
                    locator="Ch. III-XI (each number's chapter); Ch. XV, p. 91",
                    verification_level="OCR-ORIGINAL-ENGLISH",
                ),
            ),
        ),
    ),
    NumerologyProfileId.PYTHAGOREAN_BALLIETT_1908: _COMMON
    + (
        ProvenanceDef(
            entry_id="prov.balliett.letters",
            item="Letter values",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement="The alphabet divided into nine parts: a-i 1-9, j-r 1-9, s-z 1-8.",
            references=(_BALLIETT_TABLE,),
        ),
        ProvenanceDef(
            entry_id="prov.balliett.birth",
            item="Balliett's birth number",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "The digits of the month, the day and the year are found separately and added "
                "(17 January 1872: 1 + 8 + 9 = 18 = 9). Reported beside the Phase 1 Bhagyank."
            ),
            references=(_BALLIETT_TABLE,),
        ),
        ProvenanceDef(
            entry_id="prov.balliett.master",
            item="Master numbers",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "Balliett keeps 11 and 22 among the 'free numbers' (White: 29 = 11). The policy is "
                "still an explicit request field with no default (Phase 1 standard)."
            ),
            references=(
                SourceReference(
                    source_id=BALLIETT,
                    locator=(
                        "Ch. II, pp. 20-21 (11 and 22 among the free numbers); Ch. III, p. 33 "
                        "(White = 29 = 11, Cream = 22); pp. 44-46 (No. 22, No. 11)"
                    ),
                    verification_level="OCR-ORIGINAL-ENGLISH",
                ),
            ),
        ),
        ProvenanceDef(
            entry_id="prov.balliett.name",
            item="Name number",
            label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "Each name word's digit is found and the digits are added "
                "(Henry 7 + Elder 8 = 15 = 6)."
            ),
            references=(_BALLIETT_TABLE,),
        ),
    ),
}
