"""Rashi Drishti methodology profile (Phase 9 WP-B-1; `docs/ASTROLOGY_STANDARDS.md`
v1.10.0, JN-01/JN-02).

One profile, one source: BPHS Ch. 8 v. 1-3 (Santhanam translation). The
chapter's own translator note (page-image verified, printed pp. 105-106)
states this Rasi/sign-aspect rule is Parasara's own, and is only nicknamed
"Jaimini Rasi Drishti" because sage Jaimini's separate corpus also uses it
-- so the profile is never presented as a Jaimini-authored rule.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


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
