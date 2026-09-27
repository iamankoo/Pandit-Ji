"""Phase 11 matching, pure functions (`docs/ASTROLOGY_STANDARDS.md` v1.25.0,
AK-01 to AK-16, TP-01 to TP-14): every kuta and porutham, source tables and
worked examples, role handling, uncertainty, doshas, the 36-point rule and
the separation of the two systems (and of Tara Kuta from Tara Bala)."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import pytest

from pandit_astro_engine.compatibility import ashtakoot as ak
from pandit_astro_engine.compatibility import porutham as tp
from pandit_astro_engine.compatibility.constants import (
    Classification,
    DoshaState,
    FactorReason,
    FactorStatus,
    Participant,
)
from pandit_astro_engine.compatibility.models import FactorResult, MoonPlacement
from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_ORDER, Nakshatra, nakshatra_position
from pandit_astro_engine.rashi import RASHI_ORDER, Rashi, rashi_from_longitude
from pandit_astro_engine.shadbala.constants import NATURAL_ENEMIES, NATURAL_FRIENDS

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "phase11_source_tables.json").read_text("utf-8")
)
TABLES = FIXTURE["mahidhara_tables"]
N = Nakshatra
R = Rashi
B = CelestialBody


def at(longitude: float, who: Participant = Participant.A) -> MoonPlacement:
    position = nakshatra_position(longitude)
    return MoonPlacement(
        participant=who,
        birth_time_status=BirthTimeStatus.EXACT,
        nakshatra=position.nakshatra,
        pada=position.pada,
        rashi=rashi_from_longitude(longitude),
        moon_longitude=longitude,
    )


def star(nakshatra: Nakshatra, pada: int = 1, who: Participant = Participant.A) -> MoonPlacement:
    index = NAKSHATRA_ORDER.index(nakshatra)
    return at(index * 360 / 27 + (pada - 1) * 360 / 108 + 0.5, who)


def sign(rashi: Rashi, who: Participant = Participant.A, offset: float = 5.0) -> MoonPlacement:
    return at(RASHI_ORDER.index(rashi) * 30 + offset, who)


def uncertain(who: Participant = Participant.B) -> MoonPlacement:
    return MoonPlacement(
        participant=who,
        birth_time_status=BirthTimeStatus.APPROXIMATE,
        nakshatra=None,
        pada=None,
        rashi=None,
    )


ALL_STARS = [star(n) for n in NAKSHATRA_ORDER]
ALL_SIGNS = [sign(r) for r in RASHI_ORDER]

# --------------------------------------------------------------------------
# Ashtakoot tables against independent transcriptions of the verses
# --------------------------------------------------------------------------


def test_varna_verse_22() -> None:
    expected = {
        "brahmin": {R.CANCER, R.SCORPIO, R.PISCES},
        "kshatriya": {R.ARIES, R.LEO, R.SAGITTARIUS},
        "vaishya": {R.TAURUS, R.VIRGO, R.CAPRICORN},
        "shudra": {R.GEMINI, R.LIBRA, R.AQUARIUS},
    }
    for varna, signs in expected.items():
        assert {s for s, v in ak.VARNA.items() if v.value == varna} == signs


def test_gana_verse_29_and_nadi_verse_34_partition_the_27_nakshatras() -> None:
    assert len(ak.GANA) == 27 and len(ak.NADI) == 27
    for mapping in (ak.GANA, ak.NADI):
        counts: dict[object, int] = {}
        for value in mapping.values():
            counts[value] = counts.get(value, 0) + 1
        assert sorted(counts.values()) == [9, 9, 9]
    assert {n for n, g in ak.GANA.items() if g is ak.Gana.RAKSHASA} == {
        N.MAGHA, N.ASHLESHA, N.DHANISHTA, N.JYESHTHA, N.MULA, N.SHATABHISHA,
        N.KRITTIKA, N.CHITRA, N.VISHAKHA,
    }  # fmt: skip
    assert {n for n, v in ak.NADI.items() if v is ak.Nadi.ADYA} == {
        N.ASHWINI, N.ARDRA, N.PUNARVASU, N.UTTARA_PHALGUNI, N.HASTA, N.JYESHTHA,
        N.MULA, N.SHATABHISHA, N.PURVA_BHADRAPADA,
    }  # fmt: skip


def test_yoni_verses_25_26() -> None:
    assert len(ak.YONI) == 27
    assert ak.YONI[N.UTTARA_ASHADHA] is ak.Yoni.MONGOOSE
    pairs = {frozenset({ak.YONI[a], ak.YONI[b]}) for a, b in ((N.ASHWINI, N.HASTA),)}
    assert pairs <= ak.YONI_GREAT_ENMITY
    covered = set().union(*ak.YONI_GREAT_ENMITY)
    assert covered == set(ak.Yoni)  # the seven enmities cover all fourteen yonis


def test_graha_maitri_reuses_the_locked_phase6_table() -> None:
    # Muhurta Chintamani v. 27-28, transcribed independently of the code.
    verse = {
        B.SUN: ({B.MARS, B.JUPITER, B.MOON}, {B.VENUS, B.SATURN}),
        B.MOON: ({B.MERCURY, B.SUN}, set()),
        B.MARS: ({B.MOON, B.JUPITER, B.SUN}, {B.MERCURY}),
        B.MERCURY: ({B.VENUS, B.SUN}, {B.MOON}),
        B.JUPITER: ({B.SUN, B.MARS, B.MOON}, {B.MERCURY, B.VENUS}),
        B.VENUS: ({B.MERCURY, B.SATURN}, {B.MOON, B.SUN}),
        B.SATURN: ({B.VENUS, B.MERCURY}, {B.SUN, B.MOON, B.MARS}),
    }
    for body, (friends, enemies) in verse.items():
        assert NATURAL_FRIENDS[body] == friends
        assert NATURAL_ENEMIES[body] == enemies
    assert ak.NATURAL_FRIENDS is NATURAL_FRIENDS  # reused, not redefined


def test_graha_maitri_points_against_the_printed_table() -> None:
    order = [B(name) for name in TABLES["graha_maitri"]["order"]]
    slips = {
        frozenset({B(a), B(b)}) for a, b, _ in TABLES["graha_maitri"]["cells_against_the_rule"]
    }
    lord_sign = {B.SUN: R.LEO, B.MOON: R.CANCER, B.MARS: R.ARIES, B.MERCURY: R.GEMINI,
                 B.JUPITER: R.SAGITTARIUS, B.VENUS: R.TAURUS, B.SATURN: R.CAPRICORN}  # fmt: skip
    checked = 0
    for i, j in product(range(7), repeat=2):
        first, second = order[i], order[j]
        result = ak.graha_maitri(sign(lord_sign[first]), sign(lord_sign[second], Participant.B))
        printed = TABLES["graha_maitri"]["table"][i][j]
        if frozenset({first, second}) in slips:
            continue
        assert result.points == printed, (first, second)
        checked += 1
    assert checked == 45  # 49 cells less the four cells of the two recorded slips
    sun_mercury = ak.graha_maitri(sign(R.LEO), sign(R.GEMINI, Participant.B))
    assert sun_mercury.points == 4.0
    venus_sun = ak.graha_maitri(sign(R.TAURUS), sign(R.LEO, Participant.B))
    assert venus_sun.points == 0.0


def test_tara_matches_the_printed_table_and_is_symmetric() -> None:
    table = TABLES["tara"]["table"]
    for a, b in product(ALL_STARS, ALL_STARS):
        result = ak.tara(a, b)
        rab, rba = result.facts["remainder_a_to_b"], result.facts["remainder_b_to_a"]
        assert result.points == table[rab - 1][rba - 1]  # type: ignore[index,operator]
        assert result.points == ak.tara(b, a).points
        assert not result.role_dependent
        assert result.points in (3.0, 1.5)  # remainders sum to 2 mod 9: never both bad


def test_bhakoot_matches_the_printed_aries_row_and_verse_31() -> None:
    row = TABLES["bhakoot_aries_row"]
    for name, points in zip(row["order"], row["points"], strict=True):
        assert ak.bhakoot(sign(R.ARIES), sign(R(name), Participant.B)).points == points
    for a, b in product(ALL_SIGNS, ALL_SIGNS):
        assert ak.bhakoot(a, b).points == ak.bhakoot(b, a).points


@pytest.mark.parametrize("example", FIXTURE["mc_verse_examples"]["bhakoot"])
def test_bhakoot_verse_examples(example: dict[str, object]) -> None:
    a, b = sign(R(str(example["a"]))), sign(R(str(example["b"])), Participant.B)
    factor = ak.bhakoot(a, b)
    assert factor.facts["unfavourable_kind"] == example["kind"]
    factors = {f.factor_id: f for f in (kuta(a, b) for kuta in ak.KUTAS)}
    dosha = next(d for d in ak.doshas(a, b, factors) if d.dosha_id == "bhakoot_dosha")
    assert dosha.state is DoshaState.PRESENT
    assert dosha.cancellation_state == "not_evaluated_scheme_disputed"
    for key in ("same_sign_lord", "sign_lords_mutual_friends"):
        if key in example:
            assert dosha.exception_conditions[key] is example[key]


def test_nadi_and_its_dosha_with_the_verse_37_exception() -> None:
    same = ak.nadi(star(N.ASHWINI), star(N.ARDRA, who=Participant.B))
    assert same.points == 0.0
    assert ak.nadi(star(N.ASHWINI), star(N.BHARANI, who=Participant.B)).points == 8.0
    a, b = star(N.ARDRA, 2), star(N.PUNARVASU, 1, Participant.B)  # both Gemini, both adya
    factors = {f.factor_id: f for f in (kuta(a, b) for kuta in ak.KUTAS)}
    dosha = ak.doshas(a, b, factors)[0]
    assert dosha.state is DoshaState.PRESENT
    assert dosha.exception_conditions["same_sign_different_nakshatra"] is True
    assert dosha.cancellation_state == "source_exception_condition_met"
    a, b = star(N.ASHWINI, 1), star(N.ASHWINI, 2, Participant.B)
    factors = {f.factor_id: f for f in (kuta(a, b) for kuta in ak.KUTAS)}
    dosha = ak.doshas(a, b, factors)[0]
    assert dosha.exception_conditions["same_nakshatra_different_pada"] is True
    a, b = star(N.ASHWINI, 1), star(N.MULA, 1, Participant.B)  # adya, different signs
    factors = {f.factor_id: f for f in (kuta(a, b) for kuta in ak.KUTAS)}
    dosha = ak.doshas(a, b, factors)[0]
    assert dosha.cancellation_state == "no_source_exception_condition_met"


def test_yoni_points() -> None:
    assert ak.yoni(star(N.ASHWINI), star(N.SHATABHISHA, who=Participant.B)).points == 4.0
    enmity = ak.yoni(star(N.ASHWINI), star(N.SWATI, who=Participant.B))
    assert enmity.points == 0.0 and enmity.facts["great_enmity"]
    tiger_cow = ak.yoni(star(N.CHITRA), star(N.UTTARA_PHALGUNI, who=Participant.B))
    assert tiger_cow.points == 0.0  # the verse governs; the printed tiger row says 1
    asym = ak.yoni(star(N.BHARANI), star(N.HASTA, who=Participant.B))  # elephant, buffalo
    assert asym.status is FactorStatus.NOT_EVALUABLE
    assert asym.reason is FactorReason.SOURCE_TABLE_ASYMMETRIC
    sym = ak.yoni(star(N.ASHWINI), star(N.BHARANI, who=Participant.B))  # horse, elephant
    assert sym.points == 2.0


def test_yoni_table_diagonal_and_verse_zeros() -> None:
    for i in range(14):
        assert ak.YONI_TABLE[i][i] == 4
    for pair in ak.YONI_GREAT_ENMITY:
        first, second = sorted(pair, key=ak.YONI_TABLE_ORDER.index)
        cells = ak.yoni_table_points(first, second)
        assert 0 in cells


def test_varna_and_gana_role_handling() -> None:
    same = ak.varna(sign(R.CANCER), sign(R.PISCES, Participant.B))
    assert same.points == 1.0 and same.role_dependent and same.role_invariant
    different = ak.varna(sign(R.CANCER), sign(R.ARIES, Participant.B))
    assert different.reason is FactorReason.ROLE_REQUIRED_NOT_COLLECTED
    assert different.role_invariant is False and different.points is None
    same_gana = ak.gana(star(N.ASHWINI), star(N.HASTA, who=Participant.B))
    assert same_gana.points == 6.0
    mixed = ak.gana(star(N.ASHWINI), star(N.MAGHA, who=Participant.B))
    assert mixed.reason is FactorReason.ROLE_REQUIRED_NOT_COLLECTED


def test_vashya_is_never_scored() -> None:
    for a, b in product(ALL_SIGNS, ALL_SIGNS):
        result = ak.vashya(a, b)
        assert result.status is FactorStatus.NOT_EVALUABLE and result.points is None
    facts = ak.vashya(sign(R.GEMINI), sign(R.CANCER, Participant.B)).facts
    assert facts["b_vashya_to_a_by_verse"] is True
    assert facts["b_water_sign_food_of_human_sign_a"] is True
    assert (
        ak.vashya(sign(R.LEO), sign(R.SCORPIO, Participant.B)).facts["b_vashya_to_a_by_verse"]
        is False
    )
    assert (
        ak.vashya(sign(R.ARIES), sign(R.TAURUS, Participant.B)).facts["b_vashya_to_a_by_verse"]
        is None
    )


def test_no_36_point_total_from_a_partial_set() -> None:
    for a, b in product(ALL_STARS[::3], ALL_STARS[1::3]):
        factors, _, total = ak.evaluate_ashtakoot(a, b)
        assert total.status is FactorStatus.NOT_EVALUABLE and total.points is None
        assert "vashya" in total.missing_factors


def test_total_is_the_sum_when_every_kuta_is_evaluated(monkeypatch: pytest.MonkeyPatch) -> None:
    def scored_vashya(a: MoonPlacement, b: MoonPlacement) -> FactorResult:
        return FactorResult(
            factor_id="vashya",
            name="Vashya",
            status=FactorStatus.EVALUATED,
            points=2.0,
            max_points=2.0,
            role_dependent=False,
            label=ak.EvidenceLabel.INFERENCE,
        )

    monkeypatch.setattr(ak, "KUTAS", (ak.varna, scored_vashya) + ak.KUTAS[2:])
    a, b = star(N.ASHWINI, 1), star(N.ASHWINI, 1, Participant.B)
    factors, _, total = ak.evaluate_ashtakoot(a, b)
    assert total.status is FactorStatus.EVALUATED
    assert total.points == sum(f.points or 0 for f in factors) == 1 + 2 + 3 + 4 + 5 + 6 + 7 + 0


def test_uncertain_moon_makes_factors_not_evaluable() -> None:
    factors, doshas, total = ak.evaluate_ashtakoot(star(N.ASHWINI), uncertain())
    assert {f.reason for f in factors} == {FactorReason.MOON_POSITION_UNCERTAIN}
    assert all(d.state is DoshaState.NOT_EVALUABLE for d in doshas)
    no_time = uncertain().model_copy(update={"birth_time_status": BirthTimeStatus.NOT_EVALUABLE})
    assert ak.tara(star(N.ASHWINI), no_time).reason is FactorReason.BIRTH_TIME_NOT_EVALUABLE


def test_ashtakoot_weights_are_one_to_eight() -> None:
    assert list(ak.MAX_POINTS.values()) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert sum(ak.MAX_POINTS.values()) == 36


# --------------------------------------------------------------------------
# Ten poruthams
# --------------------------------------------------------------------------


@pytest.mark.parametrize("example", FIXTURE["kalaprakasika_examples"]["counts"])
def test_kalaprakasika_count_examples(example: dict[str, object]) -> None:
    assert ak.nakshatra_count(N(str(example["from"])), N(str(example["to"]))) == example["count"]


def test_porutham_tables_against_the_printed_pages() -> None:
    assert len(tp.YONI) == 27 and len(tp.RAJJU) == 27
    assert sorted(len(g) for g in tp.VEDHAI_SETS) == [2] * 12 + [3]
    assert set().union(*tp.VEDHAI_SETS) == set(NAKSHATRA_ORDER)
    missing = set(NAKSHATRA_ORDER) - set(tp.GANAM)
    assert missing == {
        N.UTTARA_PHALGUNI, N.PURVA_ASHADHA, N.UTTARA_ASHADHA, N.PURVA_BHADRAPADA,
    }  # fmt: skip
    assert tp.VASYAM[R.ARIES] == {R.LEO, R.SCORPIO}
    assert tp.VASYAM[R.PISCES] == {R.CAPRICORN}


def test_the_two_systems_keep_their_own_tables() -> None:
    assert ak.YONI[N.UTTARA_ASHADHA] is ak.Yoni.MONGOOSE
    assert tp.YONI[N.UTTARA_ASHADHA] is ak.Yoni.COW
    assert frozenset({ak.Yoni.DEER, ak.Yoni.ELEPHANT}) in tp.YONI_HOSTILE
    assert frozenset({ak.Yoni.DEER, ak.Yoni.ELEPHANT}) not in ak.YONI_GREAT_ENMITY
    # Kalaprakasika's Mars regards Venus as a friend; the BPHS/MC table does not.
    assert tp.regards_as_friend(B.MARS, B.VENUS) is True
    assert ak.relation(B.MARS, B.VENUS) == "neutral"


def test_role_counted_poruthams_are_not_evaluable_with_counts() -> None:
    a, b = star(N.ARDRA), star(N.UTTARA_PHALGUNI, who=Participant.B)
    for fn in (tp.dhinam, tp.mahendhram, tp.sthree_dheergham):
        result = fn(a, b)
        assert result.reason is FactorReason.ROLE_REQUIRED_NOT_COLLECTED
        assert result.facts == {"count_a_to_b": 7, "count_b_to_a": 22}  # 7 + 22 = 29


def test_ganam_porutham() -> None:
    assert tp.ganam(star(N.ASHWINI), star(N.HASTA, who=Participant.B)).classification is (
        Classification.AGREEMENT
    )
    missing = tp.ganam(star(N.ASHWINI), star(N.UTTARA_ASHADHA, who=Participant.B))
    assert missing.reason is FactorReason.SOURCE_TABLE_INCOMPLETE
    mixed = tp.ganam(star(N.ASHWINI), star(N.BHARANI, who=Participant.B))
    assert mixed.reason is FactorReason.ROLE_REQUIRED_NOT_COLLECTED


def test_yoni_porutham() -> None:
    assert tp.yoni(star(N.ASHWINI), star(N.SHATABHISHA, who=Participant.B)).classification is (
        Classification.AGREEMENT
    )
    assert tp.yoni(star(N.JYESHTHA), star(N.BHARANI, who=Participant.B)).classification is (
        Classification.DISAGREEMENT
    )
    assert tp.yoni(star(N.ASHWINI), star(N.BHARANI, who=Participant.B)).classification is (
        Classification.NEUTRAL
    )


def test_rasi_porutham() -> None:
    assert tp.rasi(sign(R.ARIES), sign(R.LIBRA, Participant.B)).classification is (
        Classification.AGREEMENT
    )
    assert tp.rasi(sign(R.ARIES), sign(R.ARIES, Participant.B)).reason is (
        FactorReason.NOT_SPECIFIED_BY_SOURCE
    )
    assert tp.rasi(sign(R.ARIES), sign(R.TAURUS, Participant.B)).reason is (
        FactorReason.ROLE_REQUIRED_NOT_COLLECTED
    )


def test_rasyadhipathi_porutham() -> None:
    mars_venus = tp.rasyadhipathi(sign(R.ARIES), sign(R.TAURUS, Participant.B))
    assert mars_venus.classification is Classification.AGREEMENT
    sun_venus = tp.rasyadhipathi(sign(R.LEO), sign(R.TAURUS, Participant.B))
    assert sun_venus.classification is Classification.DISAGREEMENT
    jupiter_saturn = tp.rasyadhipathi(sign(R.PISCES), sign(R.CAPRICORN, Participant.B))
    assert jupiter_saturn.classification is Classification.DISAGREEMENT
    venus_saturn = tp.rasyadhipathi(sign(R.TAURUS), sign(R.CAPRICORN, Participant.B))
    assert venus_saturn.reason is FactorReason.RELATION_NOT_SPECIFIED_BY_SOURCE
    same = tp.rasyadhipathi(sign(R.ARIES), sign(R.SCORPIO, Participant.B))
    assert same.reason is FactorReason.NOT_SPECIFIED_BY_SOURCE


def test_vasyam_rajju_vedhai() -> None:
    assert tp.vasyam(sign(R.LEO), sign(R.ARIES, Participant.B)).classification is (
        Classification.AGREEMENT
    )
    assert tp.vasyam(sign(R.ARIES), sign(R.TAURUS, Participant.B)).classification is (
        Classification.DISAGREEMENT
    )
    assert tp.rajju(star(N.ASHWINI), star(N.MAGHA, who=Participant.B)).classification is (
        Classification.DISAGREEMENT
    )
    assert tp.rajju(star(N.ASHWINI), star(N.BHARANI, who=Participant.B)).classification is (
        Classification.AGREEMENT
    )
    assert tp.vedhai(star(N.MRIGASHIRA), star(N.DHANISHTA, who=Participant.B)).classification is (
        Classification.DISAGREEMENT
    )
    assert tp.vedhai(star(N.ASHWINI), star(N.ASHWINI, who=Participant.B)).classification is (
        Classification.AGREEMENT
    )


def test_symmetric_poruthams_do_not_depend_on_order() -> None:
    for a, b in product(ALL_STARS[::2], ALL_STARS[1::2]):
        for fn in (tp.yoni, tp.vasyam, tp.rajju, tp.vedhai, tp.rasyadhipathi):
            assert fn(a, b).classification == fn(b, a).classification


def test_porutham_summary_and_doshas() -> None:
    a, b = star(N.ASHWINI), star(N.MAGHA, who=Participant.B)  # same Padha rajju
    factors, doshas, summary = tp.evaluate_ten_porutham(a, b)
    assert [f.factor_id for f in factors] == list(tp.PORUTHAM_ORDER)
    assert summary.not_evaluable == sum(f.status is not FactorStatus.EVALUATED for f in factors)
    assert all(f.points is None for f in factors)
    rajju = next(d for d in doshas if d.dosha_id == "rajju_dosha")
    assert rajju.state is DoshaState.PRESENT
    assert set(rajju.exception_conditions) == {
        "same_sign_lord",
        "sign_lords_friendly",
        "opposite_signs",
    }


def test_ashtakoot_results_carry_no_porutham_outcome() -> None:
    factors, _, _ = ak.evaluate_ashtakoot(star(N.ASHWINI), star(N.MAGHA, who=Participant.B))
    assert all(f.classification is None for f in factors)
    assert [f.factor_id for f in factors] == list(ak.KUTA_ORDER)


def test_tara_kuta_is_not_the_phase10_tara_bala() -> None:
    """The matching modules import nothing from the Phase 10 Muhurta or Panchang
    packages, so the Muhurta Tara Bala cannot be reused as Tara Kuta."""
    import ast

    package = Path(ak.__file__).parent
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "muhurta" not in node.module and "panchang" not in node.module, path
    assert "Tara Bala" in ak.tara(star(N.ASHWINI), star(N.BHARANI, who=Participant.B)).note
