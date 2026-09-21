"""Transit methodology profiles and source tables (docs/ASTROLOGY_STANDARDS.md
v1.6.0, TR-02 to TR-09).

Every table is a *source-specific reading* with its own ID. Readings are never
merged and no reading is chosen where they disagree. All source statements are
at translation level; no Sanskrit-level verification exists
(`research/ASTROLOGY_SOURCES.md` Phase 8 group, section 6.4).

House numbers are counted whole-sign from the natal Moon's sign (house 1 = the
Moon's own sign).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.models import CelestialBody

SUN = CelestialBody.SUN
MOON = CelestialBody.MOON
MARS = CelestialBody.MARS
MERCURY = CelestialBody.MERCURY
JUPITER = CelestialBody.JUPITER
VENUS = CelestialBody.VENUS
SATURN = CelestialBody.SATURN
RAHU = CelestialBody.RAHU
KETU = CelestialBody.KETU


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """What kind of statement a provenance entry is. Never merged."""

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


# --------------------------------------------------------------------------
# Profile identifiers
# --------------------------------------------------------------------------

REF_MOON_SIGN_ID = "TRANSIT_REF_MOON_SIGN"
REF_LAGNA_SIGN_ID = "TRANSIT_REF_LAGNA_SIGN"

FAV_PHALADEEPIKA_ID = "GOCHARA_FAVOURABLE_PHALADEEPIKA_SASTRI_XXVI_2"
FAV_BRIHAT_SAMHITA_ID = "GOCHARA_FAVOURABLE_BRIHAT_SAMHITA_SASTRI_CIV_4"
FAV_BRIHAT_JATAKA_ID = "GOCHARA_FAVOURABLE_BRIHAT_JATAKA_SASTRI_IX_1_7"
FAV_BPHS_DERIVED_ID = "GOCHARA_FAVOURABLE_BPHS_KAPOOR_66_DERIVED"

VEDHA_PHALADEEPIKA_ID = "GOCHARA_VEDHA_PHALADEEPIKA_SASTRI_XXVI_3_8"

CONTACT_PROFILE_ID = "TRANSIT_CONTACT_SIGN_BASED_V1"
EVENTS_PROFILE_ID = "TRANSIT_EVENTS_ENGINEERING_V1"
BOUNDARY_PROFILE_ID = "TRANSIT_BOUNDARY_HALF_OPEN_V1"
ACCURACY_PROFILE_ID = "TRANSIT_ACCURACY_HORIZONS_V1"

SADE_SATI_ID = "SADE_SATI_SIGN_BASED_MODERN_V1"
#: Reserved modern-tradition variants: documented, never implemented.
RESERVED_MODERN_PROFILE_IDS: frozenset[str] = frozenset(
    {
        "DHAIYA_SIGN_BASED_MODERN_V1",
        "ASHTAMA_SIGN_BASED_MODERN_V1",
        "SADE_SATI_DEGREE_45_MODERN_V1",
    }
)

VENUS_VEDHA_ANOMALY_WARNING = "translation_wording_anomaly_venus_sl8"


# --------------------------------------------------------------------------
# Favourable-house readings (TR-04)
# --------------------------------------------------------------------------

_COMMON_SIX: dict[CelestialBody, frozenset[int]] = {
    SUN: frozenset({3, 6, 10, 11}),
    MARS: frozenset({3, 6, 11}),
    MERCURY: frozenset({2, 4, 6, 8, 10, 11}),
    JUPITER: frozenset({2, 5, 7, 9, 11}),
    VENUS: frozenset({1, 2, 3, 4, 5, 8, 9, 11, 12}),
    SATURN: frozenset({3, 6, 11}),
}

_MOON_PHALADEEPIKA = frozenset({1, 3, 6, 7, 10, 11})
_MOON_BRIHAT_JATAKA = frozenset({1, 3, 5, 7, 10, 11})
_MOON_BPHS_DERIVED = frozenset({1, 3, 6, 7, 9, 10, 11})


class FavourableReadingDef(_Model):
    """One source's favourable houses from the natal Moon, per planet."""

    reading_id: str
    label: EvidenceLabel
    title: str
    verification_level: str
    references: tuple[SourceReference, ...]
    houses: dict[CelestialBody, frozenset[int]]
    covers_nodes: bool = False


FAVOURABLE_READINGS: tuple[FavourableReadingDef, ...] = (
    FavourableReadingDef(
        reading_id=FAV_PHALADEEPIKA_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="Phaladeepika (Sastri) Adhyaya XXVI sl. 2",
        verification_level="IMAGE-TRANSLATION",
        references=(
            SourceReference(
                source_id="SRC-PHALADEEPIKA-SASTRI",
                locator="Adhyaya XXVI sl. 2 (printed p. 286)",
                verification_level="IMAGE-TRANSLATION",
                note=(
                    "Sun 3,6,10; Moon 1,3,6,7,10; Mars and Saturn 3,6; Mercury 2,4,6,8,10; "
                    "Jupiter 2,5,7,9; Venus all except 6,7,10; all planets 11; Rahu and Ketu "
                    "'similar to the Sun' (single source)"
                ),
            ),
        ),
        houses={
            **_COMMON_SIX,
            MOON: _MOON_PHALADEEPIKA,
            RAHU: _COMMON_SIX[SUN],
            KETU: _COMMON_SIX[SUN],
        },
        covers_nodes=True,
    ),
    FavourableReadingDef(
        reading_id=FAV_BRIHAT_SAMHITA_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="Brihat Samhita (Sastri and Bhat) Adhyaya CIV sl. 4",
        verification_level="IMAGE-TRANSLATION",
        references=(
            SourceReference(
                source_id="SRC-BRIHAT-SAMHITA-SASTRI",
                locator="Adhyaya CIV sl. 4 (printed p. 770)",
                verification_level="IMAGE-TRANSLATION",
                note="Same sets as Phaladeepika for the seven planets; nodes not mentioned",
            ),
        ),
        houses={**_COMMON_SIX, MOON: _MOON_PHALADEEPIKA},
    ),
    FavourableReadingDef(
        reading_id=FAV_BRIHAT_JATAKA_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="Brihat Jataka (Sastri) Ch. IX sl. 1-7, from-the-Moon columns",
        verification_level="IMAGE-TRANSLATION",
        references=(
            SourceReference(
                source_id="SRC-BRIHAT-JATAKA-SASTRI",
                locator="Ch. IX sl. 1-7 (printed pp. 198-202)",
                verification_level="IMAGE-TRANSLATION",
                note=(
                    "From-the-Moon columns of each planet's Ashtakavarga list; "
                    "Moon from itself 1,3,5,7,10,11"
                ),
            ),
        ),
        houses={**_COMMON_SIX, MOON: _MOON_BRIHAT_JATAKA},
    ),
    FavourableReadingDef(
        reading_id=FAV_BPHS_DERIVED_ID,
        label=EvidenceLabel.DERIVED_CALCULATION,
        title="BPHS (Kapoor) Ch. 66 v. 16-42, derived from the dot lists",
        verification_level="OCR-TRANSLATION (p. 847 IMAGE-TRANSLATION)",
        references=(
            SourceReference(
                source_id="SRC-BPHS-SANTHANAM-1984",
                locator="Vol II Ch. 66 v. 16-42 (Moon's chart v. 20-22, printed p. 847)",
                verification_level="OCR-TRANSLATION (p. 847 IMAGE-TRANSLATION)",
                note=(
                    "Pandit Ji derivation (complement of the dot houses the Moon contributes); "
                    "not a BPHS statement; Moon from itself 1,3,6,7,9,10,11"
                ),
            ),
        ),
        houses={**_COMMON_SIX, MOON: _MOON_BPHS_DERIVED},
    ),
)

FAVOURABLE_READING_IDS: tuple[str, ...] = tuple(r.reading_id for r in FAVOURABLE_READINGS)


def readings_for(body: CelestialBody) -> tuple[FavourableReadingDef, ...]:
    """The readings that say something about `body` (nodes: Phaladeepika only)."""
    return tuple(r for r in FAVOURABLE_READINGS if body in r.houses)


# --------------------------------------------------------------------------
# Vedha (TR-06): Phaladeepika only
# --------------------------------------------------------------------------

#: favourable house -> Vedha house, per subject planet (Phaladeepika sl. 3-8).
VEDHA_PAIRS: dict[CelestialBody, dict[int, int]] = {
    SUN: {11: 5, 3: 9, 10: 4, 6: 12},
    MOON: {7: 2, 1: 5, 6: 12, 11: 8, 10: 4, 3: 9},
    MARS: {3: 12, 11: 5, 6: 9},
    SATURN: {3: 12, 11: 5, 6: 9},
    MERCURY: {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12},
    JUPITER: {2: 12, 11: 8, 9: 10, 5: 4, 7: 3},
    VENUS: {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 12: 6, 11: 3},
}

#: Planets that do not cause Vedha for the key planet (sl. 3-6, stated in the verses).
VEDHA_EXEMPT: dict[CelestialBody, frozenset[CelestialBody]] = {
    SUN: frozenset({SATURN}),
    SATURN: frozenset({SUN}),
    MOON: frozenset({MERCURY}),
    MERCURY: frozenset({MOON}),
}

VEDHA_REFERENCE = SourceReference(
    source_id="SRC-PHALADEEPIKA-SASTRI",
    locator="Adhyaya XXVI sl. 3-8 (printed pp. 287-288)",
    verification_level="IMAGE-TRANSLATION",
    note=(
        "Single verse-level source; further mentions (Narada and Jataka Parijata cross-references, "
        "Jataka Parijata commentary) are translator notes, not corroboration of the numbers"
    ),
)


# --------------------------------------------------------------------------
# Sade Sati (TR-09): modern tradition
# --------------------------------------------------------------------------

#: Saturn's sign offset from the natal Moon sign (mod 12) -> phase 1..3.
SADE_SATI_PHASE_BY_OFFSET: dict[int, int] = {11: 1, 0: 2, 1: 3}
SADE_SATI_PHASE_NAMES: dict[int, str] = {
    1: "twelfth_from_moon",
    2: "first_from_moon",
    3: "second_from_moon",
}

SADE_SATI_CLASSICAL_STATUS = (
    "not found as a combined unit in the classical texts read (BPHS, Brihat Jataka, Brihat "
    "Samhita, Phaladeepika, Jataka Parijata; keyword probe of OCR, NOT_VERIFIED_BY_OCR); "
    "Saturn's per-house effects are stated individually. A modern-tradition, sign-based construct"
)
