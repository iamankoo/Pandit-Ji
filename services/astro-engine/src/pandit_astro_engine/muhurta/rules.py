"""Muhurta rule sets (Phase 10; `docs/ASTROLOGY_STANDARDS.md` v1.23.0,
MU-01 to MU-14; sources in `research/ASTROLOGY_SOURCES.md` Group 23).

Each factor is a structured, source-tagged rule: the values the source
calls favourable, middling or unfavourable, what an unlisted value means,
and the source locator. Statements of effect (on health, family, wealth,
widowhood and the like) are not encoded -- `PRODUCT_POLICIES.md` forbids
fear-based claims -- and neither are rules that need inputs the product
does not collect or must not act on (a child's age for marriage, a
pregnancy, caste); those are listed as NOT_EVALUABLE factors.

Values: tithis "S1"-"S15", "K1"-"K14", "K30"; nakshatra, weekday and sign
identifiers as in the engine enums; houses counted whole-sign from the
rising sign.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.panchang.profiles import (
    KALAP,
    RAMAN_MUH,
    EvidenceLabel,
    SourceReference,
    ref,
)

MUHURTA_RULES_VERSION = "1.0.0"
_IMG_T = "IMAGE-TRANSLATION"
_OCR_T = "OCR-TRANSLATION"
_OCR = "OCR-ORIGINAL-ENGLISH"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Purpose(str, Enum):
    VIVAHA = "vivaha"  # marriage
    GRIHA_PRAVESHA = "griha_pravesha"  # entering a new house; also "housewarming"
    CHAULA = "chaula"  # first tonsure; "mundan"


#: Everyday names accepted for the purposes (MU-02). "Housewarming" is the
#: same ceremony as Griha Pravesha in the source read ("Grahapravesam -- the
#: Opening Ceremony").
PURPOSE_ALIASES: dict[str, Purpose] = {
    "marriage": Purpose.VIVAHA,
    "vivah": Purpose.VIVAHA,
    "griha_pravesh": Purpose.GRIHA_PRAVESHA,
    "housewarming": Purpose.GRIHA_PRAVESHA,
    "mundan": Purpose.CHAULA,
    "tonsure": Purpose.CHAULA,
}


class FactorKind(str, Enum):
    SUN_AYANA = "sun_ayana"  # uttarayana: Sun in Capricorn to Gemini (sidereal)
    PAKSHA = "paksha"
    TITHI = "tithi"
    NAKSHATRA = "nakshatra"
    WEEKDAY = "weekday"
    WEEKDAY_PAKSHA = "weekday_paksha"  # "monday:shukla"
    LAGNA_SIGN = "lagna_sign"
    LAGNA_MODALITY_NAVAMSA = "lagna_modality_navamsa"
    HOUSE_OCCUPANTS = "house_occupants"  # values "7:sun", ...
    HOUSE_VACANT = "house_vacant"  # values "vacant" / "occupied"
    HOUSE_ONLY_VENUS = "house_only_venus"
    TIME_OF_DAY = "time_of_day"  # "day" / "night"
    FORENOON = "forenoon"  # "forenoon_or_noon" / "afternoon" / "night"
    MOON_CONJUNCTION = "moon_conjunction"  # "alone" / "conjunct"
    YOGA = "yoga"
    BENEFIC_COMBUST = "benefic_combust"  # "none_combust" / "combust"
    TARA_COUNT = "tara_count"  # "1".."27" from the janma nakshatra
    TARA = "tara"  # nine-fold tara name
    CHANDRA_HOUSE = "chandra_house"  # "1".."12" from the janma rasi
    REMAINDER_PANCHAKA = "remainder_panchaka"
    NOT_EVALUATED = "not_evaluated"


class Classification(str, Enum):
    FAVOURABLE = "favourable"
    MIDDLING = "middling"
    UNFAVOURABLE = "unfavourable"
    NOT_LISTED = "not_listed"


class FactorRule(_Model):
    rule_id: str
    purpose: Purpose
    kind: FactorKind
    person_specific: bool = False
    house: int | None = None
    favourable: tuple[str, ...] = ()
    middling: tuple[str, ...] = ()
    unfavourable: tuple[str, ...] = ()
    unlisted: Classification = Classification.NOT_LISTED
    #: Values whose classification depends on a condition not evaluated.
    conditional: tuple[str, ...] = ()
    condition_reason: str | None = None
    #: For NOT_EVALUATED factors: why the engine does not evaluate it.
    not_evaluable_reason: str | None = None
    statement: str
    reference: SourceReference
    evidence_label: EvidenceLabel


_S = EvidenceLabel.SOURCE_SUPPORTED
_M = EvidenceLabel.MODERN_TRADITION
_I = EvidenceLabel.INFERENCE

ALL_TITHIS = tuple(f"S{i}" for i in range(1, 16)) + tuple(f"K{i}" for i in range(1, 15)) + ("K30",)
UTTARAYANA = ("capricorn", "aquarius", "pisces", "aries", "taurus", "gemini")
DAKSHINAYANA = ("cancer", "leo", "virgo", "libra", "scorpio", "sagittarius")
PLANETS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")


def _both(*numbers: int) -> tuple[str, ...]:
    """The same tithi number in both fortnights (15 and 30 excluded)."""
    return tuple(f"S{n}" for n in numbers) + tuple(f"K{n}" for n in numbers if n < 15)


def _kal(locator: str, level: str = _OCR_T) -> SourceReference:
    return ref(KALAP, locator, level)


# ------------------------------------------------------------ Chaula (V)

CHAULA: tuple[FactorRule, ...] = (
    FactorRule(
        rule_id="MU.CHAULA.AYANA", purpose=Purpose.CHAULA, kind=FactorKind.SUN_AYANA,
        favourable=UTTARAYANA, unfavourable=DAKSHINAYANA,
        statement="Most beneficent when the Sun is in its northern course; the other half of "
        "the year is unfavourable.",
        reference=_kal("Ch. V p. 37"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.PAKSHA_TITHI", purpose=Purpose.CHAULA, kind=FactorKind.TITHI,
        favourable=tuple(f"S{i}" for i in range(1, 16)) + ("K1", "K2", "K3", "K4", "K5"),
        unfavourable=tuple(f"K{i}" for i in range(6, 15)) + ("K30",),
        statement="The bright fortnight is favourable; of the dark fortnight only the first "
        "five tithis (some writers: seven, not applied).",
        reference=_kal("Ch. V pp. 37-38"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.TITHI", purpose=Purpose.CHAULA, kind=FactorKind.TITHI,
        favourable=_both(2, 3, 5, 7, 10, 11, 13),
        unfavourable=_both(1, 4, 6, 8, 9, 14) + ("S15", "K30"),
        statement="Fruitful: 2, 3, 5, 7, 10, 11, 13; avoid 1, 4, 6, 8, 9, 14, new and full moon.",
        reference=_kal("Ch. V p. 39"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.NAKSHATRA", purpose=Purpose.CHAULA, kind=FactorKind.NAKSHATRA,
        favourable=("ashwini", "mrigashira", "punarvasu", "pushya", "hasta", "chitra",
                    "shravana", "dhanishta", "revati"),
        middling=("rohini", "uttara_phalguni", "swati", "uttara_ashadha", "shatabhisha",
                  "uttara_bhadrapada"),
        unlisted=Classification.UNFAVOURABLE,
        statement="Nine favourable, six 'pretty good'; the remaining twelve are avoided.",
        reference=_kal("Ch. V p. 38"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.WEEKDAY", purpose=Purpose.CHAULA, kind=FactorKind.WEEKDAY,
        favourable=("thursday", "friday"),
        unfavourable=("sunday", "tuesday", "saturday"),
        conditional=("monday", "wednesday"),
        condition_reason="monday: see MU.CHAULA.MONDAY; wednesday: only when Mercury is not "
        "associated with a malefic (not evaluated)",
        statement="Monday, Wednesday, Thursday, Friday beneficent; Sunday, Tuesday, Saturday "
        "avoided (the caste-specific exceptions are not encoded).",
        reference=_kal("Ch. V pp. 38-39"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.MONDAY", purpose=Purpose.CHAULA, kind=FactorKind.WEEKDAY_PAKSHA,
        favourable=("monday:shukla",), unfavourable=("monday:krishna",),
        statement="Monday is good only in the bright fortnight.",
        reference=_kal("Ch. V p. 39"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.LAGNA", purpose=Purpose.CHAULA, kind=FactorKind.LAGNA_SIGN,
        favourable=("taurus", "gemini", "cancer", "virgo", "libra", "capricorn", "pisces"),
        unfavourable=("aquarius",),
        conditional=("aries", "leo", "scorpio", "sagittarius"),
        condition_reason="avoided unless occupied or aspected by benefics (not evaluated)",
        statement="Seven auspicious rising signs; Aries, Leo, Scorpio, Sagittarius avoided "
        "unless occupied or aspected by benefics; Aquarius totally avoided.",
        reference=_kal("Ch. V p. 39"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.HOUSE7", purpose=Purpose.CHAULA, kind=FactorKind.HOUSE_OCCUPANTS,
        house=7,
        favourable=("7:moon", "7:mercury", "7:jupiter"),
        unfavourable=("7:sun", "7:mars", "7:saturn", "7:venus", "7:rahu", "7:ketu"),
        statement="Sun, Mars, Saturn, Venus, Rahu or Ketu in the 7th are adverse; other "
        "planets there are favourable.",
        reference=_kal("Ch. V pp. 39-40"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.HOUSE8", purpose=Purpose.CHAULA, kind=FactorKind.HOUSE_ONLY_VENUS,
        house=8,
        favourable=("vacant", "venus_only"), unfavourable=("other_planet",),
        statement="No planet in the 8th except Venus.",
        reference=_kal("Ch. V p. 40"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.DAYTIME", purpose=Purpose.CHAULA, kind=FactorKind.TIME_OF_DAY,
        favourable=("day",), unfavourable=("night",),
        statement="Avoid night-time.",
        reference=_kal("Ch. V p. 40"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.BENEFIC_COMBUST", purpose=Purpose.CHAULA,
        kind=FactorKind.BENEFIC_COMBUST,
        favourable=("none_combust",), unfavourable=("combust",),
        statement="Jupiter and Venus should not be combust.",
        reference=_kal("Ch. V p. 37"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.TARA", purpose=Purpose.CHAULA, kind=FactorKind.TARA_COUNT,
        person_specific=True,
        unfavourable=("1", "10", "19"),
        statement="The birth nakshatra and the 10th and 19th from it are bad (stated for "
        "shaving after the tonsure; applied here as an inference).",
        reference=_kal("Ch. V p. 40"), evidence_label=_I,
    ),
    FactorRule(
        rule_id="MU.CHAULA.CHANDRASHTAMA", purpose=Purpose.CHAULA, kind=FactorKind.CHANDRA_HOUSE,
        person_specific=True,
        unfavourable=("8",),
        statement="Avoid the Moon in the 8th from the birth Moon (stated for shaving after "
        "the tonsure; applied here as an inference).",
        reference=_kal("Ch. V p. 40"), evidence_label=_I,
    ),
    FactorRule(
        rule_id="MU.CHAULA.CHILD_AGE", purpose=Purpose.CHAULA, kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="requires_child_birth_date",
        statement="Performed in the 3rd, 5th or 7th year of the child.",
        reference=_kal("Ch. V p. 37"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.CHAULA.MOTHER_PREGNANCY", purpose=Purpose.CHAULA,
        kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="requires_pregnancy_status_not_collected",
        statement="Not performed when the mother is pregnant (child under five).",
        reference=_kal("Ch. V p. 37"), evidence_label=_S,
    ),
)  # fmt: skip

# ----------------------------------------------------------- Vivaha (XIV)

VIVAHA: tuple[FactorRule, ...] = (
    FactorRule(
        rule_id="MU.VIVAHA.AYANA", purpose=Purpose.VIVAHA, kind=FactorKind.SUN_AYANA,
        favourable=UTTARAYANA, middling=DAKSHINAYANA,
        statement="Uttarayana is excellent; Dakshinayana of middling quality.",
        reference=_kal("Ch. XIV p. 79"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.NAKSHATRA", purpose=Purpose.VIVAHA, kind=FactorKind.NAKSHATRA,
        favourable=("rohini", "mrigashira", "magha", "uttara_phalguni", "hasta", "swati",
                    "anuradha", "mula", "uttara_ashadha", "uttara_bhadrapada", "revati"),
        unlisted=Classification.UNFAVOURABLE,
        statement="Eleven asterisms are the best; the others are adverse.",
        reference=_kal("Ch. XIV p. 79"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.TITHI_BEST", purpose=Purpose.VIVAHA, kind=FactorKind.TITHI,
        favourable=_both(2, 3, 5, 7, 10, 11, 13),
        middling=("K1", "S6", "K6", "S8", "K8", "S12", "K12", "S15"),
        statement="Best: 2, 3, 5, 7, 10, 11, 13; middling: 1 of the dark fortnight, 6, 8, 12 "
        "and the full moon.",
        reference=_kal("Ch. XIV p. 79"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.TITHI_AFTER_K8", purpose=Purpose.VIVAHA, kind=FactorKind.TITHI,
        unfavourable=tuple(f"K{i}" for i in range(9, 15)) + ("K30",),
        statement="All tithis after the 8th of the dark fortnight are inauspicious (a separate "
        "statement; it overlaps the 'best' list for dark 10, 11, 13 and both are reported).",
        reference=_kal("Ch. XIV p. 79"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.RIKTA", purpose=Purpose.VIVAHA, kind=FactorKind.TITHI,
        unfavourable=_both(4, 9, 14),
        statement="Rikta tithis (4, 9, 14) are inauspicious.",
        reference=_kal("Ch. XIV p. 86; Rikta defined Ch. XVIII p. 99"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.WANING_MOON", purpose=Purpose.VIVAHA, kind=FactorKind.PAKSHA,
        unfavourable=("krishna",),
        statement="Marriage when the Moon is on the wane is inauspicious.",
        reference=_kal("Ch. XIV p. 86"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.LAGNA", purpose=Purpose.VIVAHA, kind=FactorKind.LAGNA_SIGN,
        favourable=("gemini", "virgo", "libra"),
        unfavourable=("aries", "capricorn", "scorpio", "pisces"),
        unlisted=Classification.MIDDLING,
        statement="Best: Gemini, Virgo, Libra; avoid Aries, Capricorn, Scorpio, Pisces; the "
        "others middling.",
        reference=_kal("Ch. XIV p. 80"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.PRISHTODAYA", purpose=Purpose.VIVAHA, kind=FactorKind.LAGNA_SIGN,
        unfavourable=("aries", "taurus", "cancer", "sagittarius", "capricorn"),
        statement="Prishtodaya signs produce no good (a separate statement; it overlaps the "
        "'middling' Taurus, Cancer and Sagittarius and both are reported).",
        reference=_kal("Ch. XIV p. 86"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.WEEKDAY", purpose=Purpose.VIVAHA, kind=FactorKind.WEEKDAY,
        favourable=("monday", "wednesday", "thursday", "friday"),
        unfavourable=("saturday", "sunday", "tuesday"),
        statement="Choose Monday, Wednesday, Thursday or Friday; avoid Saturday, Sunday, "
        "Tuesday.",
        reference=_kal("Ch. XIV p. 80"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.HOUSE7_VACANT", purpose=Purpose.VIVAHA, kind=FactorKind.HOUSE_VACANT,
        house=7, favourable=("vacant",), unfavourable=("occupied",),
        statement="The 7th house from the rising sign should be vacant.",
        reference=_kal("Ch. XIV p. 82"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.VYATIPATA", purpose=Purpose.VIVAHA, kind=FactorKind.YOGA,
        unfavourable=("vyatipata",),
        statement="Vyatipata is inauspicious.",
        reference=_kal("Ch. XIV p. 86"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.MOON_CONJUNCTION", purpose=Purpose.VIVAHA,
        kind=FactorKind.MOON_CONJUNCTION,
        favourable=("alone",), unfavourable=("conjunct",),
        statement="The Moon in conjunction with any planet is adverse (conjunction read as "
        "the same sign: inference).",
        reference=_kal("Ch. XIV p. 87"), evidence_label=_I,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.TARA", purpose=Purpose.VIVAHA, kind=FactorKind.TARA_COUNT,
        person_specific=True,
        favourable=("2", "4", "6", "8", "9"),
        unfavourable=("1", "3", "5", "7", "10", "19"),
        statement="The 2nd, 4th, 6th, 8th, 9th from the birth nakshatra are favourable; the "
        "birth nakshatra and the 3rd, 5th, 7th, 10th and 19th are avoided.",
        reference=_kal("Ch. XIV pp. 85-86"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.MONTH", purpose=Purpose.VIVAHA, kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="month_system_unspecified",
        statement="Ashadha, Bhadrapada, Margashira and Magha are not good (the text does not "
        "say whether lunar or Tamil solar months are meant).",
        reference=_kal("Ch. XIV pp. 84-85"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.JUPITER_FROM_JANMA", purpose=Purpose.VIVAHA,
        kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="requires_role_specific_partner_input",
        statement="Jupiter's transit counted from one named partner's birth Moon.",
        reference=_kal("Ch. XIV p. 79"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.HELIACAL", purpose=Purpose.VIVAHA, kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="requires_heliacal_visibility",
        statement="Days after the reappearance and before the setting of Venus and Jupiter.",
        reference=_kal("Ch. XIV p. 80"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.VIVAHA.PERIOD_ENDS", purpose=Purpose.VIVAHA, kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="boundary_undefined",
        statement="Towards the end of a paksha, ritu, ayana or year; Vishu; "
        "Shadaseethimukha.",
        reference=_kal("Ch. XIV pp. 85-86"), evidence_label=_S,
    ),
)  # fmt: skip

# ---------------------------------------------------- Griha Pravesha (XXVI)

GRIHA_PRAVESHA: tuple[FactorRule, ...] = (
    FactorRule(
        rule_id="MU.GRIHA.PAKSHA_RANGE", purpose=Purpose.GRIHA_PRAVESHA, kind=FactorKind.TITHI,
        favourable=tuple(f"S{i}" for i in range(1, 16)) + tuple(f"K{i}" for i in range(1, 11)),
        unfavourable=("K11", "K12", "K13", "K14", "K30"),
        statement="In the bright fortnight or within the first ten tithis of the dark "
        "fortnight.",
        reference=_kal("Ch. XXVI p. 130"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.FORENOON", purpose=Purpose.GRIHA_PRAVESHA, kind=FactorKind.FORENOON,
        favourable=("forenoon_or_noon",), unfavourable=("afternoon", "night"),
        statement="In the forenoon or at noon (noon taken as the midpoint of sunrise and "
        "sunset: inference; the night variant of 'some astrologers' is not applied).",
        reference=_kal("Ch. XXVI pp. 130-131"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.NAKSHATRA", purpose=Purpose.GRIHA_PRAVESHA, kind=FactorKind.NAKSHATRA,
        favourable=("rohini", "mrigashira", "punarvasu", "pushya", "uttara_phalguni", "hasta",
                    "anuradha", "uttara_ashadha", "shravana", "shatabhisha",
                    "uttara_bhadrapada", "revati"),
        statement="Twelve best asterisms.",
        reference=_kal("Ch. XXVI p. 131"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.TITHI", purpose=Purpose.GRIHA_PRAVESHA, kind=FactorKind.TITHI,
        favourable=("K1",) + _both(2, 3, 5, 7, 10) + ("S11", "S13"),
        statement="Best: 1 of the dark fortnight, 2, 3, 5, 7, 10, and 11 and 13 of the bright "
        "fortnight.",
        reference=_kal("Ch. XXVI p. 131"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.WEEKDAY", purpose=Purpose.GRIHA_PRAVESHA, kind=FactorKind.WEEKDAY,
        favourable=("monday", "wednesday", "thursday", "friday"),
        middling=("saturday",), unfavourable=("sunday", "tuesday"),
        statement="Monday, Wednesday, Thursday, Friday auspicious; Saturday neutral; the others "
        "avoided.",
        reference=_kal("Ch. XXVI p. 131"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.LAGNA", purpose=Purpose.GRIHA_PRAVESHA,
        kind=FactorKind.LAGNA_MODALITY_NAVAMSA,
        favourable=("fixed", "movable_taurus_navamsa"), middling=("dual",),
        unfavourable=("movable",),
        statement="A fixed rising sign; dual signs middling; movable signs not considered "
        "unless the rising navamsa is Taurus.",
        reference=_kal("Ch. XXVI p. 131"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.HOUSE8_VACANT", purpose=Purpose.GRIHA_PRAVESHA,
        kind=FactorKind.HOUSE_VACANT, house=8,
        favourable=("vacant",), unfavourable=("occupied",),
        statement="The 8th house from the rising sign should be vacant.",
        reference=_kal("Ch. XXVI p. 132"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.BENEFIC_COMBUST", purpose=Purpose.GRIHA_PRAVESHA,
        kind=FactorKind.BENEFIC_COMBUST,
        favourable=("none_combust",), unfavourable=("combust",),
        statement="Entry into a house should not begin when Jupiter and Venus are combust.",
        reference=_kal("Ch. XXV p. 129"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.VENUS_DIRECTION", purpose=Purpose.GRIHA_PRAVESHA,
        kind=FactorKind.NOT_EVALUATED, not_evaluable_reason="requires_entrance_direction",
        statement="Venus should not be in the opposite direction or on the left.",
        reference=_kal("Ch. XXVI p. 132"), evidence_label=_S,
    ),
    FactorRule(
        rule_id="MU.GRIHA.OWNER_PREGNANCY", purpose=Purpose.GRIHA_PRAVESHA,
        kind=FactorKind.NOT_EVALUATED,
        not_evaluable_reason="requires_pregnancy_status_not_collected",
        statement="Not when the owner's wife is pregnant.",
        reference=_kal("Ch. XXV p. 129"), evidence_label=_S,
    ),
)  # fmt: skip

# ----------------------------------------------- common (Raman 1948, modern)


def _common(purpose: Purpose, panchaka_avoid: tuple[str, ...] | None) -> tuple[FactorRule, ...]:
    """Raman's Tarabala and Chandrabala ("common to almost all elections")
    and, for the important ceremonies he names (marriage, entry into new
    houses), the remainder Panchaka."""
    bad = ("mrityu", "agni", "raja", "chora", "roga")
    rules = (
        FactorRule(
            rule_id=f"MU.{purpose.name}.TARABALA_RAMAN", purpose=purpose,
            kind=FactorKind.TARA, person_specific=True,
            favourable=("sampat", "kshema", "sadhana", "mitra", "parama_mitra"),
            unfavourable=("janma", "vipat", "pratyak", "naidhana"),
            statement="Tarabala, common to almost all elections.",
            reference=ref(RAMAN_MUH, "pp. 17-18, 22", _OCR), evidence_label=_M,
        ),
        FactorRule(
            rule_id=f"MU.{purpose.name}.CHANDRABALA_RAMAN", purpose=purpose,
            kind=FactorKind.CHANDRA_HOUSE, person_specific=True,
            unfavourable=("6", "8", "12"),
            statement="Chandrabala: the Moon not in the 6th, 8th or 12th from the birth Moon.",
            reference=ref(RAMAN_MUH, "p. 18", _OCR), evidence_label=_M,
        ),
    )  # fmt: skip
    if panchaka_avoid is None:
        return rules
    return rules + (
        FactorRule(
            rule_id=f"MU.{purpose.name}.PANCHAKA_RAMAN", purpose=purpose,
            kind=FactorKind.REMAINDER_PANCHAKA,
            favourable=("none",),
            middling=tuple(b for b in bad if b not in panchaka_avoid),
            unfavourable=panchaka_avoid,
            statement="Remainder Panchaka; the purpose-specific kinds are avoided, the others "
            "are 'the lesser evil'.",
            reference=ref(RAMAN_MUH, "pp. 19-21", _OCR), evidence_label=_M,
        ),
    )  # fmt: skip


RULES: dict[Purpose, tuple[FactorRule, ...]] = {
    Purpose.CHAULA: CHAULA + _common(Purpose.CHAULA, None),
    Purpose.VIVAHA: VIVAHA + _common(Purpose.VIVAHA, ("roga", "mrityu")),
    Purpose.GRIHA_PRAVESHA: GRIHA_PRAVESHA
    + _common(Purpose.GRIHA_PRAVESHA, ("mrityu", "agni", "raja", "chora", "roga")),
}


def export_rules() -> dict[str, object]:
    """The rule sets as one versioned, JSON-serializable document (MU-03,
    owner decision of 2026-09-25): every rule with its identifier, purpose,
    classification sets, source locator, verification level and evidence
    label, so the data can be audited, explained or migrated to another rule
    store without loss."""
    return {
        "rules_version": MUHURTA_RULES_VERSION,
        "purposes": {
            purpose.value: [rule.model_dump(mode="json") for rule in rules]
            for purpose, rules in RULES.items()
        },
        "aliases": {alias: purpose.value for alias, purpose in PURPOSE_ALIASES.items()},
    }
