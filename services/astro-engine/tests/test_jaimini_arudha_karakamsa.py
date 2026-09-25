"""Phase 9 WP-G (standards v1.17.0, JN-11 to JN-18): planet-level Rashi
Drishti (BPHS Ch. 8 v. 4-5), Arudha Pada (Ch. 29 v. 1-7) and Karakamsa
(Ch. 33 v. 1-2).

Reference data are transcribed from the Santhanam translation's own printed
examples, page-image checked (Vol I pp. 107, 294, 295, 296), never from the
implementation: the Ch. 8 example chart and its deductions (a)-(f); the
"standard nativity" longitudes (p. 294), its printed Navamsa chart (p. 294)
and its printed Arudha chart (p. 295).
"""

from __future__ import annotations

import pytest

from pandit_astro_engine.aspects import aspected_houses
from pandit_astro_engine.jaimini.arudha import (
    PADA_NAMES,
    PadaReason,
    PadaRule,
    PadaStatus,
    bhava_padas,
    graha_padas,
)
from pandit_astro_engine.jaimini.chara_karaka import (
    CharaKarakaRequest,
    calculate_chara_karaka,
)
from pandit_astro_engine.jaimini.karakamsa import (
    KarakamsaReason,
    KarakamsaStatus,
    karakamsa,
)
from pandit_astro_engine.jaimini.planet_rashi_drishti import planet_rashi_drishti
from pandit_astro_engine.jaimini.profiles import (
    CHARA_KARAKA_EIGHT_BODY_ID,
    CHARA_KARAKA_SEVEN_BODY_ID,
    KARAKAMSA_PROFILE_ID,
    PLANET_RASHI_DRISHTI_PROFILE_ID,
)
from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.rashi import Rashi as R
from pandit_astro_engine.rashi import rashi_from_longitude
from pandit_astro_engine.vargas import calculate_varga_sign


def _dms(d: int, m: int, s: int) -> float:
    return d + m / 60 + s / 3600


# --------------------------------------------------------------------------
# Ch. 8 v. 4-5 (p. 107): example chart and deductions (a)-(f)
# --------------------------------------------------------------------------

CH8_CHART = {
    B.MARS: R.ARIES,
    B.VENUS: R.TAURUS,
    B.SUN: R.TAURUS,
    B.MERCURY: R.GEMINI,
    B.JUPITER: R.CANCER,
    B.SATURN: R.LEO,
    B.RAHU: R.LEO,
    B.MOON: R.SCORPIO,
    B.KETU: R.AQUARIUS,
}


def _aspected(body: B) -> set[B]:
    by = {r.body: r for r in planet_rashi_drishti(CH8_CHART)}
    return set(by[body].aspected_bodies)


def test_ch8_printed_deductions_that_agree_with_the_verse() -> None:
    assert _aspected(B.MARS) == {B.SATURN, B.MOON, B.RAHU, B.KETU}  # (a)
    assert _aspected(B.MERCURY) == set()  # (b), Mercury part
    assert _aspected(B.JUPITER) == {B.MOON, B.KETU, B.SUN, B.VENUS}  # (c)
    assert _aspected(B.SATURN) == _aspected(B.RAHU) == {B.MARS}  # (d)
    assert _aspected(B.MOON) == {B.MARS, B.JUPITER}  # (e)
    assert _aspected(B.KETU) == {B.MARS, B.JUPITER}  # (f)


def test_ch8_deduction_b_for_venus_and_sun_contradicts_the_verse() -> None:
    # Printed (b) says Venus and the Sun aspect none; by the verse Taurus aspects Cancer,
    # and (c) itself has Jupiter (Cancer) aspecting them. The verse is followed.
    assert _aspected(B.VENUS) == {B.JUPITER}
    assert _aspected(B.SUN) == {B.JUPITER}


def test_planet_rashi_drishti_is_mutual_and_sign_based() -> None:
    results = planet_rashi_drishti(CH8_CHART)
    by = {r.body: r for r in results}
    for r in results:
        assert r.profile_id == PLANET_RASHI_DRISHTI_PROFILE_ID
        assert len(r.aspected_signs) == 3
        assert r.body not in r.aspected_bodies
        for other in r.aspected_bodies:
            assert r.body in by[other].aspected_bodies


def test_planet_rashi_drishti_is_not_graha_drishti() -> None:
    # Mars in Aries: graha drishti falls on the 4th, 7th and 8th houses from it (Cancer,
    # Libra, Scorpio); Rashi Drishti falls on Leo, Scorpio, Aquarius. Different systems.
    signs = list(R)
    graha = {signs[h - 1] for h in aspected_houses(B.MARS, 1)}  # houses counted from Aries
    rashi = set({r.body: r for r in planet_rashi_drishti(CH8_CHART)}[B.MARS].aspected_signs)
    assert graha == {R.CANCER, R.LIBRA, R.SCORPIO}
    assert rashi == {R.LEO, R.SCORPIO, R.AQUARIUS}


# --------------------------------------------------------------------------
# Ch. 29: the standard nativity (p. 294) and its Arudha chart (p. 295)
# --------------------------------------------------------------------------

STANDARD_LONGITUDES = {
    B.SUN: _dms(37, 12, 18),
    B.MOON: _dms(27, 35, 46),
    B.MARS: _dms(96, 18, 46),
    B.MERCURY: _dms(14, 54, 13),
    B.JUPITER: _dms(116, 7, 13),
    B.VENUS: _dms(27, 17, 50),
    B.SATURN: _dms(63, 9, 41),
    B.RAHU: _dms(97, 37, 6),
    B.KETU: _dms(277, 37, 6),
}
STANDARD_SIGNS = {b: rashi_from_longitude(lon) for b, lon in STANDARD_LONGITUDES.items()}
STANDARD_LAGNA = R.SCORPIO  # Ascendant 0 deg 48' 34" Scorpio (p. 293)

#: The printed Arudha chart, p. 295 (page image): Pisces I, VII; Aquarius X, VIII, II;
#: Capricorn IX; Cancer VI, XII; Scorpio XI, III, V; Libra IV.
PRINTED_ARUDHA = {
    1: R.PISCES,
    2: R.AQUARIUS,
    3: R.SCORPIO,
    4: R.LIBRA,
    5: R.SCORPIO,
    6: R.CANCER,
    7: R.PISCES,
    8: R.AQUARIUS,
    9: R.CAPRICORN,
    10: R.AQUARIUS,
    11: R.SCORPIO,
    12: R.CANCER,
}


def test_standard_nativity_lagna_pada_is_pisces() -> None:
    # p. 295-296: "we count 9 signs from Cancer and get Pisces".
    first = bhava_padas(STANDARD_LAGNA, STANDARD_SIGNS)[0]
    assert (first.lord, first.lord_sign, first.count, first.pada) == (
        B.MARS,
        R.CANCER,
        9,
        R.PISCES,
    )
    assert first.name == "lagna_pada"


def test_printed_arudha_chart_agrees_except_houses_9_and_10() -> None:
    padas = {p.house: p for p in bhava_padas(STANDARD_LAGNA, STANDARD_SIGNS)}
    agree = {h for h in range(1, 13) if padas[h].pada == PRINTED_ARUDHA[h]}
    assert agree == {1, 2, 3, 4, 5, 6, 7, 8, 11, 12}
    # Documented source-internal disagreement (the verse rule is followed): for the
    # 9th and 10th: the Pada falls in the 7th, and the verse moves it to the 4th; the chart
    # leaves it in the 7th (it applies the same exception for the 6th house).
    assert padas[9].pada is R.LIBRA and padas[9].rule is PadaRule.SEVENTH_HOUSE_TAKES_FOURTH
    assert padas[10].pada is R.SCORPIO and padas[10].rule is PadaRule.SEVENTH_HOUSE_TAKES_FOURTH
    assert padas[6].rule is PadaRule.SEVENTH_HOUSE_TAKES_FOURTH
    assert padas[12].rule is PadaRule.SAME_HOUSE_TAKES_TENTH


def test_note_examples() -> None:
    # Note 1: lord in its own house (Jupiter in Sagittarius) -> the 10th, Virgo.
    placements = {b: R.ARIES for b in B}
    placements[B.JUPITER] = R.SAGITTARIUS
    padas = {p.house_sign: p for p in bhava_padas(R.SAGITTARIUS, placements)}
    assert padas[R.SAGITTARIUS].pada is R.VIRGO
    # Note 3: Leo ascendant, the Sun in the 4th (Scorpio) -> Scorpio.
    placements[B.SUN] = R.SCORPIO
    assert bhava_padas(R.LEO, placements)[0].pada is R.SCORPIO
    # Note 2 says Aquarius ascendant with Saturn in Leo gives Taurus; the verse rule (Saturn
    # 7 signs away, 7 more is Aquarius itself, so the 10th) gives Scorpio.
    placements[B.SATURN] = R.LEO
    first = bhava_padas(R.AQUARIUS, placements)[0]
    assert (first.pada, first.rule) == (R.SCORPIO, PadaRule.SAME_HOUSE_TAKES_TENTH)


def test_pada_never_in_the_house_or_its_seventh() -> None:
    for lagna in R:
        for lord_offset in range(12):
            placements = {b: lagna for b in B}
            for b in B:
                placements[b] = R(list(R)[(list(R).index(lagna) + lord_offset) % 12].value)
            for p in bhava_padas(lagna, placements):
                assert p.pada is not p.house_sign
                seventh = list(R)[(list(R).index(p.house_sign) + 6) % 12]
                assert p.pada is not seventh


def test_bhava_padas_need_every_lord() -> None:
    with pytest.raises(ValueError):
        bhava_padas(R.ARIES, {B.MARS: R.ARIES})


def test_graha_padas() -> None:
    # Note example: the Sun in Capricorn -> 8 signs to Leo -> 8 more -> Pisces.
    result = {g.body: g for g in graha_padas({B.SUN: R.CAPRICORN, B.MOON: R.CANCER})}
    assert result[B.SUN].pada is R.PISCES
    assert result[B.MOON].pada is R.CANCER  # in own sign: count 1, no exception for planets
    for body in (B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN):
        assert result[body].status is PadaStatus.NOT_EVALUABLE
        assert result[body].reason is PadaReason.STRONGER_SIGN_UNDEFINED
    for node in (B.RAHU, B.KETU):
        assert result[node].reason is PadaReason.NODE_OWNS_NO_SIGN
    assert graha_padas({})[0].reason is PadaReason.PLANET_MISSING


def test_pada_names() -> None:
    assert len(PADA_NAMES) == 12 and PADA_NAMES[6] == "dara_pada"


# --------------------------------------------------------------------------
# Karakamsa (Ch. 33 v. 1-2): the printed Navamsa chart places the Moon, the Atma Karaka,
# in Sagittarius (p. 294).
# --------------------------------------------------------------------------


@pytest.mark.parametrize("profile", [CHARA_KARAKA_EIGHT_BODY_ID, CHARA_KARAKA_SEVEN_BODY_ID])
def test_standard_nativity_karakamsa(profile: str) -> None:
    bodies = [B.SUN, B.MOON, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN]
    if profile == CHARA_KARAKA_EIGHT_BODY_ID:
        bodies.append(B.RAHU)
    longitudes = {b: STANDARD_LONGITUDES[b] for b in bodies}
    chara = calculate_chara_karaka(CharaKarakaRequest(profile_id=profile, longitudes=longitudes))
    result = karakamsa(chara, longitudes)
    assert result.profile_id == KARAKAMSA_PROFILE_ID
    assert result.chara_karaka_profile_id == profile
    assert result.status is KarakamsaStatus.SUCCESS
    assert result.atma_karaka is B.MOON
    assert result.karakamsa is R.SAGITTARIUS


def test_printed_navamsa_chart_matches_phase5_d9() -> None:
    # p. 294 Navamsa chart: Sun, Ketu Pisces; Jupiter Aquarius; Mars, Mercury Leo; Rahu
    # Virgo; Saturn Libra; Moon, Venus Sagittarius.
    printed = {
        B.SUN: R.PISCES,
        B.KETU: R.PISCES,
        B.JUPITER: R.AQUARIUS,
        B.MARS: R.LEO,
        B.MERCURY: R.LEO,
        B.RAHU: R.VIRGO,
        B.SATURN: R.LIBRA,
        B.MOON: R.SAGITTARIUS,
        B.VENUS: R.SAGITTARIUS,
    }
    for body, sign in printed.items():
        assert calculate_varga_sign(9, STANDARD_LONGITUDES[body]) is sign, body


def test_karakamsa_not_evaluable_on_atma_tie() -> None:
    tied = {
        B.SUN: 10.5,
        B.MOON: 40.5,
        B.MARS: 70.2,
        B.MERCURY: 100.1,
        B.JUPITER: 130.05,
        B.VENUS: 160.02,
        B.SATURN: 190.01,
    }
    chara = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=tied)
    )
    result = karakamsa(chara, tied)
    assert result.status is KarakamsaStatus.NOT_EVALUABLE
    assert result.reason is KarakamsaReason.ATMA_KARAKA_UNRESOLVED
    assert result.karakamsa is None
