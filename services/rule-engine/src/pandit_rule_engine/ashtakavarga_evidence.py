"""Ashtakavarga facts as consumed by the rule engine (Phase 9 WP-EB -> Phase 6
contract).

`astro-engine` calculates and owns the Ashtakavarga facts (Phase 9 WP-A1
Bhinna/Sarva, WP-A2 Trikona/Ekadhipatya Shodhana, WP-A3 Pinda Sadhana); the
rule engine only reads them. This module is the adapter: it takes the JSON
form of an astro-engine `AshtakavargaFacts` and, optionally, the JSON form of
an `AshtakavargaReductionFacts` for the *same* profile and natal chart, and
preserves every status, reason code, profile identifier, provenance label and
unresolved conflict verbatim, so a later rule can cite them and a result
stays reproducible.

The rule engine does not import `astro-engine` (facts flow one direction). No
shipped Phase 6 rule reads Ashtakavarga facts yet: this section only makes
them available and reproducible inside the bundle. The records carry
structural facts only (a mark or a count is a number or a label, never a
verdict).

Profile selection (`docs/ASTROLOGY_STANDARDS.md` v1.9.0 AV-14): the caller
selects exactly one of the four WP-A1 profiles per bundle build (there is no
implicit default -- `facts` must itself already carry a `profile_id`, which
is preserved on `AshtakavargaEvidence.profile.profile_id`). A caller wanting
more than one profile's evidence builds more than one bundle; the static
56-cell cross-source conflict register (the astro-engine Ashtakavarga
package's own `CROSS_TABLE_CONFLICTS` constant) is build-time registry data,
not a per-Kundli fact, and is deliberately never copied into a bundle.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.hashing import canonical_json, sha256_hex
from pandit_rule_engine.vocab import Body, Sign

_USABLE = "success"


class AshtakavargaChart(str, Enum):
    """The eight Ashtakavarga contributors/charts (astro-engine's
    `Contributor`): the seven classical grahas plus the Ascendant. Kept as
    its own vocabulary here (not reused from `Body`) because, unlike every
    other rule-engine evidence section, the Ascendant is itself a valid
    "chart" identifier in this system (BPHS's own eighth Bhinnashtakavarga
    chart), which `Body` has no member for."""

    SUN = "sun"
    MOON = "moon"
    MARS = "mars"
    MERCURY = "mercury"
    JUPITER = "jupiter"
    VENUS = "venus"
    SATURN = "saturn"
    LAGNA = "lagna"


class _Record(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class SourceReferenceRecord(_Record):
    source_id: str
    locator: str
    verification_level: str
    note: str = ""


class ProfileRecord(_Record):
    profile_id: str
    label: str
    title: str
    verification_level: str
    has_lagna_chart: bool
    reference: SourceReferenceRecord


class SignCountRecord(_Record):
    sign: Sign
    benefic_count: int
    malefic_count: int
    effectless_count: int


class SignValueRecord(_Record):
    sign: Sign
    value: int


class ContributorMarkRecord(_Record):
    """One (sign, contributor) cell of a Bhinnashtakavarga chart -- the
    per-planet/per-source detail `docs/ASTROLOGY_STANDARDS.md` §Ashtakavarga
    standards keeps alongside the per-sign totals."""

    sign: Sign
    contributor: AshtakavargaChart
    mark: str  # "benefic" | "malefic" | "effectless"


class BhinnaChartRecord(_Record):
    chart: AshtakavargaChart
    sign_counts: tuple[SignCountRecord, ...]
    contributor_marks: tuple[ContributorMarkRecord, ...]
    total_benefic: int


class SarvaRecord(_Record):
    per_sign_benefic_count: tuple[SignValueRecord, ...]
    total_benefic: int
    #: WP-A1: Sarvashtakavarga is always the unreduced sum of the seven
    #: planet charts; the WP-A2 Trikona/Ekadhipatya reductions are never
    #: applied to it by any source read (`docs/ASTROLOGY_STANDARDS.md`
    #: v1.8.0, Ch. 72 finding).
    reduction_note: str = (
        "unreduced 7-planet-chart sum; WP-A2 Trikona/Ekadhipatya Shodhana is never applied "
        "to Sarvashtakavarga (no source read defines a Sarva-specific reduction)"
    )


class EkadhipatyaConflictRecord(_Record):
    """Both of BPHS's own printed readings for the unresolved
    "exactly one sign occupied, equal Trikona-corrected values" case,
    preserved verbatim -- see `docs/ASTROLOGY_STANDARDS.md` v1.8.0 AV-10.
    Neither reading is chosen here or anywhere in this adapter."""

    occupied_sign: Sign
    empty_sign: Sign
    shared_value: int
    reading_a_occupied_value: int
    reading_b_occupied_value: int
    source_note: str


class ChartReductionRecord(_Record):
    """One chart's Trikona/Ekadhipatya Shodhana result. `status` is
    `NOT_EVALUABLE` only when at least one lordship pair hit the unresolved
    equal-value/one-occupied case (`ekadhipatya_conflicts` non-empty); in
    that case `ekadhipatya_corrected` is always absent -- never a partial
    12-sign map -- matching the astro-engine contract exactly."""

    chart: AshtakavargaChart
    trikona_corrected: tuple[SignValueRecord, ...]
    status: str
    reason_code: str | None = None
    ekadhipatya_corrected: tuple[SignValueRecord, ...] | None = None
    ekadhipatya_conflicts: tuple[EkadhipatyaConflictRecord, ...] = ()

    @model_validator(mode="after")
    def _contract(self) -> ChartReductionRecord:
        ok = self.status == _USABLE
        if ok and (self.ekadhipatya_corrected is None or self.ekadhipatya_conflicts):
            raise ValueError("a resolved chart reduction must carry a full map, no conflicts")
        if not ok and (self.ekadhipatya_corrected is not None or not self.ekadhipatya_conflicts):
            raise ValueError("an unresolved chart reduction must withhold its map")
        return self


class GrahaPindaContributionRecord(_Record):
    sign: Sign
    ekadhipatya_value: int
    occupying_contributor: Body | None = None
    multiplier: int | None = None
    product: int | None = None
    status: str = _USABLE
    reason_code: str | None = None


class PindaRecord(_Record):
    """Rasi, Graha and Yoga Pinda for one chart. `status` covers the whole
    record (withheld entirely -- `rasi_pinda` included -- when the chart's
    own Ekadhipatya reduction was itself unresolved); `graha_pinda_status`
    is a narrower, independent status for Graha/Yoga Pinda alone (the
    Mercury-multiplier or multi-occupant conflicts), which can be
    `NOT_EVALUABLE` even when `status` is resolved and `rasi_pinda` is
    present -- see `docs/ASTROLOGY_STANDARDS.md` v1.8.0 AV-11/AV-12."""

    chart: AshtakavargaChart
    status: str
    reason_code: str | None = None
    rasi_pinda: int | None = None
    graha_pinda_status: str | None = None
    graha_pinda_reason: str | None = None
    graha_pinda: int | None = None
    yoga_pinda: int | None = None
    graha_contributions: tuple[GrahaPindaContributionRecord, ...] = ()

    @model_validator(mode="after")
    def _contract(self) -> PindaRecord:
        ok = self.status == _USABLE
        if not ok and self.rasi_pinda is not None:
            raise ValueError("an unresolved Pinda result must carry no Pinda facts")
        return self


class AshtakavargaEvidence(_Record):
    """One Ashtakavarga calculation, as the evidence bundle records it.
    WP-A1 (`charts`, `sarva`, `lagna_chart`) is always attempted; WP-A2/A3
    (`reductions`, `pinda`, `lagna_reduction`, `lagna_pinda`) are populated
    only when the caller supplied reduction facts alongside the base facts
    (see `ashtakavarga_evidence_from_facts`'s `reduction_facts` parameter) --
    reduction computation is opt-in per bundle build, never automatic."""

    system_id: str
    status: str
    reason_code: str | None = None
    profile: ProfileRecord | None = None
    charts: tuple[BhinnaChartRecord, ...] = ()
    sarva: SarvaRecord | None = None
    lagna_chart: BhinnaChartRecord | None = None
    reductions: tuple[ChartReductionRecord, ...] = ()
    lagna_reduction: ChartReductionRecord | None = None
    pinda: tuple[PindaRecord, ...] = ()
    lagna_pinda: PindaRecord | None = None
    #: SHA-256 of the canonical JSON of the whole facts object(s) actually
    #: supplied, so any field not copied into a record here still changes it.
    facts_hash: str

    @model_validator(mode="after")
    def _status_contract(self) -> AshtakavargaEvidence:
        ok = self.status == _USABLE
        if ok and self.reason_code is not None:
            raise ValueError("a successful result must not carry a reason_code")
        if not ok and self.reason_code is None:
            raise ValueError("a non-success result must carry a reason_code")
        if not ok and (self.profile is not None or self.charts or self.sarva is not None):
            raise ValueError("a failed result must not carry facts")
        return self


def _bhinna_chart(raw: Mapping[str, Any]) -> BhinnaChartRecord:
    benefic = raw["benefic_count"]
    malefic = raw["malefic_count"]
    effectless = raw["effectless_count"]
    counts = tuple(
        SignCountRecord(
            sign=sign,
            benefic_count=benefic[sign],
            malefic_count=malefic[sign],
            effectless_count=effectless[sign],
        )
        for sign in benefic
    )
    contributor_marks = tuple(
        ContributorMarkRecord(sign=sign, contributor=contributor, mark=mark)
        for sign, per_contributor in raw["marks"].items()
        for contributor, mark in per_contributor.items()
    )
    return BhinnaChartRecord(
        chart=raw["chart"],
        sign_counts=counts,
        contributor_marks=contributor_marks,
        total_benefic=raw["total_benefic"],
    )


def _sign_values(raw: Mapping[str, int]) -> tuple[SignValueRecord, ...]:
    return tuple(SignValueRecord(sign=Sign(sign), value=value) for sign, value in raw.items())


def _reduction(raw: Mapping[str, Any]) -> ChartReductionRecord:
    eka = raw.get("ekadhipatya_corrected")
    return ChartReductionRecord(
        chart=raw["chart"],
        trikona_corrected=_sign_values(raw["trikona_corrected"]),
        status=raw["status"],
        reason_code=raw.get("reason_code"),
        ekadhipatya_corrected=(_sign_values(eka) if eka is not None else None),
        ekadhipatya_conflicts=tuple(
            EkadhipatyaConflictRecord(**conflict)
            for conflict in raw.get("ekadhipatya_conflicts", ())
        ),
    )


def _pinda(raw: Mapping[str, Any]) -> PindaRecord:
    return PindaRecord(
        chart=raw["chart"],
        status=raw["status"],
        reason_code=raw.get("reason_code"),
        rasi_pinda=raw.get("rasi_pinda"),
        graha_pinda_status=raw.get("graha_pinda_status"),
        graha_pinda_reason=raw.get("graha_pinda_reason"),
        graha_pinda=raw.get("graha_pinda"),
        yoga_pinda=raw.get("yoga_pinda"),
        graha_contributions=tuple(
            GrahaPindaContributionRecord(**contribution)
            for contribution in raw.get("graha_contributions", ())
        ),
    )


def ashtakavarga_evidence_from_facts(
    facts: Mapping[str, Any], reduction_facts: Mapping[str, Any] | None = None
) -> AshtakavargaEvidence:
    """Build `AshtakavargaEvidence` from an astro-engine `AshtakavargaFacts`
    in JSON form and, optionally, an `AshtakavargaReductionFacts` (same
    profile, same natal chart) for the same calculation."""
    if not isinstance(facts, Mapping):
        raise FactsError("ashtakavarga: expected an object")
    for key in ("system_id", "status"):
        if key not in facts:
            raise FactsError(f"ashtakavarga: missing required field {key!r}")
    status = facts["status"]
    if status != _USABLE:
        if facts.get("reason_code") is None:
            raise FactsError("ashtakavarga: a non-success result must carry a reason_code")
    else:
        if facts.get("reason_code") is not None:
            raise FactsError("ashtakavarga: a successful result must not carry a reason_code")
        if facts.get("profile") is None or facts.get("sarva") is None:
            raise FactsError("ashtakavarga: a successful result must carry profile and sarva")

    if reduction_facts is not None:
        if not isinstance(reduction_facts, Mapping):
            raise FactsError("ashtakavarga: reduction_facts must be an object")
        for key in ("system_id", "status"):
            if key not in reduction_facts:
                raise FactsError(f"ashtakavarga: reduction_facts missing {key!r}")

    # Every remaining step either reads a required key from an upstream JSON
    # object (KeyError on a missing one) or constructs a validated record
    # (ValidationError/ValueError on a malformed one) -- all three become one
    # FactsError, exactly like the single `model_validate` call the simpler
    # (WP-A1-only) evidence adapters use.
    try:
        profile = None
        charts: tuple[BhinnaChartRecord, ...] = ()
        sarva = None
        lagna_chart = None
        if status == _USABLE:
            profile_raw = facts["profile"]
            profile = ProfileRecord(
                profile_id=profile_raw["profile_id"],
                label=profile_raw["label"],
                title=profile_raw["title"],
                verification_level=profile_raw["verification_level"],
                has_lagna_chart=profile_raw["has_lagna_chart"],
                reference=SourceReferenceRecord(**profile_raw["reference"]),
            )
            charts = tuple(_bhinna_chart(c) for c in facts["charts"])
            sarva_raw = facts["sarva"]
            sarva = SarvaRecord(
                per_sign_benefic_count=_sign_values(sarva_raw["benefic_count"]),
                total_benefic=sarva_raw["total_benefic"],
            )
            if facts.get("lagna_chart") is not None:
                lagna_chart = _bhinna_chart(facts["lagna_chart"])

        reductions: tuple[ChartReductionRecord, ...] = ()
        lagna_reduction = None
        pinda: tuple[PindaRecord, ...] = ()
        lagna_pinda = None
        combined_hash_input: dict[str, Any] = {"facts": dict(facts)}

        if reduction_facts is not None:
            combined_hash_input["reduction_facts"] = dict(reduction_facts)
            if reduction_facts["status"] == _USABLE:
                reductions = tuple(_reduction(c) for c in reduction_facts.get("charts", ()))
                pinda = tuple(_pinda(p) for p in reduction_facts.get("pinda", ()))
                if reduction_facts.get("lagna_chart") is not None:
                    lagna_reduction = _reduction(reduction_facts["lagna_chart"])
                if reduction_facts.get("lagna_pinda") is not None:
                    lagna_pinda = _pinda(reduction_facts["lagna_pinda"])

        return AshtakavargaEvidence(
            system_id=facts["system_id"],
            status=status,
            reason_code=facts.get("reason_code"),
            profile=profile,
            charts=charts,
            sarva=sarva,
            lagna_chart=lagna_chart,
            reductions=reductions,
            lagna_reduction=lagna_reduction,
            pinda=pinda,
            lagna_pinda=lagna_pinda,
            facts_hash=sha256_hex(canonical_json(combined_hash_input)),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"ashtakavarga: malformed facts ({exc})") from exc
