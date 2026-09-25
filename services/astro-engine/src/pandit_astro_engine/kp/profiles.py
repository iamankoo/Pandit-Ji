"""KP methodology profiles (Phase 9 WP-E; `docs/ASTROLOGY_STANDARDS.md`
v1.15.0, KP-01 to KP-16; sources in `research/ASTROLOGY_SOURCES.md` Group 16).

Every choice that is not fixed by a source is a named profile with an
evidence label. Unknown profile IDs are rejected at request validation;
nothing falls back to a different profile, and no KP profile ever uses the
Vedic default's Lahiri ayanamsa.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Same vocabulary as the other phase modules' own copies
    (`western.profiles`, `transits.profiles`) -- deliberately not a shared
    cross-phase import."""

    SOURCE_SUPPORTED = "source_supported"
    TRANSLATOR_NOTE = "translator_note"
    INFERENCE = "inference"
    ENGINEERING_CONVENTION = "engineering_convention"
    DERIVED_CALCULATION = "derived_calculation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    MODERN_TRADITION = "modern_tradition"
    ENGINEERING_EVIDENCE = "engineering_evidence"


class SourceReference(_Model):
    source_id: str
    locator: str
    verification_level: str
    note: str = ""


class ProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    references: tuple[SourceReference, ...] = ()


KP_READER_I = "SRC-KP-READER-I-KRISHNAMURTI"
KP_READER_III = "SRC-KP-READER-III-KRISHNAMURTI"
KP_READER_VI = "SRC-KP-READER-VI-KRISHNAMURTI"
SWISSEPH_DOC = "SRC-SWISSEPH-DOC"
_OCR = "OCR-ORIGINAL-ENGLISH"

# --------------------------------------------------------------------------
# Ayanamsa (KP-02, KP-03)
# --------------------------------------------------------------------------

AYANAMSA_KRISHNAMURTI_ID = "KP_AYANAMSA_KRISHNAMURTI_SWISSEPH"
AYANAMSA_KRISHNAMURTI_VP291_ID = "KP_AYANAMSA_KRISHNAMURTI_VP291_SWISSEPH"


class AyanamsaProfileDef(ProfileDef):
    swe_variant: str


_READER_I_AYANAMSA = SourceReference(
    source_id=KP_READER_I,
    locator="'Ayanamsa' section and the yearly Ayanamsa table (printed pp. 56-59)",
    verification_level=_OCR,
    note=(
        "Krishnamurti places the coincidence of the zodiacs in 291 CE and follows Newcomb's "
        "precession of 50.2388475 arcseconds a year; the printed table gives the value per "
        "year to the arcminute."
    ),
)

AYANAMSA_KRISHNAMURTI = AyanamsaProfileDef(
    profile_id=AYANAMSA_KRISHNAMURTI_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "Krishnamurti ayanamsa as implemented by Swiss Ephemeris (SE_SIDM_KRISHNAMURTI); "
        "the default KP ayanamsa"
    ),
    swe_variant="krishnamurti",
    references=(
        _READER_I_AYANAMSA,
        SourceReference(
            source_id=KP_READER_I,
            locator="Yearly Ayanamsa table, 1880-2001, compared on 1 January and 1 July",
            verification_level="ENGINEERING-EVIDENCE",
            note=(
                "Swiss Ephemeris agrees with the printed table within 0.9 arcminutes over "
                "1880-2001 (the table is rounded to whole arcminutes); the default was chosen "
                "because it agrees more closely than the VP291 variant (up to 2.1 arcminutes)."
            ),
        ),
        SourceReference(
            source_id=SWISSEPH_DOC,
            locator="Section 2.8.6 'Krishnamurti ayanamshas', mode 5",
            verification_level="DOCUMENTATION-DIRECT",
            note=(
                "Mode 5 was fitted to Krishnamurti's yearly table (t0 1 January 1900, "
                "22.363889 degrees); the documentation notes that the table repeats values in "
                "1918-1921, which no steady precession can produce."
            ),
        ),
    ),
)

AYANAMSA_KRISHNAMURTI_VP291 = AyanamsaProfileDef(
    profile_id=AYANAMSA_KRISHNAMURTI_VP291_ID,
    label=EvidenceLabel.ENGINEERING_CONVENTION,
    title=(
        "Swiss Ephemeris Krishnamurti/Senthilathiban variant (SE_SIDM_KRISHNAMURTI_VP291): "
        "zero ayanamsa at the March equinox of 291 CE; selectable, never a default"
    ),
    swe_variant="krishnamurti_vp291",
    references=(
        SourceReference(
            source_id=SWISSEPH_DOC,
            locator="Section 2.8.6 'Krishnamurti ayanamshas', mode 45",
            verification_level="DOCUMENTATION-DIRECT",
            note=(
                "D. Senthilathiban's reading of the Reader's zero year 291 as the equinox date; "
                "about 1 arcminute higher than Krishnamurti's own table."
            ),
        ),
    ),
)

AYANAMSA_PROFILES: dict[str, AyanamsaProfileDef] = {
    p.profile_id: p for p in (AYANAMSA_KRISHNAMURTI, AYANAMSA_KRISHNAMURTI_VP291)
}
DEFAULT_AYANAMSA_PROFILE_ID = AYANAMSA_KRISHNAMURTI_ID

# --------------------------------------------------------------------------
# Houses (KP-04)
# --------------------------------------------------------------------------

HOUSES_PLACIDUS_SIDEREAL_ID = "KP_HOUSES_PLACIDUS_SIDEREAL_SWISSEPH"

HOUSES_PLACIDUS_SIDEREAL = ProfileDef(
    profile_id=HOUSES_PLACIDUS_SIDEREAL_ID,
    label=EvidenceLabel.INFERENCE,
    title=(
        "Placidus cusps computed tropically and reduced by the KP ayanamsa; a house runs "
        "from its cusp to the next cusp and is ruled by the lord of the cusp's sign"
    ),
    references=(
        SourceReference(
            source_id=KP_READER_I,
            locator="Methods of house division and 'Table of Houses'",
            verification_level=_OCR,
            note=(
                "The Reader names Placidus's semi-arc system as the method in common use and "
                "tells the student to use Raphael's Tables of Houses. That Raphael's tables are "
                "Placidian is outside knowledge, not stated in the Reader, hence 'inference'."
            ),
        ),
        SourceReference(
            source_id=KP_READER_III,
            locator="Worked chart: 'A house commences from the cusp of a house and ends with "
            "the succeeding cusp'",
            verification_level=_OCR,
            note="House extent and cusp-sign lordship are stated directly.",
        ),
    ),
)
HOUSE_PROFILES = {HOUSES_PLACIDUS_SIDEREAL.profile_id: HOUSES_PLACIDUS_SIDEREAL}

# --------------------------------------------------------------------------
# Star/sub division (KP-05, KP-06, KP-07)
# --------------------------------------------------------------------------

SUBDIVISION_ID = "KP_SUBLORD_VIMSHOTTARI_PROPORTIONAL"

SUBDIVISION = ProfileDef(
    profile_id=SUBDIVISION_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "Each 13 deg 20 min star divided into nine subs proportional to the Vimshottari years, "
        "first sub to the star lord; 249 sign-star-sub entries. The sub-sub level repeats the "
        "rule inside the sub (derived calculation)."
    ),
    references=(
        SourceReference(
            source_id=KP_READER_III,
            locator="Chapter on the sub (printed pp. 10-13)",
            verification_level=_OCR,
            note=(
                "Sub spans in proportion to the Vimshottari years; order as in the bhuktis; "
                "249 rather than 243 because some subs fall in two signs. Further subdivision "
                "is mentioned only 'for research students'."
            ),
        ),
        SourceReference(
            source_id=KP_READER_III,
            locator="Numbered list of the 249 sign-star-sub divisions",
            verification_level="ENGINEERING-EVIDENCE",
            note=(
                "202 legible OCR rows agree exactly with the derived table "
                "(fixture kp_reader3_sub_table.json)."
            ),
        ),
    ),
)

# --------------------------------------------------------------------------
# Significators (KP-08, KP-09)
# --------------------------------------------------------------------------

SIGNIFICATORS_FOUR_LEVEL_ID = "KP_SIGNIFICATORS_FOUR_LEVEL_READER_VI"

SIGNIFICATORS_FOUR_LEVEL = ProfileDef(
    profile_id=SIGNIFICATORS_FOUR_LEVEL_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "House significators in the Reader's order: (a) planets in the star of an occupant, "
        "(b) occupants, (c) planets in the star of the house lord, (d) the house lord. "
        "Conjunction and aspect significators (e, f) and node agency are not evaluated."
    ),
    references=(
        SourceReference(
            source_id=KP_READER_VI,
            locator="Order of strength of significators, houses 2, 5 and 11 (items a-f)",
            verification_level=_OCR,
        ),
        SourceReference(
            source_id=KP_READER_VI,
            locator="'Tenant is stronger than the owner ... constellation is stronger than "
            "the sign'",
            verification_level=_OCR,
        ),
    ),
)

# --------------------------------------------------------------------------
# Ruling planets (KP-10)
# --------------------------------------------------------------------------

RULING_PLANETS_ID = "KP_RULING_PLANETS_READER_VI"

RULING_PLANETS = ProfileDef(
    profile_id=RULING_PLANETS_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "Ruling planets of a moment: Ascendant star lord and sign lord, Moon star lord and "
        "sign lord, day lord; a node joins when it occupies a sign owned by the Ascendant "
        "sign lord, Moon sign lord or day lord. Members in the star of a retrograde planet "
        "are flagged, not removed."
    ),
    references=(
        SourceReference(
            source_id=KP_READER_VI,
            locator="'Ruling Planets' (printed p. 123)",
            verification_level=_OCR,
            note=(
                "The Reader says members in the star of a retrograde planet 'should be "
                "rejected'; the flag is reported and the caller decides. Mean nodes are always "
                "retrograde, so the flag is not evaluated for a node star lord."
            ),
        ),
    ),
)

# --------------------------------------------------------------------------
# Horary (KP-11)
# --------------------------------------------------------------------------

HORARY_NUMBER_249_ID = "KP_HORARY_NUMBER_249_READER_VI"

HORARY_NUMBER_249 = ProfileDef(
    profile_id=HORARY_NUMBER_249_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "A number 1-249 selects the table entry whose starting degree becomes the Ascendant; "
        "the other cusps are the Placidus cusps for that Ascendant at the latitude of "
        "judgment; planets are for the moment of judgment"
    ),
    references=(
        SourceReference(
            source_id=KP_READER_VI,
            locator="Horary examples for numbers 48 and 74, and the 'table of houses' "
            "instruction ('All places in the same latitude will have the same cusps')",
            verification_level=_OCR,
        ),
        SourceReference(
            source_id=KP_READER_VI,
            locator="Solving the sidereal time for a given Ascendant",
            verification_level=_OCR,
            note=(
                "The Reader reads the cusps from Raphael's printed tables; Pandit Ji solves "
                "the ARMC numerically with the true obliquity of the judgment date instead, "
                "a derived calculation of the same quantity."
            ),
        ),
    ),
)
