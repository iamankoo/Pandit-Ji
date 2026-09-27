"""North Indian Ashtakoot after Muhurta Chintamani, Vivaha Prakarana v. 21-37
(Phase 11; `docs/ASTROLOGY_STANDARDS.md` v1.25.0, AK-01 to AK-16).

Pure functions over the two birth-Moon placements. Point values follow the
Daivajna Manohara as quoted in the Piyushadhara commentary and tabulated in
Pt. Mahidhara Sharma's edition. No role (bride or groom) is known: a factor
the source scores from a named partner is evaluated only when both possible
assignments give the same points; otherwise it is not evaluable. The
traditional 36-point total exists only when all eight kutas are evaluated.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from types import MappingProxyType
from typing import Final

from pandit_astro_engine.compatibility.constants import (
    DoshaState,
    FactorReason,
    FactorStatus,
)
from pandit_astro_engine.compatibility.models import (
    AshtakootTotal,
    DoshaRecord,
    FactorResult,
    FactValue,
    MoonPlacement,
)
from pandit_astro_engine.compatibility.profiles import EvidenceLabel
from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.lordship import sign_lord
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_ORDER, Nakshatra
from pandit_astro_engine.rashi import Rashi, rashi_index
from pandit_astro_engine.shadbala.constants import NATURAL_ENEMIES, NATURAL_FRIENDS

N = Nakshatra
R = Rashi

# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


class Varna(str, Enum):
    BRAHMIN = "brahmin"
    KSHATRIYA = "kshatriya"
    VAISHYA = "vaishya"
    SHUDRA = "shudra"


#: v. 22 ("dvija jhashali-karkatah, tato nripa, vishah, anghrijah").
VARNA: Final = MappingProxyType(
    {
        R.CANCER: Varna.BRAHMIN,
        R.SCORPIO: Varna.BRAHMIN,
        R.PISCES: Varna.BRAHMIN,
        R.ARIES: Varna.KSHATRIYA,
        R.LEO: Varna.KSHATRIYA,
        R.SAGITTARIUS: Varna.KSHATRIYA,
        R.TAURUS: Varna.VAISHYA,
        R.VIRGO: Varna.VAISHYA,
        R.CAPRICORN: Varna.VAISHYA,
        R.GEMINI: Varna.SHUDRA,
        R.LIBRA: Varna.SHUDRA,
        R.AQUARIUS: Varna.SHUDRA,
    }
)
_VARNA_RANK: Final = MappingProxyType(
    {Varna.BRAHMIN: 4, Varna.KSHATRIYA: 3, Varna.VAISHYA: 2, Varna.SHUDRA: 1}
)

#: v. 23 as read with the Piyushadhara: the human signs and the water signs.
HUMAN_SIGNS: Final = frozenset({R.GEMINI, R.VIRGO, R.LIBRA})
WATER_SIGNS: Final = frozenset({R.CANCER, R.CAPRICORN, R.AQUARIUS, R.PISCES})


class Yoni(str, Enum):
    HORSE = "horse"
    ELEPHANT = "elephant"
    SHEEP = "sheep"
    SERPENT = "serpent"
    DOG = "dog"
    CAT = "cat"
    RAT = "rat"
    COW = "cow"
    BUFFALO = "buffalo"
    TIGER = "tiger"
    DEER = "deer"
    MONKEY = "monkey"
    MONGOOSE = "mongoose"
    LION = "lion"


#: v. 25-26 (Abhijit, the mongoose's other nakshatra, is not a Moon nakshatra).
YONI: Final = MappingProxyType(
    {
        N.ASHWINI: Yoni.HORSE,
        N.SHATABHISHA: Yoni.HORSE,
        N.SWATI: Yoni.BUFFALO,
        N.HASTA: Yoni.BUFFALO,
        N.DHANISHTA: Yoni.LION,
        N.PURVA_BHADRAPADA: Yoni.LION,
        N.BHARANI: Yoni.ELEPHANT,
        N.REVATI: Yoni.ELEPHANT,
        N.PUSHYA: Yoni.SHEEP,
        N.KRITTIKA: Yoni.SHEEP,
        N.SHRAVANA: Yoni.MONKEY,
        N.PURVA_ASHADHA: Yoni.MONKEY,
        N.UTTARA_ASHADHA: Yoni.MONGOOSE,
        N.MRIGASHIRA: Yoni.SERPENT,
        N.ROHINI: Yoni.SERPENT,
        N.JYESHTHA: Yoni.DEER,
        N.ANURADHA: Yoni.DEER,
        N.MULA: Yoni.DOG,
        N.ARDRA: Yoni.DOG,
        N.PUNARVASU: Yoni.CAT,
        N.ASHLESHA: Yoni.CAT,
        N.MAGHA: Yoni.RAT,
        N.PURVA_PHALGUNI: Yoni.RAT,
        N.VISHAKHA: Yoni.TIGER,
        N.CHITRA: Yoni.TIGER,
        N.UTTARA_PHALGUNI: Yoni.COW,
        N.UTTARA_BHADRAPADA: Yoni.COW,
    }
)

#: v. 25-26: the yonis named in one quarter-verse are in great enmity.
YONI_GREAT_ENMITY: Final = frozenset(
    frozenset(pair)
    for pair in (
        (Yoni.HORSE, Yoni.BUFFALO),
        (Yoni.LION, Yoni.ELEPHANT),
        (Yoni.SHEEP, Yoni.MONKEY),
        (Yoni.MONGOOSE, Yoni.SERPENT),
        (Yoni.DEER, Yoni.DOG),
        (Yoni.CAT, Yoni.RAT),
        (Yoni.TIGER, Yoni.COW),
    )
)

#: Mahidhara's printed "yonigunah" table (p. 86), transcribed from the page
#: image, rows and columns in this order.
YONI_TABLE_ORDER: Final = (
    Yoni.HORSE,
    Yoni.ELEPHANT,
    Yoni.SHEEP,
    Yoni.SERPENT,
    Yoni.DOG,
    Yoni.CAT,
    Yoni.RAT,
    Yoni.COW,
    Yoni.BUFFALO,
    Yoni.TIGER,
    Yoni.DEER,
    Yoni.MONKEY,
    Yoni.MONGOOSE,
    Yoni.LION,
)
YONI_TABLE: Final = (
    (4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1),
    (2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 2, 2, 0),
    (2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1),
    (3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2),
    (2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1),
    (2, 2, 2, 3, 2, 4, 0, 2, 2, 2, 3, 3, 2, 2),
    (2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 2, 1),
    (1, 2, 3, 2, 3, 2, 2, 4, 3, 0, 3, 2, 2, 1),
    (0, 2, 3, 2, 2, 2, 2, 3, 4, 1, 2, 3, 2, 2),
    (1, 2, 1, 1, 1, 1, 2, 1, 1, 4, 1, 1, 2, 2),
    (3, 3, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 2),
    (3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2),
    (2, 3, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2),
    (1, 0, 1, 2, 1, 1, 0, 0, 3, 2, 1, 2, 2, 4),
)


class Gana(str, Enum):
    DEVA = "deva"
    MANUSHYA = "manushya"
    RAKSHASA = "rakshasa"


#: v. 29.
GANA: Final = MappingProxyType(
    {
        **{
            n: Gana.RAKSHASA
            for n in (
                N.MAGHA,
                N.ASHLESHA,
                N.DHANISHTA,
                N.JYESHTHA,
                N.MULA,
                N.SHATABHISHA,
                N.KRITTIKA,
                N.CHITRA,
                N.VISHAKHA,
            )
        },
        **{
            n: Gana.MANUSHYA
            for n in (
                N.PURVA_PHALGUNI,
                N.PURVA_ASHADHA,
                N.PURVA_BHADRAPADA,
                N.UTTARA_PHALGUNI,
                N.UTTARA_ASHADHA,
                N.UTTARA_BHADRAPADA,
                N.ROHINI,
                N.BHARANI,
                N.ARDRA,
            )
        },
        **{
            n: Gana.DEVA
            for n in (
                N.ANURADHA,
                N.PUNARVASU,
                N.MRIGASHIRA,
                N.SHRAVANA,
                N.REVATI,
                N.SWATI,
                N.ASHWINI,
                N.PUSHYA,
                N.HASTA,
            )
        },
    }
)


class Nadi(str, Enum):
    ADYA = "adya"
    MADHYA = "madhya"
    ANTYA = "antya"


#: v. 34 ("jyeshtha raudra aryama ambhahpati bha-yuga-yugam dasrabham ...").
NADI: Final = MappingProxyType(
    {
        **{
            n: Nadi.ADYA
            for n in (
                N.JYESHTHA,
                N.MULA,
                N.ARDRA,
                N.PUNARVASU,
                N.UTTARA_PHALGUNI,
                N.HASTA,
                N.SHATABHISHA,
                N.PURVA_BHADRAPADA,
                N.ASHWINI,
            )
        },
        **{
            n: Nadi.MADHYA
            for n in (
                N.PUSHYA,
                N.MRIGASHIRA,
                N.CHITRA,
                N.ANURADHA,
                N.BHARANI,
                N.DHANISHTA,
                N.PURVA_ASHADHA,
                N.PURVA_PHALGUNI,
                N.UTTARA_BHADRAPADA,
            )
        },
        **{
            n: Nadi.ANTYA
            for n in (
                N.SWATI,
                N.VISHAKHA,
                N.KRITTIKA,
                N.ROHINI,
                N.ASHLESHA,
                N.MAGHA,
                N.UTTARA_ASHADHA,
                N.SHRAVANA,
                N.REVATI,
            )
        },
    }
)

#: Daivajna Manohara via the Piyushadhara (v. 21 commentary): weights 1-8.
MAX_POINTS: Final = MappingProxyType(
    {
        "varna": 1.0,
        "vashya": 2.0,
        "tara": 3.0,
        "yoni": 4.0,
        "graha_maitri": 5.0,
        "gana": 6.0,
        "bhakoot": 7.0,
        "nadi": 8.0,
    }
)
KUTA_ORDER: Final = tuple(MAX_POINTS)

#: v. 24: remainders (by nine) that are unfavourable.
TARA_UNFAVOURABLE: Final = frozenset({3, 5, 7})

#: Daivajna Manohara: points for the pair of relations each lord holds
#: towards the other (unordered).
GRAHA_MAITRI_POINTS: Final = MappingProxyType(
    {
        frozenset({"friend"}): 5.0,
        frozenset({"friend", "neutral"}): 4.0,
        frozenset({"neutral"}): 3.0,
        frozenset({"friend", "enemy"}): 1.0,
        frozenset({"neutral", "enemy"}): 0.5,
        frozenset({"enemy"}): 0.0,
    }
)

#: v. 31: Moon-sign distances (counted both ways) that are unfavourable.
BHAKOOT_UNFAVOURABLE: Final = MappingProxyType(
    {
        frozenset({6, 8}): "shadashtaka",
        frozenset({5, 9}): "navapanchama",
        frozenset({2, 12}): "dvirdvadasha",
    }
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def nakshatra_count(start: Nakshatra, end: Nakshatra) -> int:
    """Inclusive count from `start` to `end` (1 when they are the same)."""
    return (NAKSHATRA_ORDER.index(end) - NAKSHATRA_ORDER.index(start)) % 27 + 1


def sign_count(start: Rashi, end: Rashi) -> int:
    """Inclusive count from `start` to `end` (1 when they are the same)."""
    return (rashi_index(end) - rashi_index(start)) % 12 + 1


def tara_remainder(count: int) -> int:
    remainder = count % 9
    return 9 if remainder == 0 else remainder


def relation(of: CelestialBody, towards: CelestialBody) -> str:
    """How `of` regards `towards` in the locked Phase 6 natural table."""
    if towards in NATURAL_FRIENDS[of]:
        return "friend"
    if towards in NATURAL_ENEMIES[of]:
        return "enemy"
    return "neutral"


def yoni_table_points(first: Yoni, second: Yoni) -> tuple[int, int]:
    i, j = YONI_TABLE_ORDER.index(first), YONI_TABLE_ORDER.index(second)
    return YONI_TABLE[i][j], YONI_TABLE[j][i]


def vashya_relation(controller: Rashi, sign: Rashi) -> bool | None:
    """Whether `sign` is vashya to `controller` as far as v. 23 states it;
    None where the verse leaves it to 'worldly usage'."""
    if controller in HUMAN_SIGNS:
        return sign is not R.LEO
    if controller is R.LEO:
        return sign is not R.SCORPIO
    return None


def missing_inputs(
    a: MoonPlacement, b: MoonPlacement, fields: tuple[str, ...]
) -> FactorReason | None:
    for person in (a, b):
        if person.birth_time_status is BirthTimeStatus.NOT_EVALUABLE:
            return FactorReason.BIRTH_TIME_NOT_EVALUABLE
    for person in (a, b):
        if any(getattr(person, name) is None for name in fields):
            return FactorReason.MOON_POSITION_UNCERTAIN
    return None


def _not_evaluable(
    factor_id: str,
    name: str,
    reason: FactorReason,
    role_dependent: bool,
    label: EvidenceLabel,
    facts: dict[str, FactValue] | None = None,
    note: str = "",
) -> FactorResult:
    return FactorResult(
        factor_id=factor_id,
        name=name,
        status=FactorStatus.NOT_EVALUABLE,
        reason=reason,
        max_points=MAX_POINTS[factor_id],
        role_dependent=role_dependent,
        role_invariant=False if reason is FactorReason.ROLE_REQUIRED_NOT_COLLECTED else None,
        label=label,
        facts=facts or {},
        note=note,
        provenance_ids=(f"prov.ak.{factor_id}",),
    )


def _evaluated(
    factor_id: str,
    name: str,
    points: float,
    role_dependent: bool,
    label: EvidenceLabel,
    facts: dict[str, FactValue],
    note: str = "",
) -> FactorResult:
    return FactorResult(
        factor_id=factor_id,
        name=name,
        status=FactorStatus.EVALUATED,
        points=points,
        max_points=MAX_POINTS[factor_id],
        role_dependent=role_dependent,
        role_invariant=True if role_dependent else None,
        label=label,
        facts=facts,
        note=note,
        provenance_ids=(f"prov.ak.{factor_id}",),
    )


# --------------------------------------------------------------------------
# The eight kutas
# --------------------------------------------------------------------------


def varna(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Varna"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _not_evaluable("varna", name, missing, True, EvidenceLabel.SOURCE_SUPPORTED)
    assert a.rashi is not None and b.rashi is not None
    va, vb = VARNA[a.rashi], VARNA[b.rashi]
    facts: dict[str, FactValue] = {"varna_a": va.value, "varna_b": vb.value}

    def points(groom: Varna, bride: Varna) -> float:
        return 1.0 if _VARNA_RANK[groom] >= _VARNA_RANK[bride] else 0.0

    if points(va, vb) == points(vb, va):
        return _evaluated(
            "varna",
            name,
            points(va, vb),
            True,
            EvidenceLabel.SOURCE_SUPPORTED,
            facts,
            "Equal varnas: one guna under either assignment. Some authorities give half a guna "
            "(Piyushadhara, 'ke'pyahuh sadrshe dalam'); not this profile.",
        )
    return _not_evaluable(
        "varna",
        name,
        FactorReason.ROLE_REQUIRED_NOT_COLLECTED,
        True,
        EvidenceLabel.SOURCE_SUPPORTED,
        facts,
        "One guna only when the groom's varna is equal or higher.",
    )


def vashya(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Vashya"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _not_evaluable("vashya", name, missing, True, EvidenceLabel.UNRESOLVED_CONFLICT)
    assert a.rashi is not None and b.rashi is not None
    facts: dict[str, FactValue] = {
        "b_vashya_to_a_by_verse": vashya_relation(a.rashi, b.rashi),
        "a_vashya_to_b_by_verse": vashya_relation(b.rashi, a.rashi),
        "b_water_sign_food_of_human_sign_a": a.rashi in HUMAN_SIGNS and b.rashi in WATER_SIGNS,
        "a_water_sign_food_of_human_sign_b": b.rashi in HUMAN_SIGNS and a.rashi in WATER_SIGNS,
    }
    return _not_evaluable(
        "vashya",
        name,
        FactorReason.READING_AMBIGUOUS,
        True,
        EvidenceLabel.UNRESOLVED_CONFLICT,
        facts,
        "The verse defers most sign relations to 'worldly usage' and the point schemes read "
        "disagree; the verse-level relations are reported, no points are given.",
    )


def tara(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Tara Kuta"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _not_evaluable("tara", name, missing, False, EvidenceLabel.SOURCE_SUPPORTED)
    assert a.nakshatra is not None and b.nakshatra is not None
    count_ab = nakshatra_count(a.nakshatra, b.nakshatra)
    count_ba = nakshatra_count(b.nakshatra, a.nakshatra)
    rem_ab, rem_ba = tara_remainder(count_ab), tara_remainder(count_ba)
    good = (rem_ab not in TARA_UNFAVOURABLE) + (rem_ba not in TARA_UNFAVOURABLE)
    return _evaluated(
        "tara",
        name,
        {2: 3.0, 1: 1.5, 0: 0.0}[good],
        False,
        EvidenceLabel.SOURCE_SUPPORTED,
        {
            "count_a_to_b": count_ab,
            "count_b_to_a": count_ba,
            "remainder_a_to_b": rem_ab,
            "remainder_b_to_a": rem_ba,
            "favourable_directions": good,
        },
        "Matching Tara Kuta; not the Phase 10 Muhurta Tara Bala.",
    )


def yoni(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Yoni"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _not_evaluable("yoni", name, missing, False, EvidenceLabel.COMMENTARY)
    assert a.nakshatra is not None and b.nakshatra is not None
    ya, yb = YONI[a.nakshatra], YONI[b.nakshatra]
    facts: dict[str, FactValue] = {"yoni_a": ya.value, "yoni_b": yb.value}
    if ya is yb:
        return _evaluated("yoni", name, 4.0, False, EvidenceLabel.SOURCE_SUPPORTED, facts)
    if frozenset({ya, yb}) in YONI_GREAT_ENMITY:
        facts["great_enmity"] = True
        return _evaluated("yoni", name, 0.0, False, EvidenceLabel.SOURCE_SUPPORTED, facts)
    first, second = yoni_table_points(ya, yb)
    facts.update({"table_cell_ab": first, "table_cell_ba": second})
    if first != second:
        return _not_evaluable(
            "yoni",
            name,
            FactorReason.SOURCE_TABLE_ASYMMETRIC,
            False,
            EvidenceLabel.COMMENTARY,
            facts,
            "The printed table's two cells for this pair differ and no rule settles it.",
        )
    return _evaluated("yoni", name, float(first), False, EvidenceLabel.COMMENTARY, facts)


def graha_maitri(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Graha Maitri"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _not_evaluable("graha_maitri", name, missing, False, EvidenceLabel.SOURCE_SUPPORTED)
    assert a.rashi is not None and b.rashi is not None
    la, lb = sign_lord(a.rashi), sign_lord(b.rashi)
    facts: dict[str, FactValue] = {"lord_a": la.value, "lord_b": lb.value}
    if la is lb:
        facts["same_lord"] = True
        return _evaluated("graha_maitri", name, 5.0, False, EvidenceLabel.SOURCE_SUPPORTED, facts)
    rab, rba = relation(la, lb), relation(lb, la)
    facts.update({"a_lord_towards_b_lord": rab, "b_lord_towards_a_lord": rba})
    return _evaluated(
        "graha_maitri",
        name,
        GRAHA_MAITRI_POINTS[frozenset({rab, rba})],
        False,
        EvidenceLabel.SOURCE_SUPPORTED,
        facts,
    )


def gana(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Gana"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _not_evaluable("gana", name, missing, True, EvidenceLabel.UNRESOLVED_CONFLICT)
    assert a.nakshatra is not None and b.nakshatra is not None
    ga, gb = GANA[a.nakshatra], GANA[b.nakshatra]
    facts: dict[str, FactValue] = {"gana_a": ga.value, "gana_b": gb.value}
    if ga is gb:
        return _evaluated(
            "gana",
            name,
            6.0,
            True,
            EvidenceLabel.SOURCE_SUPPORTED,
            facts,
            "The same gana: six gunas in every source read, whichever partner is which.",
        )
    return _not_evaluable(
        "gana",
        name,
        FactorReason.ROLE_REQUIRED_NOT_COLLECTED,
        True,
        EvidenceLabel.UNRESOLVED_CONFLICT,
        facts,
        "Mixed ganas are scored by role, and the readings disagree on those cells.",
    )


def bhakoot(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Bhakoot"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _not_evaluable("bhakoot", name, missing, False, EvidenceLabel.SOURCE_SUPPORTED)
    assert a.rashi is not None and b.rashi is not None
    ab, ba = sign_count(a.rashi, b.rashi), sign_count(b.rashi, a.rashi)
    kind = BHAKOOT_UNFAVOURABLE.get(frozenset({ab, ba}))
    return _evaluated(
        "bhakoot",
        name,
        0.0 if kind else 7.0,
        False,
        EvidenceLabel.SOURCE_SUPPORTED,
        {"sign_count_a_to_b": ab, "sign_count_b_to_a": ba, "unfavourable_kind": kind},
    )


def nadi(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Nadi Kuta"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _not_evaluable("nadi", name, missing, False, EvidenceLabel.SOURCE_SUPPORTED)
    assert a.nakshatra is not None and b.nakshatra is not None
    na, nb = NADI[a.nakshatra], NADI[b.nakshatra]
    return _evaluated(
        "nadi",
        name,
        0.0 if na is nb else 8.0,
        False,
        EvidenceLabel.SOURCE_SUPPORTED,
        {"nadi_a": na.value, "nadi_b": nb.value},
        "Matching Nadi Kuta; unrelated to the deferred Phase 9 Nadi Astrology.",
    )


KUTAS: Final[tuple[Callable[[MoonPlacement, MoonPlacement], FactorResult], ...]] = (
    varna,
    vashya,
    tara,
    yoni,
    graha_maitri,
    gana,
    bhakoot,
    nadi,
)

# --------------------------------------------------------------------------
# Doshas
# --------------------------------------------------------------------------


def _v37_conditions(a: MoonPlacement, b: MoonPlacement) -> dict[str, bool | None]:
    if None in (a.rashi, b.rashi, a.nakshatra, b.nakshatra):
        return {
            "same_sign_different_nakshatra": None,
            "same_nakshatra_different_sign": None,
            "same_nakshatra_different_pada": None,
        }
    same_sign = a.rashi is b.rashi
    same_nak = a.nakshatra is b.nakshatra
    different_pada = None if None in (a.pada, b.pada) else a.pada != b.pada
    return {
        "same_sign_different_nakshatra": same_sign and not same_nak,
        "same_nakshatra_different_sign": same_nak and not same_sign,
        "same_nakshatra_different_pada": (same_nak and different_pada)
        if different_pada is not None
        else (False if not same_nak else None),
    }


def _v37_state(conditions: dict[str, bool | None]) -> str:
    values = tuple(conditions.values())
    if any(value is True for value in values):
        return "source_exception_condition_met"
    if any(value is None for value in values):
        return "not_evaluable"
    return "no_source_exception_condition_met"


def doshas(
    a: MoonPlacement, b: MoonPlacement, by_id: dict[str, FactorResult]
) -> tuple[DoshaRecord, ...]:
    records = []
    v37 = _v37_conditions(a, b)

    nadi_factor = by_id["nadi"]
    if nadi_factor.status is FactorStatus.EVALUATED:
        present = nadi_factor.points == 0.0
        records.append(
            DoshaRecord(
                dosha_id="nadi_dosha",
                name="Nadi Dosha",
                state=DoshaState.PRESENT if present else DoshaState.ABSENT,
                facts=dict(nadi_factor.facts),
                exception_conditions=v37 if present else {},
                cancellation_state=_v37_state(v37) if present else "not_applicable",
                note="v. 34-35 (dosha); v. 37 (exception). No statement of effect is encoded.",
                provenance_ids=("prov.ak.nadi",),
            )
        )
    else:
        records.append(
            DoshaRecord(
                dosha_id="nadi_dosha",
                name="Nadi Dosha",
                state=DoshaState.NOT_EVALUABLE,
                reason=nadi_factor.reason,
                cancellation_state="not_evaluable",
                provenance_ids=("prov.ak.nadi",),
            )
        )

    bhakoot_factor = by_id["bhakoot"]
    if bhakoot_factor.status is FactorStatus.EVALUATED:
        present = bhakoot_factor.points == 0.0
        conditions: dict[str, bool | None] = {}
        if present:
            assert a.rashi is not None and b.rashi is not None
            la, lb = sign_lord(a.rashi), sign_lord(b.rashi)
            tara_factor = by_id["tara"]
            conditions = {
                "same_sign_lord": la is lb,
                "sign_lords_mutual_friends": relation(la, lb) == "friend"
                and relation(lb, la) == "friend",
                "nadi_different": None
                if nadi_factor.status is not FactorStatus.EVALUATED
                else nadi_factor.points == 8.0,
                "tara_favourable_both_ways": None
                if tara_factor.status is not FactorStatus.EVALUATED
                else tara_factor.points == 3.0,
                "navamsa_lords_friendly_and_strong": None,
                "sign_vashya_by_verse": _either_vashya(a.rashi, b.rashi),
            }
        records.append(
            DoshaRecord(
                dosha_id="bhakoot_dosha",
                name="Bhakoot Dosha",
                state=DoshaState.PRESENT if present else DoshaState.ABSENT,
                reason=FactorReason.CANCELLATION_SCHEME_DISPUTED if present else None,
                facts=dict(bhakoot_factor.facts),
                exception_conditions=conditions,
                cancellation_state="not_evaluated_scheme_disputed" if present else "not_applicable",
                note=(
                    "v. 31 (dosha); v. 32-33 name the cancellations (same lord, friendly lords, "
                    "strong friendly navamsa lords, tara purity, vashya), with nadi purity "
                    "required throughout; commentators dispute how they combine, so no "
                    "cancellation verdict is given. 'Strong' is undefined."
                ),
                provenance_ids=("prov.ak.bhakoot",),
            )
        )
    else:
        records.append(
            DoshaRecord(
                dosha_id="bhakoot_dosha",
                name="Bhakoot Dosha",
                state=DoshaState.NOT_EVALUABLE,
                reason=bhakoot_factor.reason,
                cancellation_state="not_evaluable",
                provenance_ids=("prov.ak.bhakoot",),
            )
        )

    gana_factor = by_id["gana"]
    if gana_factor.status is FactorStatus.EVALUATED:
        records.append(
            DoshaRecord(
                dosha_id="gana_dosha",
                name="Gana Dosha",
                state=DoshaState.ABSENT,
                facts=dict(gana_factor.facts),
                cancellation_state="not_applicable",
                provenance_ids=("prov.ak.gana",),
            )
        )
    else:
        records.append(
            DoshaRecord(
                dosha_id="gana_dosha",
                name="Gana Dosha",
                state=DoshaState.NOT_EVALUABLE,
                reason=gana_factor.reason,
                facts=dict(gana_factor.facts),
                exception_conditions=v37,
                cancellation_state=_v37_state(v37),
                note="Mixed ganas are judged by role; v. 37 names the exception conditions.",
                provenance_ids=("prov.ak.gana",),
            )
        )
    return tuple(records)


def _either_vashya(first: Rashi, second: Rashi) -> bool | None:
    one, two = vashya_relation(first, second), vashya_relation(second, first)
    if one is True or two is True:
        return True
    if one is None or two is None:
        return None
    return False


def evaluate_ashtakoot(
    a: MoonPlacement, b: MoonPlacement
) -> tuple[tuple[FactorResult, ...], tuple[DoshaRecord, ...], AshtakootTotal]:
    factors = tuple(kuta(a, b) for kuta in KUTAS)
    by_id = {factor.factor_id: factor for factor in factors}
    missing = tuple(f.factor_id for f in factors if f.status is not FactorStatus.EVALUATED)
    if missing:
        total = AshtakootTotal(
            status=FactorStatus.NOT_EVALUABLE,
            reason=FactorReason.FACTOR_NOT_EVALUABLE,
            missing_factors=missing,
        )
    else:
        total = AshtakootTotal(
            status=FactorStatus.EVALUATED,
            points=sum(f.points or 0.0 for f in factors),
        )
    return factors, doshas(a, b, by_id), total
