"""Shadbala methodology profile and per-component provenance (Phase 9 WP-F;
`docs/ASTROLOGY_STANDARDS.md` v1.16.0, SB-01 to SB-20; sources in
`research/ASTROLOGY_SOURCES.md` Group 17).

One profile, `SHADBALA_BPHS_SANTHANAM_27_VERSE`: every component follows the
translated verse of BPHS Ch. 27. Where a component's method exists only in
the translator's notes, or the verse and notes disagree, or the verse is
ambiguous, the component is NOT_EVALUABLE with a reason code -- never filled
with a note-only or modern method. A translator's note is used only where
the verse is silent on a detail and the note does not contradict it, and
the component then carries the `translator_note` label.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Same vocabulary as the other phase modules' own copies -- deliberately
    not a shared cross-phase import."""

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


PROFILE_ID = "SHADBALA_BPHS_SANTHANAM_27_VERSE"
BPHS = "SRC-BPHS-SANTHANAM-1984"
_OCR = "OCR-TRANSLATION"


class Component(str, Enum):
    UCHCHA = "uchcha"
    SAPTAVARGAJA = "saptavargaja"
    OJAYUGMA = "ojayugmarasyamsa"
    KENDRADI = "kendradi"
    DREKKANA = "drekkana"
    STHANA_TOTAL = "sthana_total"
    DIG = "dig"
    NATHONNATHA = "nathonnatha"
    PAKSHA = "paksha"
    TRIBHAGA = "tribhaga"
    ABDA = "abda"
    MASA = "masa"
    VARA = "vara"
    HORA = "hora"
    AYANA = "ayana"
    YUDDHA = "yuddha"
    KALA_TOTAL = "kala_total"
    CHESHTA = "cheshta"
    NAISARGIKA = "naisargika"
    DRIK = "drik"
    SHADBALA_TOTAL = "shadbala_total"


STHANA_PARTS: tuple[Component, ...] = (
    Component.UCHCHA,
    Component.SAPTAVARGAJA,
    Component.OJAYUGMA,
    Component.KENDRADI,
    Component.DREKKANA,
)
KALA_PARTS: tuple[Component, ...] = (
    Component.NATHONNATHA,
    Component.PAKSHA,
    Component.TRIBHAGA,
    Component.ABDA,
    Component.MASA,
    Component.VARA,
    Component.HORA,
    Component.AYANA,
    Component.YUDDHA,
)
#: The six balas summed into the Shadbala Pinda (Ch. 27 v. 24-25).
SIX_BALAS: tuple[Component, ...] = (
    Component.STHANA_TOTAL,
    Component.DIG,
    Component.KALA_TOTAL,
    Component.CHESHTA,
    Component.NAISARGIKA,
    Component.DRIK,
)


class ComponentDef(_Model):
    component: Component
    label: EvidenceLabel
    title: str
    reference: SourceReference


def _ref(locator: str, note: str = "") -> SourceReference:
    return SourceReference(source_id=BPHS, locator=locator, verification_level=_OCR, note=note)


COMPONENTS: dict[Component, ComponentDef] = {
    d.component: d
    for d in (
        ComponentDef(
            component=Component.UCHCHA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title="(longitude - deep debilitation point), folded to <= 180 degrees, divided by 3",
            reference=_ref(
                "Ch. 27 v. 1 (printed pp. 264-265)",
                "Debilitation points: the locked Phase 5 dignity table.",
            ),
        ),
        ComponentDef(
            component=Component.SAPTAVARGAJA,
            label=EvidenceLabel.TRANSLATOR_NOTE,
            title=(
                "Moolatrikona 45, own 30, great friend 20, friend 15, equal 10, enemy 4, great "
                "enemy 2, in each of D1, D2, D3, D7, D9, D12, D30; compound relationship taken "
                "from the Rasi chart"
            ),
            reference=_ref(
                "Ch. 27 v. 2-4 and note (printed p. 265)",
                "The values are verse; 'compound relationships ... be seen in the Rasi chart "
                "only' is the translator's note. The verse says 'Moolatrikona Rasi' (a sign), "
                "while Ch. 3 v. 51-54 gives Moolatrikona as a degree range in the Rasi chart: "
                "a D1 placement in the Moolatrikona sign but outside the range is not evaluated.",
            ),
        ),
        ComponentDef(
            component=Component.OJAYUGMA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title=(
                "15 each for the Rasi and the Navamsa: Moon and Venus in even signs, the others "
                "in odd signs"
            ),
            reference=_ref(
                "Ch. 27 v. 4-5 (printed p. 266)",
                "The note's '35 Virupas' contradicts the verse's quarter Rupa and is not used.",
            ),
        ),
        ComponentDef(
            component=Component.KENDRADI,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title=(
                "Angle 60, succedent 30, cadent 15, by whole-sign house from the Lagna (the "
                "locked Vedic house baseline)"
            ),
            reference=_ref("Ch. 27 v. 5 (printed p. 266)"),
        ),
        ComponentDef(
            component=Component.DREKKANA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title="15 to a male, female, neuter planet in the first, second, third 10-degree part",
            reference=_ref(
                "Ch. 27 v. 6 (printed p. 266); genders Ch. 3 v. 19 (printed p. 31)",
            ),
        ),
        ComponentDef(
            component=Component.DIG,
            label=EvidenceLabel.TRANSLATOR_NOTE,
            title=(
                "(longitude - zero point), folded to <= 180 degrees, divided by 3; zero points: "
                "Nadir for Sun and Mars, descendant for Jupiter and Mercury, meridian for Venus "
                "and Moon, Ascendant for Saturn"
            ),
            reference=_ref(
                "Ch. 27 v. 7 (printed p. 267)",
                "The verse names the 4th, 7th and 10th houses and the ascendant; the "
                "translation glosses them as the Nadir, descendant and meridian, which are used "
                "(sidereal MC and MC + 180).",
            ),
        ),
        ComponentDef(
            component=Component.NATHONNATHA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title=(
                "Unnata = apparent time from midnight (0-30 ghatis); Moon, Mars, Saturn get "
                "2 x (30 - Unnata); Sun, Jupiter, Venus get 60 minus that; Mercury always 60"
            ),
            reference=_ref(
                "Ch. 27 v. 8-9 (printed p. 268)",
                "Apparent solar time from Swiss Ephemeris's equation of time (engineering). The "
                "note's 'simple method' disagrees with the verse and is not used.",
            ),
        ),
        ComponentDef(
            component=Component.PAKSHA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title=(
                "Benefics get (Moon - Sun, folded to <= 180) / 3; malefics get 60 minus that; "
                "benefic/malefic per the locked Phase 6 natural-nature standard"
            ),
            reference=_ref(
                "Ch. 27 v. 10-11 (printed p. 269)",
                "The note's doubling of the Moon's Paksha Bala is not in the verse and is not "
                "applied; the doubled value is not reported.",
            ),
        ),
        ComponentDef(
            component=Component.TRIBHAGA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title=(
                "60 to Mercury, Sun, Saturn in the 1st, 2nd, 3rd third of the day; to Moon, "
                "Venus, Mars in the thirds of the night; Jupiter always 60"
            ),
            reference=_ref(
                "Ch. 27 v. 12 (printed pp. 269-270)",
                "Day = sunrise to sunset, night = sunset to sunrise (Phase 4 sunrise/sunset).",
            ),
        ),
        ComponentDef(
            component=Component.ABDA,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title="Varsha (year) lord 15: NOT_EVALUABLE",
            reference=_ref(
                "Ch. 27 v. 13 and note (printed pp. 270-272)",
                "The verse gives only the value. How the year lord is found exists only in the "
                "note (Surya Siddhanta ahargana via a translator's table), whose stated divisor "
                "(160) disagrees with its own worked example (360).",
            ),
        ),
        ComponentDef(
            component=Component.MASA,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title="Masa (month) lord 30: NOT_EVALUABLE",
            reference=_ref(
                "Ch. 27 v. 13 and note (printed pp. 270-271)",
                "Month lord method only in the note, on the same unverified ahargana.",
            ),
        ),
        ComponentDef(
            component=Component.VARA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title="45 to the lord of the weekday, the day reckoned from sunrise",
            reference=_ref(
                "Ch. 27 v. 13 and note (printed pp. 270-272)",
                "The sunrise-to-sunrise day is also the locked Vara standard.",
            ),
        ),
        ComponentDef(
            component=Component.HORA,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title="Hora lord 60: NOT_EVALUABLE",
            reference=_ref(
                "Ch. 27 v. 13 and note (printed pp. 270-272)",
                "Hora division only in the note (24 equal hours from sunrise, mean local time); "
                "no Pandit Ji Hora standard is locked yet (Phase 10).",
            ),
        ),
        ComponentDef(
            component=Component.AYANA,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title="Ayana Bala: NOT_EVALUABLE",
            reference=_ref(
                "Ch. 27 v. 15-17 and note (printed p. 277 and the following tables)",
                "The verse's khanda procedure (45, 33, 12) and the note's declination formula "
                "(23 deg 27 min +/- kranti) x 1.2793 are different methods; the note also "
                "doubles the Sun's value, which the verse does not.",
            ),
        ),
        ComponentDef(
            component=Component.YUDDHA,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title="Yuddha (planetary war): NOT_EVALUABLE for Mars to Saturn; not applicable to "
            "the Sun and Moon",
            reference=_ref(
                "Ch. 27 v. 20 (printed p. 284)",
                "The chapter does not define when two planets are at war, and the adjustment "
                "uses the finished Shadbala of both planets.",
            ),
        ),
        ComponentDef(
            component=Component.CHESHTA,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title=(
                "Moon: her Paksha Bala (v. 18). Sun: his Ayana Bala (NOT_EVALUABLE). Mars to "
                "Saturn: NOT_EVALUABLE"
            ),
            reference=_ref(
                "Ch. 27 v. 18, 21-25 (printed pp. 284-285)",
                "v. 21-23 (eight kinds of motion, values partly illegible in the OCR) and "
                "v. 24-25 (Cheshta Kendra from the mean longitude and the sighrocca) are two "
                "methods; v. 24-25 needs mean elements the chapter does not supply.",
            ),
        ),
        ComponentDef(
            component=Component.NAISARGIKA,
            label=EvidenceLabel.SOURCE_SUPPORTED,
            title="60/7 x (1 Saturn, 2 Mars, 3 Mercury, 4 Jupiter, 5 Venus, 6 Moon, 7 Sun)",
            reference=_ref("Ch. 27 v. 14 (printed p. 276)"),
        ),
        ComponentDef(
            component=Component.DRIK,
            label=EvidenceLabel.UNRESOLVED_CONFLICT,
            title="Drik Bala: NOT_EVALUABLE",
            reference=_ref(
                "Ch. 27 v. 19 (printed p. 284)",
                "'Reduce one fourth of the Drishti Pinda if a planet has malefic aspects ... add "
                "a fourth if aspected by a benefic ... super add the entire aspect of Mercury and "
                "Jupiter' does not fix one arithmetic; it also depends on Ch. 26 aspect values, "
                "which are themselves not evaluable in some cases (WP-C).",
            ),
        ),
    )
}
