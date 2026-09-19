"""Golden cases for the first-tranche rule families (Phase 6N).

Each case is a Phase 5 Kundli-shaped chart plus the expected result of chosen
rules. The expected values are written by hand from the source conditions --
they are NOT produced by running the engine -- so a case checks the
methodology rather than echoing the implementation. Every case names the
source profile(s) it exercises.

Run `python -m tests.golden_cases` to (re)write `tests/fixtures/golden/*.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.chart_builder import Placement, kundli_dict

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"

NE = "NOT_EVALUABLE"
P = "BPHS_KAPOOR_PMP_75_1_2_"
N = "BPHS_SAN_NABHASA_35_"


def case(
    case_id: str,
    description: str,
    profiles: list[str],
    lagna: str,
    placements: dict[str, Placement],
    expected: dict[str, str],
    **chart_kwargs: Any,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "description": description,
        "profiles": profiles,
        "kundli": kundli_dict(lagna, placements, **chart_kwargs),
        "expected": expected,
    }


def seven(
    lagna_planets: dict[str, Placement], rahu: Placement, ketu: Placement
) -> dict[str, Placement]:
    return {**lagna_planets, "rahu": rahu, "ketu": ketu}


SAMPLE_A: dict[str, Placement] = {
    "sun": ("aries", 10.0),
    "moon": ("cancer", 10.0),
    "mars": ("capricorn", 5.0),
    "mercury": ("gemini", 3.0),
    "jupiter": ("cancer", 15.0),
    "venus": ("taurus", 4.0),
    "saturn": ("libra", 8.0),
    "rahu": ("leo", 2.0),
    "ketu": ("aquarius", 2.0),
}

MARS_FREE_OF_BENEFIC_LINK_LIBRA: dict[str, Placement] = {
    "sun": ("capricorn", 10.0),
    "moon": ("scorpio", 10.0),
    "mars": ("libra", 10.0),
    "mercury": ("sagittarius", 10.0),
    "jupiter": ("virgo", 10.0),
    "venus": ("taurus", 10.0),
    "saturn": ("cancer", 10.0),
    "rahu": ("aquarius", 10.0),
    "ketu": ("leo", 10.0),
}

LAGNADHI_BASE: dict[str, Placement] = {
    "sun": ("sagittarius", 10.0),
    "moon": ("sagittarius", 20.0),
    "mars": ("sagittarius", 15.0),
    "mercury": ("sagittarius", 25.0),
    "jupiter": ("libra", 10.0),
    "venus": ("scorpio", 10.0),
    "saturn": ("sagittarius", 5.0),
    "rahu": ("sagittarius", 2.0),
    "ketu": ("sagittarius", 3.0),
}

CASES: list[dict[str, Any]] = [
    # ---- Pancha Mahapurusha (BPHS Ch. 75 v. 1-2) ----
    case(
        "pmp_sample_a",
        "Mars exalted in the 10th, Jupiter exalted in the 4th, Saturn exalted in the 7th; "
        "Venus (own sign) and Mercury are not in a kendra.",
        ["BPHS_KAPOOR_PMP_75_1_2_RUCHAKA", "..._HAMSA", "..._SHASHA", "..._MALAVYA", "..._BHADRA"],
        "aries",
        SAMPLE_A,
        {
            P + "RUCHAKA": "TRIGGERED",
            P + "HAMSA": "TRIGGERED",
            P + "SHASHA": "TRIGGERED",
            P + "MALAVYA": "NOT_TRIGGERED",
            P + "BHADRA": "NOT_TRIGGERED",
        },
    ),
    case(
        "pmp_negative_dignity_and_house",
        "Mars in a neutral sign in a kendra, and Mars in its own sign outside a kendra.",
        ["BPHS_KAPOOR_PMP_75_1_2_RUCHAKA"],
        "aries",
        {"mars": ("gemini", 10.0)},
        {P + "RUCHAKA": "NOT_TRIGGERED"},
    ),
    case(
        "pmp_negative_own_sign_not_kendra",
        "Mars in its own sign Scorpio, the 8th house: not a kendra.",
        ["BPHS_KAPOOR_PMP_75_1_2_RUCHAKA"],
        "aries",
        {"mars": ("scorpio", 10.0)},
        {P + "RUCHAKA": "NOT_TRIGGERED"},
    ),
    case(
        "pmp_boundary_mercury_virgo_lagna",
        "Mercury in Virgo (exalted, also its own sign) in the Lagna: Bhadra.",
        ["BPHS_KAPOOR_PMP_75_1_2_BHADRA"],
        "virgo",
        {"mercury": ("virgo", 29.9)},
        {P + "BHADRA": "TRIGGERED"},
    ),
    case(
        "pmp_missing_dependency",
        "Jupiter is absent from the chart: Hamsa cannot be evaluated.",
        ["BPHS_KAPOOR_PMP_75_1_2_HAMSA"],
        "aries",
        {"mars": ("capricorn", 5.0)},
        {P + "HAMSA": NE + "(missing_dependency)", P + "RUCHAKA": "TRIGGERED"},
    ),
    # ---- Nabhasa (BPHS Ch. 35) ----
    case(
        "nabhasa_rajju_and_sankhya_cancelled",
        "All seven planets in movable signs across four signs: Rajju; Kedara is suppressed.",
        ["BPHS_SAN_NABHASA_35_RAJJU", "BPHS_SAN_NABHASA_35_KEDARA"],
        "aries",
        seven(
            {
                "sun": ("aries", 10.0),
                "moon": ("cancer", 10.0),
                "mars": ("cancer", 20.0),
                "mercury": ("libra", 10.0),
                "jupiter": ("libra", 20.0),
                "venus": ("capricorn", 10.0),
                "saturn": ("capricorn", 20.0),
            },
            ("taurus", 5.0),
            ("scorpio", 5.0),
        ),
        {
            N + "RAJJU": "TRIGGERED",
            N + "MUSALA": "NOT_TRIGGERED",
            N + "NALA": "NOT_TRIGGERED",
            N + "KEDARA": "CANCELLED",
        },
    ),
    case(
        "nabhasa_nauka_seven_continuous_houses",
        "One planet in each of the seven houses from the Lagna: Nauka; Veena is suppressed.",
        ["BPHS_SAN_NABHASA_35_NAUKA", "BPHS_SAN_NABHASA_35_VEENA"],
        "aries",
        seven(
            {
                "sun": ("aries", 10.0),
                "moon": ("taurus", 10.0),
                "mars": ("gemini", 10.0),
                "mercury": ("cancer", 10.0),
                "jupiter": ("leo", 10.0),
                "venus": ("virgo", 10.0),
                "saturn": ("libra", 10.0),
            },
            ("scorpio", 5.0),
            ("pisces", 5.0),
        ),
        {N + "NAUKA": "TRIGGERED", N + "KOOTA": "NOT_TRIGGERED", N + "VEENA": "CANCELLED"},
    ),
    case(
        "nabhasa_ambiguity_all_in_one_sign",
        "All seven planets in the Lagna sign: Sakata's two readings disagree (contained versus "
        "both houses occupied); Rajju holds and cancels Gola.",
        ["BPHS_SAN_NABHASA_35_SAKATA", "BPHS_SAN_NABHASA_35_RAJJU", "BPHS_SAN_NABHASA_35_GOLA"],
        "aries",
        seven(
            {
                b: ("aries", 5.0 + i)
                for i, b in enumerate(
                    ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]
                )
            },
            ("cancer", 5.0),
            ("capricorn", 5.0),
        ),
        {
            N + "SAKATA": NE + "(reading_ambiguous)",
            N + "RAJJU": "TRIGGERED",
            N + "GOLA": "CANCELLED",
        },
    ),
    case(
        "nabhasa_sankhya_source_gap",
        "Seven planets in two signs and no defined earlier Nabhasa yoga: Yuga is detected but the "
        "suppression cannot be ruled out because Ardhachandra has no condition in the source.",
        ["BPHS_SAN_NABHASA_35_YUGA"],
        "aries",
        seven(
            {
                "sun": ("taurus", 10.0),
                "moon": ("taurus", 25.0),
                "mars": ("taurus", 20.0),
                "mercury": ("sagittarius", 10.0),
                "jupiter": ("sagittarius", 12.0),
                "venus": ("sagittarius", 14.0),
                "saturn": ("sagittarius", 16.0),
            },
            ("cancer", 5.0),
            ("capricorn", 5.0),
        ),
        {N + "YUGA": NE + "(condition_absent_in_source)", N + "GOLA": "NOT_TRIGGERED"},
    ),
    case(
        "nabhasa_sarpa_and_maala",
        "Malefics in three angles, benefics in one: Sarpa, not Maala; Sarpa suppresses Daama.",
        ["BPHS_SAN_NABHASA_35_SARPA", "BPHS_SAN_NABHASA_35_MAALA", "BPHS_SAN_NABHASA_35_DAAMA"],
        "aries",
        SAMPLE_A,
        {N + "SARPA": "TRIGGERED", N + "MAALA": "NOT_TRIGGERED", N + "DAAMA": "CANCELLED"},
    ),
    # ---- Lunar and solar yogas (BPHS Ch. 36 v. 37, Ch. 37, Ch. 38) ----
    case(
        "lunar_solar_sample_a",
        "Node in the 2nd from the Moon makes Sunapha and Duradhara depend on node participation; "
        "Mercury in the 12th gives Anapha; Venus in the 2nd from the Sun gives Vesi.",
        [
            "BPHS_SAN_SUNAPHA_37_7_10",
            "BPHS_SAN_ANAPHA_37_7_10",
            "BPHS_SAN_DURADHARA_37_7_10",
            "BPHS_SAN_VESI_38_1",
            "BPHS_SAN_VOSI_38_1",
            "BPHS_SAN_DHANA_MOON_37_6",
        ],
        "aries",
        SAMPLE_A,
        {
            "BPHS_SAN_SUNAPHA_37_7_10": NE + "(node_participation_unspecified)",
            "BPHS_SAN_ANAPHA_37_7_10": "TRIGGERED",
            "BPHS_SAN_DURADHARA_37_7_10": NE + "(node_participation_unspecified)",
            "BPHS_SAN_VESI_38_1": "TRIGGERED",
            "BPHS_SAN_VOSI_38_1": "NOT_TRIGGERED",
            "BPHS_SAN_UBHAYACHARI_38_1": "NOT_TRIGGERED",
            "BPHS_SAN_DHANA_MOON_37_6": "TRIGGERED",
            "BPHS_SAN_ADHI_MOON_37_5": "NOT_TRIGGERED",
            "BPHS_SAN_LAGNADHI_36_37": "NOT_TRIGGERED",
        },
    ),
    case(
        "sunapha_definite_with_classical_planet",
        "Mars in the 2nd from the Moon: Sunapha holds whatever the nodes do.",
        ["BPHS_SAN_SUNAPHA_37_7_10"],
        "aries",
        seven(
            {
                "sun": "aries",
                "moon": "cancer",
                "mars": "leo",
                "mercury": "aries",
                "jupiter": "aries",
                "venus": "aries",
                "saturn": "aries",
            },
            "leo",
            "aquarius",
        ),
        {"BPHS_SAN_SUNAPHA_37_7_10": "TRIGGERED"},
    ),
    case(
        "kemadruma_sun_scope_ambiguity_and_phaladeepika_cancellation",
        "Only the Sun stands in an angle from the Lagna and nothing is near the Moon: the BPHS "
        "readings on the Sun's scope disagree; the Phaladeepika profile is cancelled by a planet "
        "in a kendra from the Moon.",
        ["BPHS_SAN_KEMADRUMA_37_11_13", "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5"],
        "aries",
        {
            "sun": ("aries", 10.0),
            "moon": ("gemini", 10.0),
            "mars": ("leo", 10.0),
            "mercury": ("virgo", 10.0),
            "jupiter": ("scorpio", 10.0),
            "venus": ("sagittarius", 10.0),
            "saturn": ("aquarius", 10.0),
            "rahu": ("pisces", 10.0),
            "ketu": ("virgo", 20.0),
        },
        {
            "BPHS_SAN_KEMADRUMA_37_11_13": NE + "(reading_ambiguous)",
            "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5": "CANCELLED",
        },
    ),
    case(
        "adhi_moon_house_semantics_ambiguity",
        "One benefic (Jupiter) in the 6th from the Moon: 'each of 6, 7, 8' and 'any' disagree.",
        ["BPHS_SAN_ADHI_MOON_37_5"],
        "aries",
        {
            "sun": ("aries", 10.0),
            "moon": ("cancer", 10.0),
            "mars": ("aries", 20.0),
            "mercury": ("aries", 25.0),
            "jupiter": ("sagittarius", 10.0),
            "venus": ("aries", 28.0),
            "saturn": ("aries", 29.0),
            "rahu": ("leo", 10.0),
            "ketu": ("aquarius", 10.0),
        },
        {"BPHS_SAN_ADHI_MOON_37_5": NE + "(reading_ambiguous)"},
    ),
    case(
        "lagnadhi_triggered_when_no_malefic_can_affect_the_benefics",
        "Jupiter in the 7th and Venus in the 8th; every malefic, nodes included, sits where it "
        "neither joins nor aspects them.",
        ["BPHS_SAN_LAGNADHI_36_37"],
        "aries",
        LAGNADHI_BASE,
        {"BPHS_SAN_LAGNADHI_36_37": "TRIGGERED"},
    ),
    case(
        "lagnadhi_node_participation_dependency",
        "As above but Ketu stands where it could aspect Jupiter: the result depends on whether "
        "the source counts the nodes.",
        ["BPHS_SAN_LAGNADHI_36_37"],
        "aries",
        LAGNADHI_BASE | {"ketu": ("gemini", 2.0)},
        {"BPHS_SAN_LAGNADHI_36_37": NE + "(node_participation_unspecified)"},
    ),
    case(
        "lagnadhi_partial_drishti_dependency",
        "As above but Saturn stands where a partial aspect on Jupiter may exist.",
        ["BPHS_SAN_LAGNADHI_36_37"],
        "aries",
        LAGNADHI_BASE | {"saturn": ("gemini", 5.0)},
        {"BPHS_SAN_LAGNADHI_36_37": NE + "(requires_partial_drishti)"},
    ),
    # ---- Gajakesari (BPHS Ch. 36 v. 3-4) and Phaladeepika Kesari ----
    case(
        "gajakesari_positive",
        "Jupiter (exalted, in the 4th) conjunct the waxing Moon, not combust or in an enemy sign.",
        ["BPHS_SAN_GAJAKESARI_36_3_4", "PHALADEEPIKA_SASTRI_KESARI_6_14"],
        "aries",
        SAMPLE_A,
        {"BPHS_SAN_GAJAKESARI_36_3_4": "TRIGGERED", "PHALADEEPIKA_SASTRI_KESARI_6_14": "TRIGGERED"},
    ),
    case(
        "gajakesari_negative_no_kendra",
        "Jupiter is not in an angle from the Lagna and is the 12th from the Moon.",
        ["BPHS_SAN_GAJAKESARI_36_3_4", "PHALADEEPIKA_SASTRI_KESARI_6_14"],
        "aries",
        {
            "sun": ("aries", 10.0),
            "moon": ("gemini", 10.0),
            "mars": ("leo", 10.0),
            "mercury": ("virgo", 10.0),
            "jupiter": ("taurus", 10.0),
            "venus": ("sagittarius", 10.0),
            "saturn": ("aquarius", 10.0),
            "rahu": ("pisces", 10.0),
            "ketu": ("virgo", 20.0),
        },
        {
            "BPHS_SAN_GAJAKESARI_36_3_4": "NOT_TRIGGERED",
            "PHALADEEPIKA_SASTRI_KESARI_6_14": "NOT_TRIGGERED",
        },
    ),
    case(
        "gajakesari_exclusion_attachment_ambiguity",
        "Jupiter debilitated in the 10th with a benefic conjunct: the readings on whom the "
        "exclusions attach to disagree.",
        ["BPHS_SAN_GAJAKESARI_36_3_4"],
        "aries",
        {
            "sun": ("leo", 10.0),
            "moon": ("aries", 10.0),
            "mars": ("aries", 20.0),
            "mercury": ("virgo", 10.0),
            "jupiter": ("capricorn", 10.0),
            "venus": ("capricorn", 20.0),
            "saturn": ("libra", 10.0),
            "rahu": ("pisces", 10.0),
            "ketu": ("virgo", 20.0),
        },
        {"BPHS_SAN_GAJAKESARI_36_3_4": NE + "(reading_ambiguous)"},
    ),
    case(
        "gajakesari_enemy_sign_basis_ambiguity",
        "Jupiter in Taurus (lord Venus, a natural enemy) with Venus a temporal friend: the natural "
        "and compound readings of 'inimical sign' disagree.",
        ["BPHS_SAN_GAJAKESARI_36_3_4"],
        "taurus",
        {
            "sun": ("aries", 10.0),
            "moon": ("taurus", 10.0),
            "mars": ("leo", 10.0),
            "mercury": ("virgo", 10.0),
            "jupiter": ("taurus", 20.0),
            "venus": ("gemini", 10.0),
            "saturn": ("aquarius", 10.0),
            "rahu": ("pisces", 10.0),
            "ketu": ("virgo", 20.0),
        },
        {"BPHS_SAN_GAJAKESARI_36_3_4": NE + "(reading_ambiguous)"},
    ),
    case(
        "gajakesari_missing_dependency",
        "No Jupiter in the chart.",
        ["BPHS_SAN_GAJAKESARI_36_3_4"],
        "aries",
        {"sun": ("aries", 10.0), "moon": ("cancer", 10.0)},
        {"BPHS_SAN_GAJAKESARI_36_3_4": NE + "(missing_dependency)"},
    ),
    # ---- Mangal / Kuja (BPHS Ch. 80 v. 47-49; Jataka Parijata v. 34) ----
    case(
        "kuja_mars_in_third",
        "Mars in the 3rd from the Lagna: neither profile applies.",
        ["BPHS_KAPOOR_80_47_49_MARS_HOUSES", "JP_KUJA_DOSHA"],
        "aries",
        SAMPLE_A | {"mars": ("gemini", 5.0), "mercury": ("virgo", 3.0)},
        {"BPHS_KAPOOR_80_47_49_MARS_HOUSES": "NOT_TRIGGERED", "JP_KUJA_DOSHA": "NOT_TRIGGERED"},
    ),
    case(
        "kuja_partner_chart_dependency",
        "Mars in the 7th with no benefic joined to or able to aspect it: the BPHS placement holds "
        "in both readings but its cancellation needs the partner's chart; JP applies.",
        ["BPHS_KAPOOR_80_47_49_MARS_HOUSES", "JP_KUJA_DOSHA"],
        "aries",
        MARS_FREE_OF_BENEFIC_LINK_LIBRA,
        {
            "BPHS_KAPOOR_80_47_49_MARS_HOUSES": NE + "(requires_partner_chart)",
            "JP_KUJA_DOSHA": "TRIGGERED",
        },
    ),
    case(
        "kuja_mars_in_lagna_reading_ambiguity",
        "Mars in the Lagna: reading A (12, 4, 7, 8) does not apply, reading B (with the Lagna) "
        "does, so the profile is reading_ambiguous; JP (2, 4, 7, 8, 12) does not apply.",
        ["BPHS_KAPOOR_80_47_49_MARS_HOUSES", "JP_KUJA_DOSHA"],
        "aries",
        {
            "sun": ("leo", 10.0),
            "moon": ("scorpio", 10.0),
            "mars": ("aries", 10.0),
            "mercury": ("gemini", 10.0),
            "jupiter": ("pisces", 10.0),
            "venus": ("taurus", 10.0),
            "saturn": ("capricorn", 10.0),
            "rahu": ("cancer", 10.0),
            "ketu": ("capricorn", 20.0),
        },
        {
            "BPHS_KAPOOR_80_47_49_MARS_HOUSES": NE + "(reading_ambiguous)",
            "JP_KUJA_DOSHA": "NOT_TRIGGERED",
        },
    ),
    case(
        "kuja_benefic_conjunct_removes_bphs_yoga",
        "Mars in the 7th conjunct Jupiter: the BPHS condition (unaspected and unassociated by a "
        "benefic) fails; the JP profile has no such exception.",
        ["BPHS_KAPOOR_80_47_49_MARS_HOUSES", "JP_KUJA_DOSHA"],
        "aries",
        MARS_FREE_OF_BENEFIC_LINK_LIBRA | {"jupiter": ("libra", 20.0)},
        {"BPHS_KAPOOR_80_47_49_MARS_HOUSES": "NOT_TRIGGERED", "JP_KUJA_DOSHA": "TRIGGERED"},
    ),
    case(
        "kuja_full_aspect_of_benefic",
        "Mars in the 7th aspected by Venus in the 1st (full 7th aspect).",
        ["BPHS_KAPOOR_80_47_49_MARS_HOUSES"],
        "aries",
        MARS_FREE_OF_BENEFIC_LINK_LIBRA | {"venus": ("aries", 10.0)},
        {"BPHS_KAPOOR_80_47_49_MARS_HOUSES": "NOT_TRIGGERED"},
    ),
    case(
        "kuja_partial_drishti_dependency",
        "Mars in the 7th with Venus in Aquarius, a house from which a partial aspect may exist.",
        ["BPHS_KAPOOR_80_47_49_MARS_HOUSES"],
        "aries",
        MARS_FREE_OF_BENEFIC_LINK_LIBRA | {"venus": ("aquarius", 10.0)},
        {"BPHS_KAPOOR_80_47_49_MARS_HOUSES": NE + "(requires_partial_drishti)"},
    ),
]


def write_fixtures() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for item in CASES:
        path = GOLDEN_DIR / f"{item['case_id']}.json"
        path.write_text(json.dumps(item, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_fixtures()
    print(f"wrote {len(CASES)} golden fixtures to {GOLDEN_DIR}")
