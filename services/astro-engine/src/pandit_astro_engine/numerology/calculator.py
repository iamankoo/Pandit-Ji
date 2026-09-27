"""Pure numerology calculator (Phase 11; `docs/ASTROLOGY_STANDARDS.md` v1.25.0,
NU-01 to NU-16). No clock, network, file or ephemeris access: the result
depends only on the request."""

from __future__ import annotations

import unicodedata

from pandit_astro_engine._version import __version__
from pandit_astro_engine.numerology.constants import (
    CHEIRO_BIRTH_NUMBER_CHAPTER,
    CHEIRO_COMPOUND_CHAPTER,
    CHEIRO_INTERCHANGEABLE,
    IGNORED_PUNCTUATION,
    LETTER_VALUES,
    METHODOLOGY_VERSION,
    NUMEROLOGY_STANDARDS_VERSION,
    PROFILE_SYSTEM,
    RETAINED,
    ItemReason,
    ItemStatus,
    NumerologyProfileId,
)
from pandit_astro_engine.numerology.models import (
    AssociatedNumbers,
    InterpretationReference,
    NameInput,
    NameNumber,
    NameWord,
    NumberItem,
    NumerologyFacts,
    NumerologyRequest,
    ProvenanceEntry,
    Reduction,
)
from pandit_astro_engine.numerology.profiles import (
    CHEIRO,
    PROVENANCE,
    EvidenceLabel,
    SourceReference,
)

_CHALDEAN = NumerologyProfileId.CHALDEAN_CHEIRO_1926


def digit_sum(value: int) -> int:
    return sum(int(digit) for digit in str(value))


def reduce_number(total: int, retained: frozenset[int] = frozenset()) -> Reduction:
    """Repeated digit sums ("natural addition") until one digit remains or a
    retained master number is reached (NU-05, NU-06)."""
    if total < 1:
        raise ValueError("numerology totals are positive integers")
    chain = [total]
    while chain[-1] > 9 and chain[-1] not in retained:
        chain.append(digit_sum(chain[-1]))
    value = chain[-1]
    return Reduction(
        chain=tuple(chain),
        value=value,
        compound=total if total > 9 else None,
        master_retained=value > 9,
    )


def normalize_latin_name(
    spelling: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], ItemReason | None]:
    """Upper-case A-Z words, notes on changes, offending characters and a
    failure reason (NU-09). No transliteration: a letter outside the Latin
    alphabet makes the name not evaluable."""
    words: list[str] = []
    notes: list[str] = []
    offending: list[str] = []
    non_latin = False
    current: list[str] = []
    for char in spelling:
        if char.isspace():
            if current:
                words.append("".join(current))
                current = []
            continue
        if char in IGNORED_PUNCTUATION:
            notes.append(f"ignored punctuation {char!r}")
            continue
        base = [c for c in unicodedata.normalize("NFKD", char) if not unicodedata.combining(c)]
        if len(base) == 1 and "A" <= base[0].upper() <= "Z" and base[0].isascii():
            letter = base[0].upper()
            if char.upper() != letter:
                notes.append(f"{char!r} read as {letter!r} (diacritic removed)")
            current.append(letter)
            continue
        offending.append(char)
        if unicodedata.category(char).startswith("L") and "LATIN" not in unicodedata.name(char, ""):
            non_latin = True
    if current:
        words.append("".join(current))
    if offending:
        reason = ItemReason.NON_LATIN_SCRIPT if non_latin else ItemReason.UNSUPPORTED_CHARACTER
        return (), tuple(notes), tuple(offending), reason
    if not words:
        return (), tuple(notes), (), ItemReason.NAME_EMPTY
    return tuple(words), tuple(notes), (), None


def name_number(
    name: NameInput | None, profile: NumerologyProfileId, retained: frozenset[int]
) -> NameNumber:
    if name is None:
        return NameNumber(status=ItemStatus.NOT_EVALUABLE, reason=ItemReason.NAME_NOT_SUPPLIED)
    words, notes, offending, reason = normalize_latin_name(name.latin_spelling)
    if reason is not None:
        return NameNumber(
            status=ItemStatus.NOT_EVALUABLE,
            reason=reason,
            input_spelling=name.latin_spelling,
            normalization_notes=notes,
            offending_characters=offending,
        )
    table = LETTER_VALUES[profile]
    word_records = []
    for word in words:
        values = tuple(table[letter] for letter in word)
        word_records.append(
            NameWord(
                word=word,
                letter_values=values,
                total=sum(values),
                reduction=reduce_number(sum(values), retained),
            )
        )
    if len(word_records) == 1:
        total = word_records[0].total
    else:
        total = sum(record.reduction.value for record in word_records)
    return NameNumber(
        status=ItemStatus.EVALUATED,
        input_spelling=name.latin_spelling,
        normalized_words=words,
        normalization_notes=notes,
        words=tuple(word_records),
        reduction=reduce_number(total, retained),
    )


def _evaluated(
    item_id: str, label: EvidenceLabel, inputs: dict[str, int | str], reduction: Reduction
) -> NumberItem:
    return NumberItem(
        item_id=item_id,
        status=ItemStatus.EVALUATED,
        label=label,
        inputs=inputs,
        reduction=reduction,
    )


def _missing_date(item_id: str) -> NumberItem:
    return NumberItem(
        item_id=item_id,
        status=ItemStatus.NOT_EVALUABLE,
        reason=ItemReason.DATE_OF_BIRTH_NOT_SUPPLIED,
        label=EvidenceLabel.PHASE1_LOCKED_STANDARD,
    )


def _associated(birth_number: int | None, profile: NumerologyProfileId) -> AssociatedNumbers:
    if profile is not _CHALDEAN:
        return AssociatedNumbers(
            status=ItemStatus.DEFERRED,
            reason=ItemReason.NO_SOURCE_RULE_READ,
            statement="No rule for associated ('lucky') numbers was read in Balliett (1908).",
        )
    if birth_number is None:
        return AssociatedNumbers(
            status=ItemStatus.NOT_EVALUABLE,
            reason=ItemReason.DATE_OF_BIRTH_NOT_SUPPLIED,
            statement="Cheiro derives these from the Birth number, which needs a date of birth.",
        )
    interchangeable = CHEIRO_INTERCHANGEABLE[birth_number]
    return AssociatedNumbers(
        status=ItemStatus.EVALUATED,
        birth_number=birth_number,
        own_series_dates=tuple(d for d in range(1, 32) if reduce_number(d).value == birth_number),
        interchangeable_numbers=interchangeable,
        interchangeable_dates=tuple(
            d for d in range(1, 32) if reduce_number(d).value in interchangeable
        ),
        statement=(
            "Cheiro's own-series dates and 'interchangeable' numbers for this Birth number, "
            "which he calls favourable; reported as the source's associations, with no claim "
            "of effect."
        ),
    )


def calculate_numerology(request: NumerologyRequest) -> NumerologyFacts:
    profile = request.profile
    policy = request.effective_policy
    retained = RETAINED[policy]
    dob = request.date_of_birth

    moolank = _missing_date("moolank")
    bhagyank = _missing_date("bhagyank")
    date_numbers: list[NumberItem] = []
    if dob is not None:
        moolank = _evaluated(
            "moolank",
            EvidenceLabel.SOURCE_SUPPORTED
            if profile is _CHALDEAN
            else EvidenceLabel.PHASE1_LOCKED_STANDARD,
            {"day": dob.day},
            reduce_number(dob.day, retained),
        )
        digits = f"{dob.day:02d}{dob.month:02d}{dob.year:04d}"
        bhagyank = _evaluated(
            "bhagyank",
            EvidenceLabel.PHASE1_LOCKED_STANDARD,
            {"digits": digits},
            reduce_number(sum(int(d) for d in digits), retained),
        )
        if profile is _CHALDEAN:
            date_numbers.append(
                _evaluated(
                    "cheiro_day_number",
                    EvidenceLabel.SOURCE_SUPPORTED,
                    {"day": dob.day},
                    reduce_number(dob.day),
                )
            )
            date_numbers.append(
                NumberItem(
                    item_id="cheiro_month_number",
                    status=ItemStatus.NOT_EVALUABLE,
                    reason=ItemReason.CHEIRO_MONTH_NUMBER_BASIS_UNCLEAR,
                    label=EvidenceLabel.UNRESOLVED_CONFLICT,
                    inputs={"month": dob.month},
                    note="Cheiro's example gives 'June = 5', not the calendar month number.",
                )
            )
            date_numbers.append(
                _evaluated(
                    "cheiro_year_number",
                    EvidenceLabel.SOURCE_SUPPORTED,
                    {"year": dob.year},
                    reduce_number(digit_sum(dob.year)),
                )
            )
        else:
            month = reduce_number(dob.month, retained)
            day = reduce_number(dob.day, retained)
            year = reduce_number(digit_sum(dob.year), retained)
            date_numbers.append(
                _evaluated(
                    "balliett_birth_number",
                    EvidenceLabel.SOURCE_SUPPORTED,
                    {
                        "month_digit": month.value,
                        "day_digit": day.value,
                        "year_digit": year.value,
                    },
                    reduce_number(month.value + day.value + year.value, retained),
                )
            )

    interpretation = InterpretationReference(
        references=(
            (
                SourceReference(
                    source_id=CHEIRO,
                    locator=CHEIRO_BIRTH_NUMBER_CHAPTER[moolank.reduction.value],
                    verification_level="OCR-ORIGINAL-ENGLISH",
                    note="Birth number chapter.",
                ),
            )
            if profile is _CHALDEAN and moolank.reduction is not None
            else ()
        )
        + (
            (
                SourceReference(
                    source_id=CHEIRO,
                    locator=CHEIRO_COMPOUND_CHAPTER,
                    verification_level="OCR-ORIGINAL-ENGLISH",
                    note="Compound-number descriptions.",
                ),
            )
            if profile is _CHALDEAN
            else ()
        )
    )

    birth_number = None if moolank.reduction is None else moolank.reduction.value
    return NumerologyFacts(
        system=PROFILE_SYSTEM[profile],
        profile_id=profile,
        methodology_version=METHODOLOGY_VERSION[profile],
        standards_version=NUMEROLOGY_STANDARDS_VERSION,
        engine_version=__version__,
        master_number_policy=policy,
        date_of_birth=dob,
        moolank=moolank,
        bhagyank=bhagyank,
        date_numbers=tuple(date_numbers),
        name_number=name_number(request.name, profile, retained),
        associated_numbers=_associated(birth_number, profile),
        interpretation=interpretation,
        assumptions=(
            "The date of birth is the civil calendar date at the birth place, as entered.",
            "The name is the spelling in use, supplied by the caller in Latin letters.",
        ),
        confidence=(
            "HIGH for the letter table (page image and worked examples); "
            "MEDIUM for the other rules (OCR text)"
            if profile is _CHALDEAN
            else "MEDIUM (OCR text; the worked example is reproduced)"
        ),
        provenance=tuple(
            ProvenanceEntry(
                entry_id=d.entry_id,
                item=d.item,
                evidence_label=d.label,
                statement=d.statement,
                references=d.references,
            )
            for d in PROVENANCE[profile]
        ),
    )
