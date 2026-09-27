"""South Indian ten poruthams after Kalaprakasika Ch. XIII (N. P. Subramania
Iyer's translation, 1917; Phase 11, `docs/ASTROLOGY_STANDARDS.md` v1.25.0,
TP-01 to TP-14).

A separate system from the Ashtakoot, with its own tables (its Yoni list,
hostile pairs and planetary friendships differ from Muhurta Chintamani's)
and no points: each consideration is agreement, disagreement or (Yoni only)
neutral, as the source states it. No role is known, so the considerations
counted from the bride to the groom are not evaluable.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType
from typing import Final

from pandit_astro_engine.compatibility.ashtakoot import (
    Gana,
    Yoni,
    missing_inputs,
    nakshatra_count,
    sign_count,
)
from pandit_astro_engine.compatibility.constants import (
    Classification,
    DoshaState,
    FactorReason,
    FactorStatus,
)
from pandit_astro_engine.compatibility.models import (
    DoshaRecord,
    FactorResult,
    FactValue,
    MoonPlacement,
    PoruthamSummary,
)
from pandit_astro_engine.compatibility.profiles import EvidenceLabel
from pandit_astro_engine.lordship import sign_lord
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.rashi import Rashi

N = Nakshatra
R = Rashi
P = CelestialBody

# --------------------------------------------------------------------------
# Tables (Kalaprakasika Ch. XIII, printed pp. 72-76, page images)
# --------------------------------------------------------------------------

#: p. 72. The Manushya list prints five nakshatras only; the four missing
#: ones (Uttara Phalguni, Purva Ashadha, Uttara Ashadha, Purva Bhadrapada)
#: are deliberately absent.
GANAM: Final = MappingProxyType(
    {
        **{
            n: Gana.DEVA
            for n in (
                N.ASHWINI,
                N.MRIGASHIRA,
                N.PUNARVASU,
                N.PUSHYA,
                N.HASTA,
                N.SWATI,
                N.ANURADHA,
                N.SHRAVANA,
                N.REVATI,
            )
        },
        **{
            n: Gana.MANUSHYA
            for n in (N.BHARANI, N.ROHINI, N.ARDRA, N.PURVA_PHALGUNI, N.UTTARA_BHADRAPADA)
        },
        **{
            n: Gana.RAKSHASA
            for n in (
                N.KRITTIKA,
                N.ASHLESHA,
                N.MAGHA,
                N.CHITRA,
                N.VISHAKHA,
                N.JYESHTHA,
                N.MULA,
                N.DHANISHTA,
                N.SHATABHISHA,
            )
        },
    }
)

#: p. 73. Uttara Ashadha is a cow here (a mongoose in Muhurta Chintamani).
YONI: Final = MappingProxyType(
    {
        N.ASHWINI: Yoni.HORSE,
        N.SHATABHISHA: Yoni.HORSE,
        N.BHARANI: Yoni.ELEPHANT,
        N.REVATI: Yoni.ELEPHANT,
        N.PUSHYA: Yoni.SHEEP,
        N.KRITTIKA: Yoni.SHEEP,
        N.ROHINI: Yoni.SERPENT,
        N.MRIGASHIRA: Yoni.SERPENT,
        N.ASHLESHA: Yoni.CAT,
        N.PUNARVASU: Yoni.CAT,
        N.MAGHA: Yoni.RAT,
        N.PURVA_PHALGUNI: Yoni.RAT,
        N.UTTARA_PHALGUNI: Yoni.COW,
        N.UTTARA_ASHADHA: Yoni.COW,
        N.UTTARA_BHADRAPADA: Yoni.COW,
        N.SWATI: Yoni.BUFFALO,
        N.HASTA: Yoni.BUFFALO,
        N.VISHAKHA: Yoni.TIGER,
        N.CHITRA: Yoni.TIGER,
        N.JYESHTHA: Yoni.DEER,
        N.ANURADHA: Yoni.DEER,
        N.MULA: Yoni.DOG,
        N.ARDRA: Yoni.DOG,
        N.PURVA_ASHADHA: Yoni.MONKEY,
        N.SHRAVANA: Yoni.MONKEY,
        N.DHANISHTA: Yoni.LION,
        N.PURVA_BHADRAPADA: Yoni.LION,
    }
)

#: p. 73: "mutually hostile" pairs.
YONI_HOSTILE: Final = frozenset(
    frozenset(pair)
    for pair in (
        (Yoni.MONKEY, Yoni.SHEEP),
        (Yoni.DEER, Yoni.ELEPHANT),
        (Yoni.HORSE, Yoni.BUFFALO),
        (Yoni.COW, Yoni.TIGER),
        (Yoni.RAT, Yoni.CAT),
        (Yoni.SERPENT, Yoni.RAT),
        (Yoni.SERPENT, Yoni.MONGOOSE),
        (Yoni.DOG, Yoni.DEER),
    )
)

#: pp. 74-75 Rasyadhipathi friendship lists, as printed. `None` in
#: `COMPLETE` means the list is not stated to be exhaustive.
FRIENDS: Final = MappingProxyType(
    {
        P.MARS: frozenset({P.MERCURY, P.VENUS}),
        P.VENUS: frozenset({P.MARS, P.MERCURY, P.JUPITER, P.SATURN}),
        P.MERCURY: frozenset({P.MOON, P.MARS, P.JUPITER, P.VENUS, P.SATURN}),
        P.MOON: frozenset({P.MERCURY, P.JUPITER}),
        P.SUN: frozenset({P.JUPITER}),
        P.JUPITER: frozenset({P.SUN, P.MOON, P.MERCURY, P.VENUS, P.SATURN}),
        P.SATURN: frozenset[CelestialBody](),
    }
)
#: Saturn: only "Jupiter is his enemy" is printed; his friends are unknown.
FRIEND_LIST_EXHAUSTIVE: Final = MappingProxyType({body: body is not P.SATURN for body in FRIENDS})
SATURN_KNOWN_NON_FRIENDS: Final = frozenset({P.JUPITER})

#: p. 75 Vasyam: key is concordant ("vasya") to each value.
VASYAM: Final = MappingProxyType(
    {
        R.ARIES: frozenset({R.LEO, R.SCORPIO}),
        R.TAURUS: frozenset({R.CANCER, R.LEO}),
        R.GEMINI: frozenset({R.VIRGO}),
        R.CANCER: frozenset({R.SCORPIO, R.SAGITTARIUS}),
        R.LEO: frozenset({R.LIBRA}),
        R.VIRGO: frozenset({R.GEMINI, R.PISCES}),
        R.LIBRA: frozenset({R.CAPRICORN}),
        R.SCORPIO: frozenset({R.VIRGO, R.CANCER}),
        R.SAGITTARIUS: frozenset({R.PISCES}),
        R.CAPRICORN: frozenset({R.AQUARIUS, R.ARIES}),
        R.AQUARIUS: frozenset({R.ARIES}),
        R.PISCES: frozenset({R.CAPRICORN}),
    }
)

#: p. 75 Rajju divisions.
RAJJU: Final = MappingProxyType(
    {
        **{n: "padha" for n in (N.ASHWINI, N.ASHLESHA, N.MAGHA, N.JYESHTHA, N.MULA, N.REVATI)},
        **{
            n: "ooroo"
            for n in (
                N.BHARANI,
                N.PUSHYA,
                N.PURVA_PHALGUNI,
                N.ANURADHA,
                N.PURVA_ASHADHA,
                N.UTTARA_BHADRAPADA,
            )
        },
        **{
            n: "nabhi"
            for n in (
                N.KRITTIKA,
                N.PUNARVASU,
                N.UTTARA_PHALGUNI,
                N.VISHAKHA,
                N.UTTARA_ASHADHA,
                N.PURVA_BHADRAPADA,
            )
        },
        **{n: "kanta" for n in (N.ROHINI, N.ARDRA, N.HASTA, N.SWATI, N.SHRAVANA, N.SHATABHISHA)},
        **{n: "siro" for n in (N.MRIGASHIRA, N.CHITRA, N.DHANISHTA)},
    }
)

#: p. 76 Vedhai: mutually repellent sets.
VEDHAI_SETS: Final = tuple(
    frozenset(group)
    for group in (
        (N.ASHWINI, N.JYESHTHA),
        (N.BHARANI, N.ANURADHA),
        (N.KRITTIKA, N.VISHAKHA),
        (N.ROHINI, N.SWATI),
        (N.ARDRA, N.SHRAVANA),
        (N.PUNARVASU, N.UTTARA_ASHADHA),
        (N.PUSHYA, N.PURVA_ASHADHA),
        (N.ASHLESHA, N.MULA),
        (N.MAGHA, N.REVATI),
        (N.PURVA_PHALGUNI, N.UTTARA_BHADRAPADA),
        (N.UTTARA_PHALGUNI, N.PURVA_BHADRAPADA),
        (N.HASTA, N.SHATABHISHA),
        (N.MRIGASHIRA, N.CHITRA, N.DHANISHTA),
    )
)

PORUTHAM_ORDER: Final = (
    "dhinam",
    "ganam",
    "mahendhram",
    "sthree_dheergham",
    "yoni",
    "rasi",
    "rasyadhipathi",
    "vasyam",
    "rajju",
    "vedhai",
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def regards_as_friend(of: CelestialBody, towards: CelestialBody) -> bool | None:
    """Whether `of` counts `towards` a friend in Kalaprakasika's lists; None
    where the lists do not say."""
    if towards in FRIENDS[of]:
        return True
    if FRIEND_LIST_EXHAUSTIVE[of] or towards in SATURN_KNOWN_NON_FRIENDS:
        return False
    return None


def mutual_friends(first: CelestialBody, second: CelestialBody) -> bool | None:
    one, two = regards_as_friend(first, second), regards_as_friend(second, first)
    if one is False or two is False:
        return False
    if one is None or two is None:
        return None
    return True


def _result(
    factor_id: str,
    name: str,
    *,
    classification: Classification | None = None,
    reason: FactorReason | None = None,
    role_dependent: bool = False,
    label: EvidenceLabel = EvidenceLabel.SOURCE_SUPPORTED,
    facts: dict[str, FactValue] | None = None,
    note: str = "",
    provenance: str = "prov.tp.symmetric",
) -> FactorResult:
    return FactorResult(
        factor_id=factor_id,
        name=name,
        status=FactorStatus.EVALUATED if reason is None else FactorStatus.NOT_EVALUABLE,
        reason=reason,
        classification=classification,
        role_dependent=role_dependent,
        role_invariant=(
            None
            if not role_dependent
            else (False if reason is FactorReason.ROLE_REQUIRED_NOT_COLLECTED else True)
        ),
        label=label,
        facts=facts or {},
        note=note,
        provenance_ids=(provenance,),
    )


def _counts(a: MoonPlacement, b: MoonPlacement) -> dict[str, FactValue]:
    assert a.nakshatra is not None and b.nakshatra is not None
    return {
        "count_a_to_b": nakshatra_count(a.nakshatra, b.nakshatra),
        "count_b_to_a": nakshatra_count(b.nakshatra, a.nakshatra),
    }


# --------------------------------------------------------------------------
# The ten considerations
# --------------------------------------------------------------------------


def _role_counted(factor_id: str, name: str, note: str) -> Callable[..., FactorResult]:
    def evaluate(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
        missing = missing_inputs(a, b, ("nakshatra",))
        if missing:
            return _result(factor_id, name, reason=missing, role_dependent=True)
        return _result(
            factor_id,
            name,
            reason=FactorReason.ROLE_REQUIRED_NOT_COLLECTED,
            role_dependent=True,
            facts=_counts(a, b),
            note=note,
            provenance="prov.tp.role",
        )

    return evaluate


dhinam = _role_counted(
    "dhinam",
    "Dhinam",
    "Counted from the bride's nakshatra to the groom's (p. 69); the counts both ways are given.",
)
mahendhram = _role_counted(
    "mahendhram",
    "Mahendhram",
    "The groom's nakshatra should be the 4th, 7th, ... 25th from the bride's (p. 72).",
)
sthree_dheergham = _role_counted(
    "sthree_dheergham",
    "Sthree-Dheergham",
    "The groom's nakshatra beyond the 13th from the bride's; 'some writers' say beyond the "
    "7th (p. 72): a role and a reading question.",
)


def ganam(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Ganam"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _result("ganam", name, reason=missing, role_dependent=True)
    assert a.nakshatra is not None and b.nakshatra is not None
    ga, gb = GANAM.get(a.nakshatra), GANAM.get(b.nakshatra)
    facts: dict[str, FactValue] = {
        "ganam_a": None if ga is None else ga.value,
        "ganam_b": None if gb is None else gb.value,
    }
    if ga is None or gb is None:
        return _result(
            "ganam",
            name,
            reason=FactorReason.SOURCE_TABLE_INCOMPLETE,
            role_dependent=True,
            facts=facts,
            note="This nakshatra is in none of the printed gana lists.",
            provenance="prov.tp.ganam",
        )
    if ga is gb:
        return _result(
            "ganam",
            name,
            classification=Classification.AGREEMENT,
            role_dependent=True,
            facts=facts,
            note="The same ganam 'signifies suitability' whichever partner is which.",
            provenance="prov.tp.ganam",
        )
    return _result(
        "ganam",
        name,
        reason=FactorReason.ROLE_REQUIRED_NOT_COLLECTED,
        role_dependent=True,
        facts=facts,
        note="Mixed ganams are judged by the groom's and the bride's ganam in turn.",
        provenance="prov.tp.role",
    )


def yoni(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Yoni"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _result("yoni", name, reason=missing)
    assert a.nakshatra is not None and b.nakshatra is not None
    ya, yb = YONI[a.nakshatra], YONI[b.nakshatra]
    facts: dict[str, FactValue] = {"yoni_a": ya.value, "yoni_b": yb.value}
    if ya is yb:
        classification = Classification.AGREEMENT
    elif frozenset({ya, yb}) in YONI_HOSTILE:
        classification = Classification.DISAGREEMENT
    else:
        classification = Classification.NEUTRAL
    return _result("yoni", name, classification=classification, facts=facts)


def rasi(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Rasi"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _result("rasi", name, reason=missing, role_dependent=True)
    assert a.rashi is not None and b.rashi is not None
    ab, ba = sign_count(a.rashi, b.rashi), sign_count(b.rashi, a.rashi)
    facts: dict[str, FactValue] = {"sign_count_a_to_b": ab, "sign_count_b_to_a": ba}
    if ab == 7:
        return _result(
            "rasi",
            name,
            classification=Classification.AGREEMENT,
            role_dependent=True,
            facts=facts,
            note="Diametrically opposite Moon signs (p. 74).",
        )
    if ab == 1:
        return _result(
            "rasi",
            name,
            reason=FactorReason.NOT_SPECIFIED_BY_SOURCE,
            role_dependent=True,
            facts=facts,
            note="The Rasi consideration does not state a rule for the same Moon sign.",
        )
    return _result(
        "rasi",
        name,
        reason=FactorReason.ROLE_REQUIRED_NOT_COLLECTED,
        role_dependent=True,
        facts=facts,
        note="Each rule names the groom's sign counted from the bride's (pp. 73-74).",
        provenance="prov.tp.role",
    )


def rasyadhipathi(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Rasyadhipathi"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _result("rasyadhipathi", name, reason=missing, label=EvidenceLabel.INFERENCE)
    assert a.rashi is not None and b.rashi is not None
    la, lb = sign_lord(a.rashi), sign_lord(b.rashi)
    facts: dict[str, FactValue] = {
        "lord_a": la.value,
        "lord_b": lb.value,
        "a_lord_counts_b_lord_friend": None if la is lb else regards_as_friend(la, lb),
        "b_lord_counts_a_lord_friend": None if la is lb else regards_as_friend(lb, la),
    }
    if la is lb:
        return _result(
            "rasyadhipathi",
            name,
            reason=FactorReason.NOT_SPECIFIED_BY_SOURCE,
            label=EvidenceLabel.INFERENCE,
            facts=facts,
            note=(
                "The same lord is named in the exception clause, not as this consideration's rule."
            ),
            provenance="prov.tp.rasyadhipathi",
        )
    friends = mutual_friends(la, lb)
    if friends is None:
        return _result(
            "rasyadhipathi",
            name,
            reason=FactorReason.RELATION_NOT_SPECIFIED_BY_SOURCE,
            label=EvidenceLabel.INFERENCE,
            facts=facts,
            note="Saturn's friends are not listed.",
            provenance="prov.tp.rasyadhipathi",
        )
    return _result(
        "rasyadhipathi",
        name,
        classification=Classification.AGREEMENT if friends else Classification.DISAGREEMENT,
        label=EvidenceLabel.INFERENCE,
        facts=facts,
        provenance="prov.tp.rasyadhipathi",
    )


def vasyam(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Vasyam"
    missing = missing_inputs(a, b, ("rashi",))
    if missing:
        return _result("vasyam", name, reason=missing)
    assert a.rashi is not None and b.rashi is not None
    b_to_a = b.rashi in VASYAM[a.rashi]
    a_to_b = a.rashi in VASYAM[b.rashi]
    return _result(
        "vasyam",
        name,
        classification=Classification.AGREEMENT
        if (a_to_b or b_to_a)
        else Classification.DISAGREEMENT,
        facts={"a_concordant_to_b": a_to_b, "b_concordant_to_a": b_to_a},
        note="'Concordant to that of the bride, or vice versa' (p. 75): either direction.",
    )


def rajju(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Rajju"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _result("rajju", name, reason=missing)
    assert a.nakshatra is not None and b.nakshatra is not None
    ra, rb = RAJJU[a.nakshatra], RAJJU[b.nakshatra]
    return _result(
        "rajju",
        name,
        classification=Classification.DISAGREEMENT if ra == rb else Classification.AGREEMENT,
        facts={"rajju_a": ra, "rajju_b": rb},
    )


def vedhai(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
    name = "Vedhai"
    missing = missing_inputs(a, b, ("nakshatra",))
    if missing:
        return _result("vedhai", name, reason=missing)
    assert a.nakshatra is not None and b.nakshatra is not None
    repellent = a.nakshatra is not b.nakshatra and any(
        {a.nakshatra, b.nakshatra} <= group for group in VEDHAI_SETS
    )
    return _result(
        "vedhai",
        name,
        classification=Classification.DISAGREEMENT if repellent else Classification.AGREEMENT,
        facts={"repellent_pair": repellent},
    )


PORUTHAMS: Final[tuple[Callable[[MoonPlacement, MoonPlacement], FactorResult], ...]] = (
    dhinam,
    ganam,
    mahendhram,
    sthree_dheergham,
    yoni,
    rasi,
    rasyadhipathi,
    vasyam,
    rajju,
    vedhai,
)


def _exception(a: MoonPlacement, b: MoonPlacement) -> dict[str, bool | None]:
    if a.rashi is None or b.rashi is None:
        return {"same_sign_lord": None, "sign_lords_friendly": None, "opposite_signs": None}
    la, lb = sign_lord(a.rashi), sign_lord(b.rashi)
    return {
        "same_sign_lord": la is lb,
        "sign_lords_friendly": None if la is lb else mutual_friends(la, lb),
        "opposite_signs": sign_count(a.rashi, b.rashi) == 7,
    }


def evaluate_ten_porutham(
    a: MoonPlacement, b: MoonPlacement
) -> tuple[tuple[FactorResult, ...], tuple[DoshaRecord, ...], PoruthamSummary]:
    factors = tuple(porutham(a, b) for porutham in PORUTHAMS)
    by_id = {f.factor_id: f for f in factors}
    exception = _exception(a, b)
    exception_met = any(value is True for value in exception.values())
    records = []
    for factor_id, name in (("rajju", "Rajju Dosha"), ("vedhai", "Vedhai Dosha")):
        factor = by_id[factor_id]
        if factor.status is not FactorStatus.EVALUATED:
            records.append(
                DoshaRecord(
                    dosha_id=f"{factor_id}_dosha",
                    name=name,
                    state=DoshaState.NOT_EVALUABLE,
                    reason=factor.reason,
                    cancellation_state="not_evaluable",
                    provenance_ids=("prov.tp.exception",),
                )
            )
            continue
        present = factor.classification is Classification.DISAGREEMENT
        records.append(
            DoshaRecord(
                dosha_id=f"{factor_id}_dosha",
                name=name,
                state=DoshaState.PRESENT if present else DoshaState.ABSENT,
                facts=dict(factor.facts),
                exception_conditions=exception if present else {},
                cancellation_state=(
                    (
                        "source_exception_condition_met"
                        if exception_met
                        else (
                            "not_evaluable"
                            if any(v is None for v in exception.values())
                            else "no_source_exception_condition_met"
                        )
                    )
                    if present
                    else "not_applicable"
                ),
                note=(
                    "p. 76 exception: adverse effects 'need not be considered'. No effect "
                    "statement is encoded."
                ),
                provenance_ids=("prov.tp.exception",),
            )
        )

    def count(classification: Classification) -> int:
        return sum(1 for f in factors if f.classification is classification)

    summary = PoruthamSummary(
        agreements=count(Classification.AGREEMENT),
        disagreements=count(Classification.DISAGREEMENT),
        neutral=count(Classification.NEUTRAL),
        not_evaluable=sum(1 for f in factors if f.status is not FactorStatus.EVALUATED),
    )
    return factors, tuple(records), summary
