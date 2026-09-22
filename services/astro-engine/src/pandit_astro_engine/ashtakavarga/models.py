"""Typed contracts for the Ashtakavarga engine (Phase 9 WP-A1, extended by
WP-A2/A3).

Facts only: a "benefic house" is membership in a source's own printed list,
never a verdict, and no interpretation vocabulary (good/bad/strong/weak)
appears anywhere in this module. WP-A2 (Trikona/Ekadhipatya Shodhana) and
WP-A3 (Pinda Sadhana) are modelled as an additive, separate request/response
pair (`AshtakavargaReductionRequest` / `AshtakavargaReductionFacts`) so the
WP-A1 `AshtakavargaRequest` / `AshtakavargaFacts` contract is completely
unchanged -- existing callers of `calculate()` see no difference at all.
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
    #: WP-A2/A3 (`AshtakavargaReductionFacts` only)
    REDUCTION_UNSUPPORTED_FOR_PROFILE = "reduction_unsupported_for_profile"
    NODE_POSITIONS_REQUIRED = "node_positions_required"
    #: Ch. 68's own printed "abstract illustration" table (p. 876) gives two
    #: different results for "exactly one sign occupied, both Trikona-corrected
    #: values equal": the Capricorn/Aquarius pair keeps the occupied sign
    #: unchanged (matching rule 6's literal wording); the Gemini/Virgo pair,
    #: under the identical shape, prints as if both signs were zeroed. Neither
    #: reading is chosen; see `EkadhipatyaConflict`.
    EKADHIPATYA_EQUAL_VALUE_CONFLICT = "ekadhipatya_equal_value_conflict"


class GrahaPindaStatus(str, Enum):
    """WP-A3: whether a chart's Graha Pinda (and therefore its Yoga Pinda)
    could be computed at all. Rasi Pinda has no such ambiguity and is
    always available whenever the chart's reduction succeeded."""

    AVAILABLE = "available"
    NOT_EVALUABLE = "not_evaluable"


class GrahaPindaReason(str, Enum):
    #: Ch. 69's verse and its own printed table disagree on Mercury's
    #: multiplier (5 vs 6) and no worked example arbitrates; a sign occupied
    #: solely by Mercury makes the whole chart's Graha/Yoga Pinda
    #: NOT_EVALUABLE rather than silently picking one value.
    MERCURY_MULTIPLIER_CONFLICT = "mercury_multiplier_conflict"
    #: No source read states what happens when a sign is occupied by more
    #: than one classical (non-node) planet at once for Graha Pinda
    #: purposes; not inferred.
    MULTIPLE_OCCUPANTS_UNSUPPORTED = "multiple_occupants_unsupported"


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
    Phase 5 Kundli.

    `rahu_longitude` / `ketu_longitude` are additive and optional (WP-A1
    never used them -- Rahu/Ketu are not Ashtakavarga contributors). WP-A2's
    Ekadhipatya Shodhana needs them only to test sign *occupancy* (Ch. 68's
    own worked example treats a sign occupied solely by Ketu as "with a
    planet"); they are never used as bindu contributors."""

    longitudes: dict[Contributor, float] = Field(default_factory=dict)
    rahu_longitude: float | None = None
    ketu_longitude: float | None = None

    @classmethod
    def from_kundli(cls, kundli: Kundli) -> NatalPositions:
        planets = {p.body: p.longitude for p in kundli.planets}
        longitudes: dict[Contributor, float] = {}
        for body, contributor in _PLANET_TO_CONTRIBUTOR.items():
            if body in planets:
                longitudes[contributor] = planets[body]
        longitudes[Contributor.LAGNA] = kundli.lagna_longitude
        return cls(
            longitudes=longitudes,
            rahu_longitude=planets.get(CelestialBody.RAHU),
            ketu_longitude=planets.get(CelestialBody.KETU),
        )

    def all_longitudes(self) -> list[float]:
        values = list(self.longitudes.values())
        values.extend(v for v in (self.rahu_longitude, self.ketu_longitude) if v is not None)
        return values


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


# --------------------------------------------------------------------------
# WP-A2 / WP-A3: reductions and Pinda (BPHS profiles only; additive, separate
# from the WP-A1 request/response pair above)
# --------------------------------------------------------------------------


class EkadhipatyaConflict(_Model):
    """One lordship pair where Ch. 68's own printed table gives two
    different readings for the same rule shape ("exactly one sign occupied,
    both Trikona-corrected values equal") -- both preserved verbatim, no
    winner chosen (docs/ASTROLOGY_STANDARDS.md v1.8.0 AV-10).

    `reading_a` (Capricorn/Aquarius pair, Ch. 68 p. 876): the occupied sign
    keeps `shared_value`; the empty sign becomes 0. Matches rule 6's literal
    English ("the number of the *latter* [without-planet sign] should be
    reduced to zero").
    `reading_b` (Gemini/Virgo pair, same table, same page): the occupied
    sign is *also* reduced to 0, contradicting reading_a under what should
    be the identical rule."""

    occupied_sign: Rashi
    empty_sign: Rashi
    shared_value: int = Field(..., description="The common Trikona-corrected value of both signs.")
    reading_a_occupied_value: int = Field(
        ...,
        description=(
            "Capricorn/Aquarius reading (Ch. 68 p. 876): occupied sign unchanged "
            "(equals shared_value); matches rule 6's literal wording."
        ),
    )
    reading_b_occupied_value: int = Field(
        default=0,
        description=(
            "Gemini/Virgo reading (Ch. 68 p. 876, same table): occupied sign also "
            "zeroed; contradicts reading_a under the identical rule shape."
        ),
    )
    source_note: str = (
        "BPHS Ch. 68 'An imaginary illustration' (printed p. 876), IMAGE-TRANSLATION; "
        "recorded as an unresolved internal print inconsistency, research/ASTROLOGY_SOURCES.md "
        "section 6.5 Group 11."
    )


class ChartReduction(_Model):
    """One chart's Trikona- and Ekadhipatya-corrected values (docs
    AV-09/AV-10). `ekadhipatya_corrected` and `status` cover the whole
    chart: if even one lordship pair hits the unresolved equal-value/
    one-occupied case (`EkadhipatyaConflict`), the entire chart's
    Ekadhipatya-corrected map is withheld (`None`) -- a partial map that
    silently omitted the disputed signs would still let an unreviewed
    caller sum the other 10 signs and call it a total, which this
    prevents. `trikona_corrected` has no such ambiguity and is always
    present."""

    chart: Contributor
    trikona_corrected: dict[Rashi, int]
    status: AshtakavargaStatus
    reason_code: AshtakavargaReason | None = None
    ekadhipatya_corrected: dict[Rashi, int] | None = None
    ekadhipatya_conflicts: tuple[EkadhipatyaConflict, ...] = ()

    @model_validator(mode="after")
    def _status_contract(self) -> ChartReduction:
        ok = self.status == AshtakavargaStatus.SUCCESS
        if ok and self.reason_code is not None:
            raise ValueError("a resolved chart reduction must not carry a reason code")
        if not ok and self.reason_code is None:
            raise ValueError("an unresolved chart reduction must carry a reason code")
        if ok and (self.ekadhipatya_corrected is None or self.ekadhipatya_conflicts):
            raise ValueError(
                "a resolved chart reduction must carry ekadhipatya_corrected and no conflicts"
            )
        if not ok and (self.ekadhipatya_corrected is not None or not self.ekadhipatya_conflicts):
            raise ValueError(
                "an unresolved chart reduction must withhold ekadhipatya_corrected "
                "and list its conflicts"
            )
        return self


class GrahaPindaContribution(_Model):
    """One sign's contribution to Graha Pinda -- kept individually so a
    result is explainable (docs AV-11): which sign, whose multiplier, and
    the product, or why it has none."""

    sign: Rashi
    ekadhipatya_value: int
    occupying_contributor: Contributor | None = Field(
        default=None,
        description="None if the sign is unoccupied, or occupied only by Rahu/Ketu.",
    )
    multiplier: int | None = None
    product: int | None = None
    status: GrahaPindaStatus = GrahaPindaStatus.AVAILABLE
    reason_code: GrahaPindaReason | None = None


class PindaResult(_Model):
    """Rasi Pinda, Graha Pinda and Yoga Pinda for one chart (docs AV-11 to
    AV-13).

    `status` covers the whole result: `NOT_EVALUABLE` (with `reason_code`
    `ekadhipatya_equal_value_conflict`) when the chart's own Ekadhipatya
    reduction was itself unresolved, in which case `rasi_pinda` is withheld
    too (it sums all 12 signs, so an unresolved sign makes the whole total
    unusable, not just the disputed sign's own contribution -- see
    `docs/ASTROLOGY_STANDARDS.md` v1.8.0 AV-10/AV-13).

    When `status` is `SUCCESS`, `rasi_pinda` is always present; Graha (and
    therefore Yoga) Pinda can independently be `NOT_EVALUABLE` for a reason
    specific to Graha Pinda alone (the unresolved Mercury multiplier, or an
    unsupported multi-occupant sign) -- `graha_pinda_status` covers that
    narrower case, orthogonal to `status`."""

    chart: Contributor
    status: AshtakavargaStatus
    reason_code: AshtakavargaReason | None = None
    rasi_pinda: int | None = None
    graha_pinda_status: GrahaPindaStatus | None = None
    graha_pinda_reason: GrahaPindaReason | None = None
    graha_pinda: int | None = None
    graha_contributions: tuple[GrahaPindaContribution, ...] = ()
    yoga_pinda: int | None = Field(
        default=None, description="rasi_pinda + graha_pinda; None unless graha_pinda is available."
    )

    @model_validator(mode="after")
    def _status_contract(self) -> PindaResult:
        ok = self.status == AshtakavargaStatus.SUCCESS
        if ok and self.reason_code is not None:
            raise ValueError("a resolved Pinda result must not carry a reason code")
        if not ok and self.reason_code is None:
            raise ValueError("an unresolved Pinda result must carry a reason code")
        if not ok:
            if (
                self.rasi_pinda is not None
                or self.graha_pinda_status is not None
                or self.graha_pinda is not None
                or self.yoga_pinda is not None
                or self.graha_contributions
            ):
                raise ValueError("an unresolved Pinda result must carry no Pinda facts at all")
            return self
        if self.rasi_pinda is None or self.graha_pinda_status is None:
            raise ValueError("a resolved Pinda result must carry rasi_pinda and graha_pinda_status")
        available = self.graha_pinda_status == GrahaPindaStatus.AVAILABLE
        if available and self.graha_pinda_reason is not None:
            raise ValueError("an available Graha Pinda must not carry a reason code")
        if not available and self.graha_pinda_reason is None:
            raise ValueError("a not-evaluable Graha Pinda must carry a reason code")
        if available and (self.graha_pinda is None or self.yoga_pinda is None):
            raise ValueError("an available Graha Pinda must carry graha_pinda and yoga_pinda")
        if not available and (self.graha_pinda is not None or self.yoga_pinda is not None):
            raise ValueError("a not-evaluable Graha Pinda must not carry graha_pinda or yoga_pinda")
        if available and self.yoga_pinda != self.rasi_pinda + (self.graha_pinda or 0):
            raise ValueError("yoga_pinda must equal rasi_pinda + graha_pinda")
        return self


class AshtakavargaReductionRequest(_Model):
    """WP-A2/A3 request. Reductions are defined only under the two BPHS
    profiles (`docs/ASTROLOGY_STANDARDS.md` v1.8.0 AV-09) -- Brihat Jataka
    and Phaladeepika return `NOT_EVALUABLE(reduction_unsupported_for_profile)`,
    never a silently computed result."""

    natal: NatalPositions
    profile_id: str


class AshtakavargaReductionFacts(_Model):
    """The complete WP-A2/A3 result. For any non-success status every fact
    section is absent and `reason_code` says why."""

    system_id: str = SYSTEM_ID
    status: AshtakavargaStatus
    reason_code: AshtakavargaReason | None = None
    detail: str | None = None
    standards_version: str = ASHTAKAVARGA_STANDARDS_VERSION
    engine_version: str
    profile: ProfileSummary | None = None
    charts: tuple[ChartReduction, ...] = ()
    lagna_chart: ChartReduction | None = Field(
        default=None,
        description="Present only under the two BPHS profiles.",
    )
    pinda: tuple[PindaResult, ...] = ()
    lagna_pinda: PindaResult | None = None
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _status_contract(self) -> AshtakavargaReductionFacts:
        ok = self.status == AshtakavargaStatus.SUCCESS
        if ok and self.reason_code is not None:
            raise ValueError("a successful result must not carry a failure reason code")
        if not ok and self.reason_code is None:
            raise ValueError("every failure must carry a machine-readable reason code")
        if not ok and (self.charts or self.pinda or self.lagna_chart is not None):
            raise ValueError("a failed result must not carry facts")
        return self


#: Stable iteration order re-exported for convenience (evidence, tests).
CONTRIBUTORS_IN_ORDER = CONTRIBUTOR_ORDER
