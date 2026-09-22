"""Partial/Degree Drishti methodology profiles (Phase 9 WP-C;
`docs/ASTROLOGY_STANDARDS.md` v1.12.0/v1.13.0, PD-01).

No cross-source variant of the discrete quarter/half/three-quarter/full
progression was found (Brihat Jataka's and Phaladeepika's superficially
similar chapters are interpretive, not computational, and were ruled out;
Saravali gave a genuine negative keyword result). Two structurally
different methods for the *continuous* refinement were found and are kept
as two separate, explicitly-selected profiles -- no default, never merged,
mirroring the Ashtakavarga precedent of never merging distinct readings.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Matches the vocabulary of every other phase module's own copy
    (`ashtakavarga.profiles`, `dashas.profiles`, `transits.profiles`,
    `jaimini.profiles`) -- deliberately not a shared cross-phase import."""

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


BPHS_26_ID = "PARTIAL_DEGREE_DRISHTI_BPHS_26"
UTTARAKALAMRITA_SRIPATI_ID = "PARTIAL_DEGREE_DRISHTI_UTTARAKALAMRITA_SRIPATI"


class PartialDegreeDrishtiProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    verification_level: str
    reference: SourceReference


BPHS_26_PROFILE = PartialDegreeDrishtiProfileDef(
    profile_id=BPHS_26_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title="Brihat Parasara Hora Shastra (Santhanam translation) Ch. 26 v. 1-13",
    verification_level="IMAGE-TRANSLATION",
    reference=SourceReference(
        source_id="SRC-BPHS-SANTHANAM-1984",
        locator="Vol I Ch. 26 v. 1-13 (Santhanam translation), printed pp. 254-255",
        verification_level="IMAGE-TRANSLATION",
        note=(
            "v. 2-5: the discrete quarter/half/three-quarter/full progression on "
            "3rd/10th, 4th/8th, 5th/9th and 7th. v. 6-9: a five-branch continuous "
            "formula, Sanskrit-verified via the bhutasamkhya number-word convention "
            "(veda=4, bhuta=5, tithi=15, rupa=1) against sanskritdocuments.org "
            "par2130.html; algebraically identical to linear interpolation between "
            "the v.2-5 checkpoints -- a project-level derivation, never presented as "
            "either source's own claim. v. 6's reduction step for separations beyond "
            "180 degrees is Sanskrit-confirmed as the numeral 10 (the word 'dik', a "
            "standard ten-directions number-word), not a translation artifact; this "
            "correctly reproduces the house-8 checkpoint but contradicts BPHS's own "
            "house-9/house-10 pairing statement -- a permanent, unresolved "
            "source-internal conflict, never silently resolved either way. v. 9-12: "
            "separate override formulas for Saturn, Mars and Jupiter, each confirmed "
            "independently to reach exactly 60 (full) at that planet's own special "
            "house; the interior shape away from that exact point is not resolved "
            "(the published English translation and an unreviewed reading of the "
            "Sanskrit disagree on one operation for Saturn's own threshold)."
        ),
    ),
)

UTTARAKALAMRITA_SRIPATI_PROFILE = PartialDegreeDrishtiProfileDef(
    profile_id=UTTARAKALAMRITA_SRIPATI_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title="Uttara Kalamrita (Sastri translation) Ch. 2 Sl. 17.5-19.5",
    verification_level="IMAGE-TRANSLATION",
    reference=SourceReference(
        source_id="SRC-UTTARA-KALAMRITA-SASTRI",
        locator="Ch. 2 ('Determination of Strength') Sl. 17.5-19.5",
        verification_level="IMAGE-TRANSLATION",
        note=(
            "Sl. 17.5-18.5 independently restates BPHS's own discrete "
            "quarter/half/three-quarter/full progression, word for word in "
            "substance. Sl. 18.5-19.5 gives a linear ('rule of three') "
            "interpolation between adjacent discrete checkpoints -- a structurally "
            "different method from BPHS's own v. 6-9, with no reduction step and "
            "therefore no gap at houses 9-10. Cites 'Sripatipaddhati-II' for this "
            "method; that attribution is TRANSLATION-LEVEL, not independently "
            "verified -- the primary Sripatipaddhati text was unreachable via two "
            "independent technical attempts (a non-functional archive.org "
            "reader/search-index and a failed direct-file fetch), not a "
            "content-based finding."
        ),
    ),
)

PROFILES: dict[str, PartialDegreeDrishtiProfileDef] = {
    BPHS_26_ID: BPHS_26_PROFILE,
    UTTARAKALAMRITA_SRIPATI_ID: UTTARAKALAMRITA_SRIPATI_PROFILE,
}
