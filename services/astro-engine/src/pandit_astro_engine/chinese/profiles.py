"""Chinese Four Pillars methodology profile and provenance (Phase 9 WP-H;
`docs/ASTROLOGY_STANDARDS.md` v1.18.0, CN-01 to CN-14; sources in
`research/ASTROLOGY_SOURCES.md` Group 19).

One profile, `CHINESE_BAZI_FOUR_PILLARS_SOLAR_TERMS_V1`: the four calendar
pillars only. Luck cycles need the person's sex (not collected: NOT_EVALUABLE
by project rule); hidden stems, ten gods, Na Yin and every interpretive
layer are not implemented.
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


PROFILE_ID = "CHINESE_BAZI_FOUR_PILLARS_SOLAR_TERMS_V1"

SANMING = "SRC-SANMING-TONGHUI-WAN-MINYING"
HKO = "SRC-HKO-CALENDAR"
_WEB_SRC = "WEB-TRANSCRIPTION-SOURCE-LANGUAGE (unreviewed)"

PROVENANCE: tuple[ProvenanceDef, ...] = (
    ProvenanceDef(
        entry_id="prov.solar_terms",
        item="Solar terms",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "The 24 solar terms are the instants the Sun's apparent (tropical) longitude reaches "
            "multiples of 15 degrees; 立春 is 315 degrees."
        ),
        references=(
            SourceReference(
                source_id=HKO,
                locator="'The 24 Solar Terms' (Table 1) and 24SolarTerms_YYYY.xml, 2020-2028",
                verification_level="DOCUMENTATION-DIRECT",
                note=(
                    "Pandit Ji's instants agree with HKO's published minute-rounded times for "
                    "all 216 terms (largest difference 30.2 s; fixture "
                    "hko_solar_terms_and_year_names.json)."
                ),
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.year",
        item="Year pillar",
        label=EvidenceLabel.MODERN_TRADITION,
        statement=(
            "The year pillar changes at 立春, not at the lunar new year; index (Y - 4) mod 60. "
            "The popular zodiac year that changes at the lunar new year is a different "
            "convention and is not produced."
        ),
        references=(
            SourceReference(
                source_id=SANMING,
                locator=(
                    "卷二 論遁月時 ('正月起丙寅'); 卷二 大運 passage (立春 opens the next month)"
                ),
                verification_level=_WEB_SRC,
                note=(
                    "The text counts months from 寅 opened by the jie terms; it was not found "
                    "stating the year boundary in so many words, hence 'modern_tradition'. "
                    "The sexagenary year labels agree with HKO's for 1901-2100 samples."
                ),
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.month",
        item="Month pillar",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Months open at the twelve jie terms (315, 345, 15, ... degrees); the 寅 month's "
            "stem from the year stem: 甲己 丙, 乙庚 戊, 丙辛 庚, 丁壬 壬, 戊癸 甲."
        ),
        references=(
            SourceReference(
                source_id=SANMING,
                locator="卷二 論遁月時, 古歌 '甲己之年丙作首 ...'",
                verification_level=_WEB_SRC,
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.day",
        item="Day pillar",
        label=EvidenceLabel.ENGINEERING_EVIDENCE,
        statement=(
            "The continuous sixty-day count, index (JDN + 49) mod 60 with 甲子 = 0, on the "
            "local date in the chosen time basis."
        ),
        references=(
            SourceReference(
                source_id="SRC-ALMANAC-SECONDARY",
                locator="1 January 2000 = 己卯年 丙子月 戊午日",
                verification_level="SECONDARY",
                note=(
                    "Several almanac sites agree; no primary or scholarly table was read "
                    "(Academia Sinica's converter could not be queried automatically). "
                    "Confidence MEDIUM."
                ),
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.hour",
        item="Hour pillar",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Twelve double hours, 子 = 23:00-01:00; the 子 hour's stem from the day stem: "
            "甲己 甲, 乙庚 丙, 丙辛 戊, 丁壬 庚, 戊癸 壬."
        ),
        references=(
            SourceReference(
                source_id=SANMING,
                locator="卷二 論遁月時, 古歌 '甲己還加甲 ...'",
                verification_level=_WEB_SRC,
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.conventions",
        item="Time basis and day boundary",
        label=EvidenceLabel.UNRESOLVED_CONFLICT,
        statement=(
            "Clock time, local mean solar time and local apparent solar time are all in use, as "
            "are a day that changes at 23:00 (the 子 hour) and at midnight; both are explicit "
            "request fields with no default. With the midnight boundary, the hour stem of "
            "23:00-24:00 is not evaluated."
        ),
        references=(),
    ),
    ProvenanceDef(
        entry_id="prov.elements",
        item="Elements, polarity, animals",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement="Stem and branch elements and polarity, and the branch animals.",
        references=(
            SourceReference(
                source_id=SANMING,
                locator="卷二 論十干合, 論地支屬相; 卷三 論十干祿",
                verification_level=_WEB_SRC,
            ),
        ),
    ),
)
