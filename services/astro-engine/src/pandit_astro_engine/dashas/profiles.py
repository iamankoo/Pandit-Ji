"""Balance, year-length and sub-period profiles for Vimshottari
(docs/ASTROLOGY_STANDARDS.md v1.5.0 "Vimshottari Dasha").

Every profile is an explicit, identified choice. None of them is presented as
the only valid classical method: the balance-at-birth method is a documented
source conflict (`research/ASTROLOGY_SOURCES.md` section 4), and no verse read
states a year length. A profile that cannot be implemented safely is
registered as INACTIVE with the reason, never approximated.
"""

from __future__ import annotations

from enum import Enum
from fractions import Fraction

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProfileAvailability(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class EvidenceLabel(str, Enum):
    """What kind of statement a provenance entry is. Never merged."""

    SOURCE_SUPPORTED = "source_supported"  # a verse, at the stated verification level
    TRANSLATOR_NOTE = "translator_note"
    INFERENCE = "inference"
    ENGINEERING_CONVENTION = "engineering_convention"  # a Pandit Ji implementation decision
    DERIVED_CALCULATION = "derived_calculation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"


class SourceReference(_Model):
    source_id: str
    locator: str
    verification_level: str
    note: str = ""


# --------------------------------------------------------------------------
# Balance profiles
# --------------------------------------------------------------------------

BALANCE_LONGITUDE_ID = "DASHA_STANDARD_V1_BALANCE_LONGITUDE"
BALANCE_BPHS_TIME_ID = "DASHA_BPHS_KAPOOR_46_16_BALANCE_TIME"
BALANCE_PHALADEEPIKA_ID = "DASHA_PHALADEEPIKA_SASTRI_XIX_3_BALANCE"


class BalanceProfile(_Model):
    profile_id: str
    label: str
    availability: ProfileAvailability
    evidence_label: EvidenceLabel
    is_default: bool
    method: str
    unavailable_reason: str | None = None
    references: tuple[SourceReference, ...] = ()


BALANCE_PROFILES: dict[str, BalanceProfile] = {
    BALANCE_LONGITUDE_ID: BalanceProfile(
        profile_id=BALANCE_LONGITUDE_ID,
        label="Moon longitude fraction (Pandit Ji product default)",
        availability=ProfileAvailability.ACTIVE,
        evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
        is_default=True,
        method=(
            "remaining_fraction = 1 - fraction of the birth Nakshatra's 13 deg 20 min span "
            "already traversed by the Moon's sidereal longitude; balance = remaining_fraction "
            "x the starting lord's full Mahadasha years"
        ),
        references=(
            SourceReference(
                source_id="docs/ASTROLOGY_STANDARDS.md",
                locator="Vimshottari Dasha, Balance of the first Mahadasha (v1.4.0)",
                verification_level="ENGINEERING_STANDARD",
                note="The locked Pandit Ji standard states the longitude-fraction rule.",
            ),
            SourceReference(
                source_id="SRC-BPHS-SANTHANAM-1984",
                locator="Ch. 46 v. 16, translator's note (Kapoor)",
                verification_level="TRANSLATOR_NOTE",
                note="Modern researchers use the Moon's longitude instead of Panchanga time.",
            ),
            SourceReference(
                source_id="SRC-UTTARA-KALAMRITA-SASTRI",
                locator="printed p. 142 worked example",
                verification_level="OCR_TRANSLATION",
                note=(
                    "Translator calls the arc-based balance the correct one; it differs from the "
                    "Panchanga-time balance by seven days in that example."
                ),
            ),
        ),
    ),
    BALANCE_BPHS_TIME_ID: BalanceProfile(
        profile_id=BALANCE_BPHS_TIME_ID,
        label="BPHS Ch. 46 v. 16 Panchanga-time balance (Kapoor translation)",
        availability=ProfileAvailability.INACTIVE,
        evidence_label=EvidenceLabel.SOURCE_SUPPORTED,
        is_default=False,
        method=(
            "expired part = years x the Moon's expired stay in the nakshatra / its total stay, "
            "both measured as Panchanga time (ghatis and palas)"
        ),
        unavailable_reason="requires_moon_nakshatra_entry_and_exit_instants_not_computed",
        references=(
            SourceReference(
                source_id="SRC-BPHS-SANTHANAM-1984",
                locator="Ch. 46 v. 16 (Kapoor, Vol II, printed pp. 505-507)",
                verification_level="IMAGE_CHECKED_TRANSLATION",
                note="Translation level only; no Sanskrit-level verification.",
            ),
        ),
    ),
    BALANCE_PHALADEEPIKA_ID: BalanceProfile(
        profile_id=BALANCE_PHALADEEPIKA_ID,
        label="Phaladeepika XIX sl. 3 balance (Sastri translation)",
        availability=ProfileAvailability.INACTIVE,
        evidence_label=EvidenceLabel.UNRESOLVED_CONFLICT,
        is_default=False,
        method="ghatikas still to be traversed x years / 60, remainder to months and days",
        unavailable_reason="source_unit_time_or_arc_unresolved",
        references=(
            SourceReference(
                source_id="SRC-PHALADEEPIKA-SASTRI",
                locator="Adhyaya XIX sl. 3",
                verification_level="OCR_TRANSLATION",
                note="The translation does not settle whether the divisor 60 is time or arc.",
            ),
        ),
    ),
}

DEFAULT_BALANCE_PROFILE_ID = BALANCE_LONGITUDE_ID


# --------------------------------------------------------------------------
# Year-length profiles (fixed-duration years; no calendar-year arithmetic)
# --------------------------------------------------------------------------

YEAR_365_2425_ID = "YEAR_365_2425_FIXED_DAY"
YEAR_365_25_ID = "YEAR_365_25_FIXED_DAY"
YEAR_360_ID = "YEAR_360_FIXED_DAY"
YEAR_SIDEREAL_ID = "YEAR_SIDEREAL_365_256363_FIXED_DAY"
YEAR_SUN_RETURN_ID = "YEAR_SUN_RETURN_PHALADEEPIKA_XIX_4"


class YearLengthProfile(_Model):
    profile_id: str
    label: str
    availability: ProfileAvailability
    evidence_label: EvidenceLabel
    is_default: bool
    #: Exact length of one year in days, as a fraction (None when not a fixed length).
    days_numerator: int | None = None
    days_denominator: int | None = None
    unavailable_reason: str | None = None
    references: tuple[SourceReference, ...] = ()

    def days(self) -> Fraction:
        if self.days_numerator is None or self.days_denominator is None:
            raise ValueError(f"{self.profile_id} has no fixed year length")
        return Fraction(self.days_numerator, self.days_denominator)


_NO_VERSE = SourceReference(
    source_id="SRC-BPHS-SANTHANAM-1984",
    locator="Ch. 46, Ch. 51, Ch. 61 (Kapoor, Vol II)",
    verification_level="TRANSLATION_LEVEL",
    note="No verse read states the year length used for Vimshottari.",
)

YEAR_LENGTH_PROFILES: dict[str, YearLengthProfile] = {
    YEAR_365_2425_ID: YearLengthProfile(
        profile_id=YEAR_365_2425_ID,
        label="365.2425 mean solar days (Pandit Ji product default)",
        availability=ProfileAvailability.ACTIVE,
        evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
        is_default=True,
        days_numerator=3652425,
        days_denominator=10000,
        references=(_NO_VERSE,),
    ),
    YEAR_365_25_ID: YearLengthProfile(
        profile_id=YEAR_365_25_ID,
        label="365.25 days (Julian year; explicit non-default choice)",
        availability=ProfileAvailability.ACTIVE,
        evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
        is_default=False,
        days_numerator=1461,
        days_denominator=4,
        references=(_NO_VERSE,),
    ),
    YEAR_360_ID: YearLengthProfile(
        profile_id=YEAR_360_ID,
        label="360-day year (translator worked-example convention; explicit non-default choice)",
        availability=ProfileAvailability.ACTIVE,
        evidence_label=EvidenceLabel.TRANSLATOR_NOTE,
        is_default=False,
        days_numerator=360,
        days_denominator=1,
        references=(
            SourceReference(
                source_id="SRC-BPHS-SANTHANAM-1984",
                locator="Ch. 46, 51, 61 worked examples (Kapoor): months counted as 30 days",
                verification_level="TRANSLATOR_NOTE",
                note="Implied by the translator's examples; not a verse statement.",
            ),
        ),
    ),
    YEAR_SIDEREAL_ID: YearLengthProfile(
        profile_id=YEAR_SIDEREAL_ID,
        label="Mean sidereal year 365.256363 days (translator note; documented, inactive)",
        availability=ProfileAvailability.INACTIVE,
        evidence_label=EvidenceLabel.TRANSLATOR_NOTE,
        is_default=False,
        days_numerator=365256363,
        days_denominator=1000000,
        unavailable_reason="documented_alternative_not_activated",
        references=(
            SourceReference(
                source_id="SRC-UTTARA-KALAMRITA-SASTRI",
                locator="translator's note (recorded in SUMMARY.md section 21)",
                verification_level="RESEARCH_RECORD_NOT_REVERIFIED",
                note="Value taken from the project research record; not re-verified here.",
            ),
        ),
    ),
    YEAR_SUN_RETURN_ID: YearLengthProfile(
        profile_id=YEAR_SUN_RETURN_ID,
        label="Sun's return to its birth position (Phaladeepika XIX sl. 4; documented, inactive)",
        availability=ProfileAvailability.INACTIVE,
        evidence_label=EvidenceLabel.INFERENCE,
        is_default=False,
        unavailable_reason="variable_length_per_birth_and_application_to_vimshottari_is_inference",
        references=(
            SourceReference(
                source_id="SRC-PHALADEEPIKA-SASTRI",
                locator="Adhyaya XIX sl. 4",
                verification_level="OCR_TRANSLATION",
                note=(
                    "The verse calls the Sun's return one solar year, also the Ududasa year; "
                    "applying it to Vimshottari is an inference."
                ),
            ),
        ),
    ),
}

DEFAULT_YEAR_LENGTH_PROFILE_ID = YEAR_365_2425_ID


# --------------------------------------------------------------------------
# Sub-period profile
# --------------------------------------------------------------------------

SUBPERIOD_PROFILE_ID = "DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1"

SUBPERIOD_PROFILE_DESCRIPTION = (
    "child duration = full nominal parent duration x child lord years / 120, children in the "
    "canonical sequence starting from the parent lord. For the birth-balance Mahadasha the "
    "sub-periods are those of the full, untruncated Mahadasha; sub-periods that ended before "
    "birth are omitted and the one containing birth starts at birth (truncated_at_birth)."
)

SUBPERIOD_REFERENCES: tuple[SourceReference, ...] = (
    SourceReference(
        source_id="SRC-BPHS-SANTHANAM-1984",
        locator="Ch. 51 v. 1-2 and Ch. 61 v. 1 (Kapoor)",
        verification_level="OCR_TRANSLATION_IN_REGISTRY",
        note=(
            "The proportional formula is source-supported at translation level. How the "
            "birth-balance Mahadasha is subdivided is not stated in the sources read; the "
            "full-parent treatment is a Pandit Ji engineering convention."
        ),
    ),
)


def get_balance_profile(profile_id: str) -> BalanceProfile | None:
    return BALANCE_PROFILES.get(profile_id)


def get_year_length_profile(profile_id: str) -> YearLengthProfile | None:
    return YEAR_LENGTH_PROFILES.get(profile_id)
