"""Ashtakavarga methodology profiles (Phase 9 WP-A1; `docs/ASTROLOGY_STANDARDS.md`
v1.7.0, AV-02).

Four profiles, one per printed source reading. None is a default; a caller
must name one explicitly. No profile is called "BPHS" unqualified, because
BPHS's own printed dot grid and printed verse-translation list disagree
with each other on 5 of 56 cells in the same chapter (`constants.py`
`CROSS_TABLE_CONFLICTS`) and there is no basis to prefer one over the other
without Sanskrit review.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.ashtakavarga.constants import (
    BJ_EFFECTLESS_CELLS,
    BJ_TABLE,
    BPHS_GRID_TABLE,
    BPHS_VERSE_TABLE,
    LAGNA_CHART_BPHS,
    PHALADEEPIKA_TABLE,
    Contributor,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """What kind of statement a provenance entry is. Never merged (matches
    the vocabulary used by `pandit_astro_engine.transits.profiles` and
    `pandit_astro_engine.dashas.profiles` -- each phase module keeps its own
    copy of this enum rather than sharing a cross-phase import)."""

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

BRIHAT_JATAKA_ID = "ASHTAKAVARGA_BRIHAT_JATAKA_SASTRI_IX_1_7"
PHALADEEPIKA_ID = "ASHTAKAVARGA_PHALADEEPIKA_SASTRI_XXIII_3_9"
BPHS_GRID_ID = "ASHTAKAVARGA_BPHS_GRID_KAPOOR_66"
BPHS_VERSE_ID = "ASHTAKAVARGA_BPHS_VERSE_KAPOOR_66"

ALL_PROFILE_IDS: tuple[str, ...] = (
    BRIHAT_JATAKA_ID,
    PHALADEEPIKA_ID,
    BPHS_GRID_ID,
    BPHS_VERSE_ID,
)


class AshtakavargaProfileDef(_Model):
    """One source's own reading, in full: its table, whether it gives the
    Ascendant its own eighth chart, its effectless-cell exceptions (Brihat
    Jataka only), and its source reference."""

    profile_id: str
    label: EvidenceLabel
    title: str
    verification_level: str
    reference: SourceReference
    table: dict[Contributor, dict[Contributor, tuple[int, ...]]]
    has_lagna_chart: bool
    lagna_chart: dict[Contributor, tuple[int, ...]] | None
    effectless_cells: dict[tuple[Contributor, Contributor], tuple[int, ...]]

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)


PROFILES: dict[str, AshtakavargaProfileDef] = {
    BRIHAT_JATAKA_ID: AshtakavargaProfileDef(
        profile_id=BRIHAT_JATAKA_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="Brihat Jataka (Varahamihira, Sastri translation) Ch. IX sl. 1-7",
        verification_level="IMAGE-TRANSLATION",
        reference=SourceReference(
            source_id="SRC-BRIHAT-JATAKA-SASTRI",
            locator="Ch. IX sl. 1-7 (printed pp. 198-202)",
            verification_level="IMAGE-TRANSLATION",
            note=(
                "All 56 cells (7 charts x 8 contributors) transcribed directly from the "
                "printed page images; sl. 3 states the 10th house from the Moon is "
                "effectless in Mars's chart (neither benefic nor malefic)"
            ),
        ),
        table=BJ_TABLE,
        has_lagna_chart=False,
        lagna_chart=None,
        effectless_cells=BJ_EFFECTLESS_CELLS,
    ),
    PHALADEEPIKA_ID: AshtakavargaProfileDef(
        profile_id=PHALADEEPIKA_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="Phaladeepika (Mantreswara, Sastri translation) Ch. XXIII sl. 3-9",
        verification_level="IMAGE-TRANSLATION",
        reference=SourceReference(
            source_id="SRC-PHALADEEPIKA-SASTRI",
            locator="Adhyaya XXIII sl. 3-9 (printed pp. 258-261)",
            verification_level="IMAGE-TRANSLATION",
            note=(
                "All 56 cells transcribed from the printed page images (main text only); "
                "two cells carry a translator's footnote naming an alternate reading by "
                "another author (see constants.CROSS_TABLE_CONFLICTS), kept as "
                "translator_note and not merged into this table"
            ),
        ),
        table=PHALADEEPIKA_TABLE,
        has_lagna_chart=False,
        lagna_chart=None,
        effectless_cells={},
    ),
    BPHS_GRID_ID: AshtakavargaProfileDef(
        profile_id=BPHS_GRID_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="BPHS (Vol II Ch. 66, Kapoor translation) printed dot grid",
        verification_level="IMAGE-TRANSLATION",
        reference=SourceReference(
            source_id="SRC-BPHS-SANTHANAM-1984",
            locator=(
                "Vol II Ch. 66 v. 16-42, 65-68 (Kapoor translation), the printed "
                "'Chart showing dots in ... Ashtakavarga' tables (pp. 845-854, 864-865)"
            ),
            verification_level="IMAGE-TRANSLATION",
            note=(
                "Complement of the printed dot houses (source's own note: houses without "
                "dots are auspicious); disagrees with BPHS's own printed verse-translation "
                "list on 5 of 56 cells in the same chapter (see "
                "constants.CROSS_TABLE_CONFLICTS); no correction attempted"
            ),
        ),
        table=BPHS_GRID_TABLE,
        has_lagna_chart=True,
        lagna_chart=LAGNA_CHART_BPHS,
        effectless_cells={},
    ),
    BPHS_VERSE_ID: AshtakavargaProfileDef(
        profile_id=BPHS_VERSE_ID,
        label=EvidenceLabel.SOURCE_SUPPORTED,
        title="BPHS (Vol II Ch. 66, Kapoor translation) printed verse-translation list",
        verification_level="IMAGE-TRANSLATION",
        reference=SourceReference(
            source_id="SRC-BPHS-SANTHANAM-1984",
            locator=(
                "Vol II Ch. 66 v. 16-42, 65-68 (Kapoor translation), the printed "
                "'Thus [contributors], these N in the Kth ...' verse translation "
                "(pp. 845-854, 864-865)"
            ),
            verification_level="IMAGE-TRANSLATION",
            note=(
                "Complement of the printed dot houses named in the verse translation; "
                "disagrees with BPHS's own printed dot grid on 5 of 56 cells in the same "
                "chapter (see constants.CROSS_TABLE_CONFLICTS); no correction attempted"
            ),
        ),
        table=BPHS_VERSE_TABLE,
        has_lagna_chart=True,
        lagna_chart=LAGNA_CHART_BPHS,
        effectless_cells={},
    ),
}
