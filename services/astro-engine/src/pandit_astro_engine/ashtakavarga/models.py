"""Typed contracts for the Ashtakavarga engine (Phase 9 WP-A1).

Facts only: a "benefic house" is membership in a source's own printed list,
never a verdict, and no interpretation vocabulary (good/bad/strong/weak)
appears anywhere in this module. Reductions (Trikona Shodhana, Ekadhipatya
Shodhana, Pinda Sadhana) are out of scope for WP-A1 and are not modelled
here.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.ashtakavarga.constants import (
    ASHTAKAVARGA_STANDARDS_VERSION,
    CONTRIBUTOR_ORDER,
    SYSTEM_ID,
    Contributor,
)
from pandit_astro_engine.ashtakavarga.profiles import EvidenceLabel, SourceReference
from pandit_astro_engine.kundli_models import Kundli
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AshtakavargaStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"
    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_PROFILE = "unsupported_profile"
    INTERNAL_ERROR = "internal_error"


class AshtakavargaReason(str, Enum):
    """Machine-readable reason codes. Every non-success status carries one."""

    LAGNA_UNAVAILABLE = "lagna_unavailable"
    NATAL_POSITIONS_INCOMPLETE = "natal_positions_incomplete"
    NON_FINITE_LONGITUDE = "non_finite_longitude"
    UNSUPPORTED_PROFILE = "unsupported_profile"
    INTERNAL_ERROR = "internal_error"


class HouseMark(str, Enum):
    """A contributor's mark on one house of one chart. `EFFECTLESS` occurs
    only under the Brihat Jataka profile (Ch. IX sl. 3: the 10th from the
    Moon in Mars's chart is neither benefic nor malefic)."""

    BENEFIC = "benefic"
    MALEFIC = "malefic"
    EFFECTLESS = "effectless"


_PLANET_TO_CONTRIBUTOR: dict[CelestialBody, Contributor] = {
    CelestialBody.SUN: Contributor.SUN,
    CelestialBody.MOON: Contributor.MOON,
    CelestialBody.MARS: Contributor.MARS,
    CelestialBody.MERCURY: Contributor.MERCURY,
    CelestialBody.JUPITER: Contributor.JUPITER,
    CelestialBody.VENUS: Contributor.VENUS,
    CelestialBody.SATURN: Contributor.SATURN,
}


class NatalPositions(_Model):
    """Sidereal longitudes of the seven classical planets and the
    Ascendant. A partial mapping is accepted (so callers can exercise
    validation paths); `from_kundli` always supplies all eight from a
    Phase 5 Kundli."""

    longitudes: dict[Contributor, float] = Field(default_factory=dict)

    @classmethod
    def from_kundli(cls, kundli: Kundli) -> NatalPositions:
        planets = {p.body: p.longitude for p in kundli.planets}
        longitudes: dict[Contributor, float] = {}
        for body, contributor in _PLANET_TO_CONTRIBUTOR.items():
            if body in planets:
                longitudes[contributor] = planets[body]
        longitudes[Contributor.LAGNA] = kundli.lagna_longitude
        return cls(longitudes=longitudes)

    def all_longitudes(self) -> list[float]:
        return list(self.longitudes.values())


class AshtakavargaRequest(_Model):
    natal: NatalPositions
    profile_id: str


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


class ChartResult(_Model):
    """One contributor's Bhinnashtakavarga chart: 12 signs, each with every
    contributor's mark and the resulting benefic/malefic/effectless counts.
    `sign_marks` is keyed by `Rashi` (absolute sign, not house-from-anything)
    so the chart stands alone without a reference point."""

    chart: Contributor
    marks: dict[Rashi, dict[Contributor, HouseMark]]
    benefic_count: dict[Rashi, int] = Field(
        ..., description="0..8 (0..7 where an effectless mark removes one contributor)."
    )
    malefic_count: dict[Rashi, int]
    effectless_count: dict[Rashi, int]
    total_benefic: int = Field(..., description="Sum of `benefic_count` over all 12 signs.")


class SarvashtakavargaResult(_Model):
    """Per-sign sum of `benefic_count` over the seven planet charts only
    (BPHS's own eighth, Ascendant, chart is never included in Sarva, per
    every source read)."""

    benefic_count: dict[Rashi, int]
    total_benefic: int


class ProfileSummary(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    verification_level: str
    reference: SourceReference
    has_lagna_chart: bool


class AshtakavargaFacts(_Model):
    """The complete Ashtakavarga result for one profile. For any
    non-success status every fact section is absent and `reason_code` says
    why."""

    system_id: str = SYSTEM_ID
    status: AshtakavargaStatus
    reason_code: AshtakavargaReason | None = None
    detail: str | None = None
    standards_version: str = ASHTAKAVARGA_STANDARDS_VERSION
    engine_version: str
    profile: ProfileSummary | None = None
    charts: tuple[ChartResult, ...] = ()
    sarva: SarvashtakavargaResult | None = None
    lagna_chart: ChartResult | None = Field(
        default=None,
        description=(
            "Present only when the profile gives the Ascendant its own chart (the two BPHS "
            "profiles); absent, never synthesized, under Brihat Jataka or Phaladeepika."
        ),
    )
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _status_contract(self) -> AshtakavargaFacts:
        ok = self.status == AshtakavargaStatus.SUCCESS
        if ok and self.reason_code is not None:
            raise ValueError("a successful result must not carry a failure reason code")
        if not ok and self.reason_code is None:
            raise ValueError("every failure must carry a machine-readable reason code")
        if not ok and (self.charts or self.sarva is not None or self.lagna_chart is not None):
            raise ValueError("a failed result must not carry facts")
        return self


#: Stable iteration order re-exported for convenience (evidence, tests).
CONTRIBUTORS_IN_ORDER = CONTRIBUTOR_ORDER
