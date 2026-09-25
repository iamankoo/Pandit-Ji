"""Panchang, calendar and special-point profiles with provenance (Phase 10;
`docs/ASTROLOGY_STANDARDS.md` v1.23.0, PC-01 to PC-30; sources in
`research/ASTROLOGY_SOURCES.md` Group 23).

Every convention that the sources leave open, or on which they differ, is a
named profile. A result records every profile it used; alternatives that
the sources do not settle are reported side by side, never merged.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Same vocabulary as the other phase modules' own copies."""

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


class ProvenanceDef(_Model):
    entry_id: str
    item: str
    label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...]


PANCHANG_STANDARDS_VERSION = "1.23.0"
PANCHANG_SYSTEM_ID = "panchang_muhurta_calendar"

CRC = "SRC-CALENDAR-REFORM-COMMITTEE-1955"
SEWELL = "SRC-SEWELL-DIKSHIT-INDIAN-CALENDAR-1896"
KALAP = "SRC-KALAPRAKASIKA-IYER-1917"
RAMAN_MUH = "SRC-RAMAN-MUHURTHA-1948"
BPHS = "SRC-BPHS-SANTHANAM-1984"
PHALA = "SRC-PHALADEEPIKA-SASTRI"
UK = "SRC-UTTARA-KALAMRITA-SASTRI"
SWISS = "SRC-SWISSEPH-DOC"

_IMG = "IMAGE-ORIGINAL-ENGLISH"
_OCR = "OCR-ORIGINAL-ENGLISH"
_IMG_T = "IMAGE-TRANSLATION"
_OCR_T = "OCR-TRANSLATION"


def ref(source_id: str, locator: str, level: str, note: str = "") -> SourceReference:
    return SourceReference(
        source_id=source_id, locator=locator, verification_level=level, note=note
    )


# ---------------------------------------------------------------- profiles


class SunriseConvention(str, Enum):
    """PC-03. The Calendar Reform Committee's convention is the default of
    the standard pan-Indian (Drik) configuration; the Phase 4 convention is
    kept as an explicit alternative."""

    CRC_1955_CENTRE_REFRACTION_30 = "crc_1955_centre_refraction_30"
    UPPER_LIMB_STANDARD_REFRACTION = "upper_limb_standard_refraction"


SUNRISE_SWISS_CONVENTION: dict[SunriseConvention, str] = {
    SunriseConvention.CRC_1955_CENTRE_REFRACTION_30: "centre_refraction_30_arcmin",
    SunriseConvention.UPPER_LIMB_STANDARD_REFRACTION: "upper_limb_standard_refraction",
}

#: Moonrise and moonset: upper limb with standard refraction for every
#: configuration (PC-04, engineering convention; no source read defines it).
MOONRISE_SWISS_CONVENTION = "upper_limb_standard_refraction"


class RegionalConvention(str, Enum):
    """PC-02. The only regional configuration implemented: the standard
    pan-Indian Drik-Ganita convention as defined by the Calendar Reform
    Committee (1955). Regional solar calendars (Tamil, Bengali, Malayalam,
    Odia) are not implemented."""

    PAN_INDIAN_DRIK_CRC_1955 = "pan_indian_drik_crc_1955"


class SauraFrame(str, Enum):
    """PC-15. How the Sun's entry into a sign (sankranti) is measured for
    the saura months that name the lunar months. Both are reported."""

    LAHIRI_VARIABLE = "lahiri_variable"
    CRC_FIXED_23_15 = "crc_fixed_23_15"


CRC_FIXED_AYANAMSA_DEGREES = 23.25

PANCHANG_PROFILE_ID = "PANCHANG_DRIK_CRC_1955_V1"
HORA_PROFILE_ID = "HORA_EQUAL_60_MINUTES_FROM_SUNRISE_V1"
DAY_PART_PROFILE_ID = "DAY_EIGHTHS_OF_SUNRISE_TO_SUNSET_V1"
NAKSHATRA_PANCHAKA_PROFILE_ID = "NAKSHATRA_PANCHAKA_RAMAN_1948"
REMAINDER_PANCHAKA_PROFILE_ID = "REMAINDER_PANCHAKA_RAMAN_KALAPRAKASIKA"
BHADRA_PROFILE_ID = "BHADRA_AS_VISHTI_KARANA_RAMAN_1948"
TARA_PROFILE_ID = "TARA_BALA_NINE_FROM_JANMA"


class ChandraBalaProfile(str, Enum):
    """PC-20. The two sources disagree; both are reported."""

    KALAPRAKASIKA_CHANDRASHTAMA = "kalaprakasika_chandrashtama"  # 8th only
    RAMAN_6_8_12 = "raman_6_8_12"


class UpagrahaProfile(str, Enum):
    """PC-25. BPHS Ch. 3 v. 61-65: the verse translation and the
    translator's note give different Vyatipata and Parivesha."""

    BPHS_VERSE = "bphs_verse"
    BPHS_TRANSLATOR_NOTE = "bphs_translator_note"


class GulikaProfile(str, Enum):
    """PC-26. Three readings, never assumed identical."""

    GULIKA_PORTION_START_BPHS_TRANSLATION = "gulika_portion_start_bphs_translation"
    GULIKA_PORTION_END = "gulika_portion_end"
    MANDI_PHALADEEPIKA_GHATI_TABLE = "mandi_phaladeepika_ghati_table"


class PranapadaSunReading(str, Enum):
    """PC-29. The verse does not say at which moment the Sun is taken."""

    SUN_AT_GIVEN_TIME = "sun_at_given_time"
    SUN_AT_SUNRISE = "sun_at_sunrise"


# -------------------------------------------------------------- provenance

PROVENANCE: tuple[ProvenanceDef, ...] = (
    ProvenanceDef(
        entry_id="prov.day",
        item="Civil day and Vara",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="The day and the weekday run from sunrise to sunrise; a day bears the tithi "
        "(and other elements) current at its sunrise.",
        references=(
            ref(SEWELL, "Art. 5 (p. 2), Art. 31-32 (pp. 19-20)", _OCR),
            ref(CRC, "Recommendation (8), p. 7", _IMG),
            ref(CRC, "Part B, Calendar for five years, explanation (6)", _OCR),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.sunrise",
        item="Sunrise and sunset",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="Sunrise and sunset are the moments the centre of the Sun is on the horizon "
        "as affected by refraction, taken as 30 minutes of arc (default); the upper-limb "
        "convention of Phase 4 is an explicit alternative.",
        references=(
            ref(
                CRC,
                "Part B, Calendar for five years, explanation (5); minutes, item (8)",
                _OCR,
                "reproduced to the minute on the printed calendar for Saka 1876 (pp. 41-42, "
                "page images)",
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.elements",
        item="Tithi, Nakshatra, Yoga, Karana",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="Tithi: the Moon gains 12 degrees on the Sun; Karana: half a tithi (6 degrees), "
        "Kimstughna, seven movable karanas eight times, Shakuni, Chatushpada, Naga; Yoga: the "
        "sum of the sidereal longitudes in 13 deg 20 min parts; Nakshatra: 13 deg 20 min of the "
        "sidereal zodiac from Ashwini; true (apparent) longitudes; nakshatras with the variable "
        "ayanamsa (Lahiri).",
        references=(
            ref(SEWELL, "Art. 7-10 (pp. 3-4)", _OCR),
            ref(CRC, "Recommendations (7) and (9), p. 7", _IMG),
            ref(RAMAN_MUH, "pp. 12-14 (yoga and karana lists)", _OCR),
            ref(KALAP, "p. 99 footnote (fixed karanas)", _OCR),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.month",
        item="Lunar month, adhika and kshaya",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="Amanta months run from new moon to new moon and are named after the saura "
        "month in which the new moon falls; two new moons in one saura month make the first "
        "month adhika; a saura month without a new moon gives a suppressed (kshaya) name. "
        "Purnimanta: the dark fortnight takes the name of the following month.",
        references=(
            ref(CRC, "Recommendation (6), p. 7", _IMG),
            ref(SEWELL, "Art. 13-14, 48, 51 (pp. 4-5, 29-31)", _OCR),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.saura_frames",
        item="Saura month frames",
        label=EvidenceLabel.UNRESOLVED_CONFLICT,
        statement="The Committee fixed the saura months 23 deg 15 min ahead of the vernal "
        "equinox; nakshatras use the variable (Lahiri) ayanamsa. Almanacs that measure "
        "sankrantis with the variable ayanamsa are not verified in a primary source read, so "
        "both frames are computed and reported; they differ by the growth of the ayanamsa "
        "since 1956.",
        references=(ref(CRC, "Recommendations (5) and (7), p. 7", _IMG),),
    ),
    ProvenanceDef(
        entry_id="prov.day_parts",
        item="Eighth parts of the day",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="The day is divided into eight parts; the lord of the day governs the first "
        "and the last, the other lords follow in weekday order; Saturn's part is Gulika. "
        "Yamaganda: 5th, 4th, 3rd, 2nd, 1st, 7th, 6th part Sunday to Saturday.",
        references=(
            ref(KALAP, "Ch. XXXIII p. 175 (text)", _IMG_T),
            ref(
                KALAP,
                "p. 176 tables",
                _IMG_T,
                "the tables use a 12-hour day from 6 o'clock; dividing the actual sunrise-to-"
                "sunset span into eight is PC-19's inference",
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.rahu_kalam",
        item="Rahu Kalam",
        label=EvidenceLabel.TRANSLATOR_NOTE,
        statement="Daytime only: Sunday 8th part, Monday 2nd, Tuesday 7th, Wednesday 5th, "
        "Thursday 6th, Friday 4th, Saturday 3rd (clock times for a 6-to-6 day).",
        references=(ref(KALAP, "p. 176 footnote", _IMG_T, "the translator's, not the text's"),),
    ),
    ProvenanceDef(
        entry_id="prov.hora",
        item="Hora",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="Horas of one hour from sunrise; the first is the weekday lord, each next "
        "lord the sixth in weekday order from the previous one.",
        references=(
            ref(KALAP, "p. 176 (text) and p. 177 table (hours from 6 o'clock)", _IMG_T),
            ref(
                "SRC-RAMAN-GRAHA-BHAVA-BALAS",
                "Art. 68-70",
                "IMAGE-ORIGINAL-ENGLISH",
                "equal hours from sunrise",
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.panchaka",
        item="Panchaka",
        label=EvidenceLabel.MODERN_TRADITION,
        statement="Two different things share the name. Nakshatra Panchaka: the Moon from the "
        "third quarter of Dhanishta to the end of Revati (Raman). Remainder Panchaka: tithi "
        "(1-30) + weekday (Sunday 1) + nakshatra (Ashwini 1) + lagna (Aries 1), divided by 9; "
        "remainders 1, 2, 4, 6, 8 are Mrityu, Agni, Raja, Chora, Roga (Raman; the same test as "
        "Kalaprakasika's 'add 15, 12, 10, 8, 4 and look for remainder 5').",
        references=(
            ref(RAMAN_MUH, "pp. 19-22 (remainder), p. 26 (nakshatra panchaka)", _OCR),
            ref(KALAP, "Ch. XXIX pp. 161-162", _OCR),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.bhadra",
        item="Bhadra",
        label=EvidenceLabel.MODERN_TRADITION,
        statement="Bhadra is the Vishti karana (Raman lists Visti among the karanas and calls "
        "Bhadra unfit for good work). Bhadra's residence (loka) rules are not implemented.",
        references=(ref(RAMAN_MUH, "pp. 13-14, 29", _OCR),),
    ),
    ProvenanceDef(
        entry_id="prov.tara_chandra",
        item="Tara Bala and Chandra Bala",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="Tara: count from the birth nakshatra to the day's, divide by 9; 1 Janma, "
        "2 Sampat, 3 Vipat, 4 Kshema, 5 Pratyak, 6 Sadhana, 7 Naidhana, 8 Mitra, 9 Parama "
        "Mitra. Chandra Bala: Kalaprakasika avoids only the 8th from the birth Moon sign "
        "(Chandrashtama); Raman avoids the 6th, 8th and 12th.",
        references=(
            ref(KALAP, "Ch. XXXIII pp. 166-167", _OCR),
            ref(RAMAN_MUH, "pp. 17-18", _OCR),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.special_points",
        item="Upagrahas, Gulika and Mandi, special Lagnas, Pranapada",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="BPHS Ch. 3 v. 61-74 and Ch. 5 v. 1-13; Phaladeepika Ch. 25 sl. 2; see PC-25 "
        "to PC-29 for the separately tagged readings.",
        references=(
            ref(BPHS, "Ch. 3 v. 61-74 (pp. 43-47), Ch. 5 v. 1-8 (pp. 61-64)", _IMG_T),
            ref(BPHS, "Ch. 5 v. 10-13 (p. 65)", _OCR_T),
            ref(PHALA, "Ch. 25 sl. 2", _OCR_T),
            ref(UK, "Ch. 1 (Gulika at the end of Saturn's part)", _OCR_T),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ghati",
        item="Ghati and pala",
        label=EvidenceLabel.ENGINEERING_CONVENTION,
        statement="A ghati is 24 minutes and a pala 24 seconds of civil time; elapsed time is "
        "counted from the sunrise of the chosen convention.",
        references=(ref(SEWELL, "Art. 8-9 tables (gh., pa.)", _OCR),),
    ),
)
