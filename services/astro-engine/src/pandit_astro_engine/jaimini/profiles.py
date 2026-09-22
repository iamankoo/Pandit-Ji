"""Jaimini methodology profiles (Phase 9 WP-B-1/WP-B-2;
`docs/ASTROLOGY_STANDARDS.md` v1.10.0 JN-01/JN-02, v1.11.0 JN-06 to JN-10).

**Rashi Drishti (WP-B-1)**: one profile, one source: BPHS Ch. 8 v. 1-3
(Santhanam translation). The chapter's own translator note (page-image
verified, printed pp. 105-106) states this Rasi/sign-aspect rule is
Parasara's own, and is only nicknamed "Jaimini Rasi Drishti" because sage
Jaimini's separate corpus also uses it -- so the profile is never presented
as a Jaimini-authored rule.

**Chara Karaka (WP-B-2)**: BPHS Ch. 32 v. 1-2 (page-image re-verified) does
not settle its own candidate-body scope -- it states three positions
("Some say ... yet some say ...") without choosing one. Rather than pick a
winner, two profiles are shipped, mirroring the Ashtakavarga precedent of
never merging disagreeing source readings: `CHARA_KARAKA_SEVEN_BODY_ID` (the
base rule, the 7 classical planets only) and `CHARA_KARAKA_EIGHT_BODY_ID`
(the "yet some say" 8-body-unconditional reading, which the chapter's own
translator's note says is what its own worked example, "the standard
nativity", actually uses). The third, conditional reading ("Rahu becomes a
Karka when there is a state of similarity in ... longitude between two
planets") is read but not implemented: the source does not define the
condition precisely enough to implement without inventing it. No default is
chosen between the two shipped profiles; a caller must name one explicitly.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.models import CelestialBody


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Matches the vocabulary of `pandit_astro_engine.ashtakavarga.profiles`,
    `.dashas.profiles` and `.transits.profiles` -- each phase module keeps
    its own copy rather than sharing a cross-phase import."""

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


RASHI_DRISHTI_PROFILE_ID = "RASHI_DRISHTI_BPHS_8_1_3"


class RashiDrishtiProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    verification_level: str
    reference: SourceReference


RASHI_DRISHTI_PROFILE = RashiDrishtiProfileDef(
    profile_id=RASHI_DRISHTI_PROFILE_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title="Brihat Parasara Hora Shastra (Santhanam translation) Ch. 8 v. 1-3",
    verification_level="IMAGE-TRANSLATION",
    reference=SourceReference(
        source_id="SRC-BPHS-SANTHANAM-1984",
        locator="Vol I Ch. 8 v. 1-3 (Santhanam translation), printed pp. 105-107",
        verification_level="IMAGE-TRANSLATION",
        note=(
            "Every movable sign aspects the 3 fixed signs other than the fixed sign "
            "adjacent to it; every fixed sign aspects the 3 movable signs other than "
            "the movable sign adjacent to it; every common (dual) sign aspects the "
            "other 3 common signs. The chapter's own printed 12-sign worked table "
            "(pp. 106-107) was cross-checked cell by cell against this rule with zero "
            "mismatches. The translator's note (pp. 105-106) attributes the rule to "
            "Parasara, stating it is only nicknamed the 'Jaimini system' because "
            "Jaimini's own corpus also uses it -- this profile is never presented as "
            "Jaimini-authored. v. 4-5 (the same table applied to a planet's own "
            "placement) is read and verified but deliberately not implemented here: "
            "it would produce a planet-level aspect that disagrees with the "
            "already-locked Phase 5/6 Vedic graha drishti for the same placement, "
            "and docs/ASTROLOGY_STANDARDS.md already requires the two systems to "
            "never be blended."
        ),
    ),
)


# --------------------------------------------------------------------------
# Chara Karaka (WP-B-2)
# --------------------------------------------------------------------------

CHARA_KARAKA_SEVEN_BODY_ID = "JAIMINI_CHARA_KARAKA_SEVEN_BODY_BPHS_32_1_17"
CHARA_KARAKA_EIGHT_BODY_ID = "JAIMINI_CHARA_KARAKA_EIGHT_BODY_BPHS_32_1_17"

_SEVEN_CLASSICAL_BODIES: tuple[CelestialBody, ...] = (
    CelestialBody.SUN,
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
)
_EIGHT_BODIES: tuple[CelestialBody, ...] = _SEVEN_CLASSICAL_BODIES + (CelestialBody.RAHU,)

#: Ketu is never a member of either tuple: no position read in Ch. 32 names
#: Ketu as a Chara Karaka candidate under any of the three stated readings.
CHARA_KARAKA_PROFILE_BODIES: dict[str, tuple[CelestialBody, ...]] = {
    CHARA_KARAKA_SEVEN_BODY_ID: _SEVEN_CLASSICAL_BODIES,
    CHARA_KARAKA_EIGHT_BODY_ID: _EIGHT_BODIES,
}


class CharaKarakaProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    verification_level: str
    reference: SourceReference
    bodies: tuple[CelestialBody, ...]


CHARA_KARAKA_PROFILES: dict[str, CharaKarakaProfileDef] = {
    CHARA_KARAKA_SEVEN_BODY_ID: CharaKarakaProfileDef(
        profile_id=CHARA_KARAKA_SEVEN_BODY_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title=(
            "Brihat Parasara Hora Shastra (Santhanam translation) Ch. 32 v. 1-17, 7-planet reading"
        ),
        verification_level="IMAGE-TRANSLATION",
        reference=SourceReference(
            source_id="SRC-BPHS-SANTHANAM-1984",
            locator="Vol I Ch. 32 v. 1-17 (Santhanam translation), printed pp. 316-319",
            verification_level="IMAGE-TRANSLATION",
            note=(
                "v. 1-2's base rule: Atma Karaka etc. are obtainable 'from among the 7 "
                "planets viz the Sun to Saturn'. Rahu is excluded under this reading. "
                "The chapter's own translator's note also mentions a 'school of thought "
                "[with] only seven significators, treating Matru Karaka and Putra "
                "Karaka as identical' -- read but not implemented here (one sentence "
                "only, no worked table showing the merged role's exact rank position); "
                "this profile instead ranks 7 candidates into the first 7 of the "
                "standard 8 roles and reports the 8th (Dara Karaka) as "
                "NOT_EVALUABLE(rank_deficit), never inventing a merge."
            ),
        ),
        bodies=_SEVEN_CLASSICAL_BODIES,
    ),
    CHARA_KARAKA_EIGHT_BODY_ID: CharaKarakaProfileDef(
        profile_id=CHARA_KARAKA_EIGHT_BODY_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="Brihat Parasara Hora Shastra (Santhanam translation) Ch. 32 v. 1-17, 8-body reading",
        verification_level="IMAGE-TRANSLATION",
        reference=SourceReference(
            source_id="SRC-BPHS-SANTHANAM-1984",
            locator="Vol I Ch. 32 v. 1-2, 3-17 (Santhanam translation), printed pp. 316-319",
            verification_level="IMAGE-TRANSLATION",
            note=(
                "v. 1-2's 'yet some say the 8 planets including Rahu will have to be "
                "considered irrespective of' the longitude-similarity condition. The "
                "chapter's own translator's note confirms this is the reading its own "
                "worked example uses ('In the standard nativity (ch. 29) ... We take 8 "
                "Karkas into consideration'), listing all 8 role-to-planet assignments "
                "including Rahu as Matru Karaka. Rahu's comparison degree is 30 minus "
                "his own degree within the sign (v. 3-8's explicit reverse-degree "
                "convention). Ketu is not a candidate under this or any reading."
            ),
        ),
        bodies=_EIGHT_BODIES,
    ),
}
