"""Shadbala method policy (owner decision of 2026-09-25;
`docs/ASTROLOGY_STANDARDS.md` v1.22.0, SM-01 to SM-12).

    ShadbalaMethodRequest -> ShadbalaMethodService.calculate -> ShadbalaMethodResult

Two methods, never combined:

* `MODERN_RAMAN` -- the default method for user-facing Shadbala. It runs the
  profile `SHADBALA_RAMAN_GRAHA_BHAVA_BALAS` (SR-01 to SR-24), which follows
  one modern manual (B. V. Raman, *Graha and Bhava Balas*). Its totals are
  that manual's totals, not a universally authoritative Shadbala.
* `BPHS_VERSE_REFERENCE` -- the verse-literal reference method, profile
  `SHADBALA_BPHS_SANTHANAM_27_VERSE` (SB-01 to SB-20). It still produces no
  total.

Raman's book contradicts itself twice (the Drekkana order, SR-06; the Moon's
benefic rule for Paksha, SR-09). Each is a methodology choice the caller may
configure explicitly. A choice that is not configured is never settled by a
hidden default: the method runs every option of the unconfigured choices,
keeps a component only where every option gives the same value, and marks
the others `NOT_EVALUABLE(methodology_reading_not_selected)`, so a total is
produced only when the unconfigured choices do not change it. The totals
under every option are returned as alternatives, so the contradiction stays
visible and reproducible.

This module selects and describes a method; it computes no component itself
and never places a component of one method into a result of the other.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_astro_engine._version import __version__
from pandit_astro_engine.models import (
    CelestialBody,
    LocalDateTimeInput,
    Location,
    NodeConvention,
)
from pandit_astro_engine.shadbala.constants import SHADBALA_SYSTEM_ID
from pandit_astro_engine.shadbala.models import (
    ComponentProvenance,
    ComponentResult,
    ComponentStatus,
    PlanetShadbala,
    RamanShadbalaFacts,
    RamanShadbalaRequest,
    ShadbalaFacts,
    ShadbalaReason,
    ShadbalaRequest,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala.profiles import (
    PROFILE_ID,
    RAMAN_PROFILE_ID,
    Component,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.shadbala.raman import DrekkanaReading, MoonPakshaReading
from pandit_astro_engine.shadbala.raman_service import RamanShadbalaService, _assemble
from pandit_astro_engine.shadbala.service import LEAF_COMPONENTS, ShadbalaService

SHADBALA_METHOD_STANDARDS_VERSION = "1.22.0"

#: Two component values are "the same" across readings when they differ by
#: less than this many Virupas (floating-point noise only; engineering tag).
SAME_VALUE_TOLERANCE_VIRUPAS = 1e-9

_RunKey = tuple[DrekkanaReading, MoonPakshaReading]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ShadbalaMethod(str, Enum):
    MODERN_RAMAN = "MODERN_RAMAN"
    BPHS_VERSE_REFERENCE = "BPHS_VERSE_REFERENCE"


#: The method used for user-facing Shadbala (owner decision, SM-02).
DEFAULT_USER_FACING_METHOD = ShadbalaMethod.MODERN_RAMAN

#: Method versions. A method version changes whenever the method's formulas,
#: choices or result contract change (SM-11).
METHOD_VERSION: dict[ShadbalaMethod, str] = {
    ShadbalaMethod.MODERN_RAMAN: "1.0.0",
    ShadbalaMethod.BPHS_VERSE_REFERENCE: "1.0.0",
}

METHOD_PROFILE_ID: dict[ShadbalaMethod, str] = {
    ShadbalaMethod.MODERN_RAMAN: RAMAN_PROFILE_ID,
    ShadbalaMethod.BPHS_VERSE_REFERENCE: PROFILE_ID,
}


class EvidenceConfidence(str, Enum):
    """The owner's scale: HIGH = read directly in the cited source and
    reproduced; MEDIUM = credible but not verified at that level; LOW =
    conflicting or weak."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TotalStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class ChoiceSelection(str, Enum):
    CALLER_CONFIGURED = "caller_configured"
    NOT_SELECTED = "not_selected"


class MethodAssumption(_Model):
    assumption_id: str
    statement: str
    evidence_label: EvidenceLabel


class MethodologyChoice(_Model):
    choice_id: str
    statement: str
    options: tuple[str, ...]
    selection: ChoiceSelection
    selected: str | None = None
    #: Whether the options give different component values for this chart;
    #: None when the choice was configured (the other options are not run).
    material_for_this_chart: bool | None = None
    affected: tuple[tuple[CelestialBody, Component], ...] = ()
    confidence: EvidenceConfidence
    reference: SourceReference


class ReadingAlternative(_Model):
    """Totals under one combination of Raman's readings."""

    drekkana_reading: DrekkanaReading
    moon_paksha_reading: MoonPakshaReading
    totals_in_rupas: tuple[tuple[CelestialBody, float | None], ...]


class NotEvaluableComponent(_Model):
    body: CelestialBody
    component: Component
    reason: ShadbalaReason
    detail: str | None = None


class PlanetTotal(_Model):
    body: CelestialBody
    status: TotalStatus
    total_rupas: float | None = None
    missing_components: tuple[Component, ...] = ()


class ShadbalaMethodRequest(_Model):
    """`drekkana_reading` and `moon_paksha_reading` belong to MODERN_RAMAN
    only; left unset, the choice is reported as not selected (never
    defaulted)."""

    method: ShadbalaMethod
    local_datetime: LocalDateTimeInput
    location: Location
    time_precision: ShadbalaTimePrecision
    drekkana_reading: DrekkanaReading | None = None
    moon_paksha_reading: MoonPakshaReading | None = None
    node_convention: NodeConvention = NodeConvention.MEAN
    allow_moshier_fallback: bool = True

    @model_validator(mode="after")
    def _readings_only_for_raman(self) -> ShadbalaMethodRequest:
        if self.method is ShadbalaMethod.BPHS_VERSE_REFERENCE and (
            self.drekkana_reading is not None or self.moon_paksha_reading is not None
        ):
            raise ValueError(
                "drekkana_reading and moon_paksha_reading belong to MODERN_RAMAN; "
                "BPHS_VERSE_REFERENCE has no such choice"
            )
        return self


class ShadbalaMethodResult(_Model):
    system: str
    method: ShadbalaMethod
    method_version: str
    is_default_user_facing_method: bool
    profile_id: str
    standards_version: str
    engine_version: str
    method_produces_total: bool
    source_confidence: EvidenceConfidence
    sources: tuple[SourceReference, ...]
    provenance: tuple[ComponentProvenance, ...]
    authority_note: str
    assumptions: tuple[MethodAssumption, ...]
    methodology_choices: tuple[MethodologyChoice, ...]
    unresolved_choices: tuple[str, ...]
    time_precision: ShadbalaTimePrecision
    planets: tuple[PlanetShadbala, ...]
    totals: tuple[PlanetTotal, ...]
    total_status: TotalStatus
    not_evaluable_components: tuple[NotEvaluableComponent, ...]
    alternatives: tuple[ReadingAlternative, ...] = ()
    #: The underlying profile result; None only when a MODERN_RAMAN reading
    #: was not configured (the planets above are then the agreement view).
    facts: RamanShadbalaFacts | ShadbalaFacts | None = None
    warnings: tuple[str, ...] = ()


_RAMAN_SRC = "SRC-RAMAN-GRAHA-BHAVA-BALAS"

_AUTHORITY_NOTE: dict[ShadbalaMethod, str] = {
    ShadbalaMethod.MODERN_RAMAN: (
        "Totals follow one modern manual (B. V. Raman, Graha and Bhava Balas) as "
        "implemented and checked on its worked example; they are not a universally "
        "authoritative Shadbala, and other manuals and the BPHS verses differ in places."
    ),
    ShadbalaMethod.BPHS_VERSE_REFERENCE: (
        "Verse-literal reference reading of BPHS Ch. 27 (Santhanam translation, OCR level); "
        "components whose method is not fixed by the verses are not evaluable, so no "
        "Shadbala total is produced."
    ),
}

_SOURCE_CONFIDENCE: dict[ShadbalaMethod, EvidenceConfidence] = {
    # Formulas read at page-image level and reproduced on the printed example.
    ShadbalaMethod.MODERN_RAMAN: EvidenceConfidence.HIGH,
    # Verses read in OCR of an English translation.
    ShadbalaMethod.BPHS_VERSE_REFERENCE: EvidenceConfidence.MEDIUM,
}

_EC = EvidenceLabel.ENGINEERING_CONVENTION
_ASSUMPTIONS: dict[ShadbalaMethod, tuple[MethodAssumption, ...]] = {
    ShadbalaMethod.MODERN_RAMAN: (
        MethodAssumption(
            assumption_id="SM-A1",
            statement="Positions, Lagna and vargas come from the Phase 5 Kundli "
            "(Lahiri ayanamsa, whole-sign houses); Raman used his own ayanamsa.",
            evidence_label=_EC,
        ),
        MethodAssumption(
            assumption_id="SM-A2",
            statement="Cheshta Bala is computed in the frame of Raman's mean-motion tables "
            "(Raman ayanamsa), extrapolated only for the years 1800-2100.",
            evidence_label=_EC,
        ),
        MethodAssumption(
            assumption_id="SM-A3",
            statement="Ayana Bala uses the tropical longitude reconstructed as the Lahiri "
            "longitude plus the Lahiri ayanamsa.",
            evidence_label=_EC,
        ),
        MethodAssumption(
            assumption_id="SM-A4",
            statement="The birth time is exact; with an unknown time only Naisargika Bala is "
            "evaluated and no total is produced.",
            evidence_label=_EC,
        ),
    ),
    ShadbalaMethod.BPHS_VERSE_REFERENCE: (
        MethodAssumption(
            assumption_id="SM-B1",
            statement="Positions, Lagna and vargas come from the Phase 5 Kundli "
            "(Lahiri ayanamsa, whole-sign houses).",
            evidence_label=_EC,
        ),
        MethodAssumption(
            assumption_id="SM-B2",
            statement="Only the translated verses are followed; translator's notes are "
            "not used to fill a component.",
            evidence_label=_EC,
        ),
    ),
}

_DREKKANA_REF = SourceReference(
    source_id=_RAMAN_SRC,
    locator="Art. 36 versus Example 12",
    verification_level="IMAGE-ORIGINAL-ENGLISH",
    note="text: neuter middle, female last; worked example: female second",
)
_MOON_REF = SourceReference(
    source_id=_RAMAN_SRC,
    locator="Art. 53",
    verification_level="IMAGE-ORIGINAL-ENGLISH",
    note="'increasing Moon' versus '8th day of the bright half to 8th day of the dark half'",
)


class ShadbalaMethodService:
    """Stateless facade selecting exactly one Shadbala method."""

    def __init__(self, ephemeris_path: str | None = None) -> None:
        self._raman = RamanShadbalaService(ephemeris_path)
        self._bphs = ShadbalaService(ephemeris_path)

    def calculate(self, request: ShadbalaMethodRequest) -> ShadbalaMethodResult:
        if request.method is ShadbalaMethod.BPHS_VERSE_REFERENCE:
            return self._bphs_result(request)
        return self._raman_result(request)

    def _bphs_result(self, request: ShadbalaMethodRequest) -> ShadbalaMethodResult:
        facts = self._bphs.calculate(
            ShadbalaRequest(
                local_datetime=request.local_datetime,
                location=request.location,
                time_precision=request.time_precision,
                node_convention=request.node_convention,
                allow_moshier_fallback=request.allow_moshier_fallback,
            )
        )
        return _result(
            request.method,
            facts.planets,
            choices=(),
            alternatives=(),
            facts=facts,
            provenance=facts.provenance,
            warnings=facts.warnings,
            time_precision=request.time_precision,
        )

    def _raman_result(self, request: ShadbalaMethodRequest) -> ShadbalaMethodResult:
        drekkana = (
            (request.drekkana_reading,)
            if request.drekkana_reading is not None
            else tuple(DrekkanaReading)
        )
        moon = (
            (request.moon_paksha_reading,)
            if request.moon_paksha_reading is not None
            else tuple(MoonPakshaReading)
        )
        runs: dict[_RunKey, RamanShadbalaFacts] = {
            (d, m): self._raman.calculate(
                RamanShadbalaRequest(
                    local_datetime=request.local_datetime,
                    location=request.location,
                    time_precision=request.time_precision,
                    drekkana_reading=d,
                    moon_paksha_reading=m,
                    node_convention=request.node_convention,
                    allow_moshier_fallback=request.allow_moshier_fallback,
                )
            )
            for d, m in itertools.product(drekkana, moon)
        }
        first = next(iter(runs.values()))
        choices = (
            _choice(
                "RAMAN_DREKKANA_ORDER",
                "Order of the male, female and neuter Drekkanas (SR-06).",
                DrekkanaReading,
                request.drekkana_reading,
                _affected(runs, lambda key: key[1]),
                _DREKKANA_REF,
            ),
            _choice(
                "RAMAN_MOON_BENEFIC_RULE",
                "Rule deciding whether the Moon is benefic for Paksha Bala (SR-09).",
                MoonPakshaReading,
                request.moon_paksha_reading,
                _affected(runs, lambda key: key[0]),
                _MOON_REF,
            ),
        )
        if len(runs) == 1:
            return _result(
                request.method,
                first.planets,
                choices=choices,
                alternatives=(),
                facts=first,
                provenance=first.provenance,
                warnings=first.warnings,
                time_precision=request.time_precision,
            )
        facts_list = list(runs.values())
        planets = tuple(_agreement_planet(i, facts_list) for i in range(len(first.planets)))
        alternatives = tuple(
            ReadingAlternative(
                drekkana_reading=d, moon_paksha_reading=m, totals_in_rupas=f.totals_in_rupas
            )
            for (d, m), f in runs.items()
        )
        warnings = (
            *first.warnings,
            "methodology readings not configured: components that differ between Raman's "
            "own readings are not evaluable; see methodology_choices and alternatives",
        )
        return _result(
            request.method,
            planets,
            choices=choices,
            alternatives=alternatives,
            facts=None,
            provenance=first.provenance,
            warnings=warnings,
            time_precision=request.time_precision,
        )


def _same(a: ComponentResult, b: ComponentResult) -> bool:
    if a.status is not b.status or a.reason is not b.reason:
        return False
    if a.virupas is None or b.virupas is None:
        return a.virupas is None and b.virupas is None
    return abs(a.virupas - b.virupas) < SAME_VALUE_TOLERANCE_VIRUPAS


def _differing(runs: list[RamanShadbalaFacts]) -> set[tuple[CelestialBody, Component]]:
    out: set[tuple[CelestialBody, Component]] = set()
    for other in runs[1:]:
        for pa, pb in zip(runs[0].planets, other.planets, strict=True):
            for c in LEAF_COMPONENTS:
                if not _same(pa.component(c), pb.component(c)):
                    out.add((pa.body, c))
    return out


def _affected(
    runs: dict[_RunKey, RamanShadbalaFacts], other_value: Callable[[_RunKey], Enum]
) -> tuple[tuple[CelestialBody, Component], ...] | None:
    """Components that change when only this choice changes (the other
    choice held fixed); None when this choice was configured."""
    groups: dict[Enum, list[RamanShadbalaFacts]] = {}
    for key, facts in runs.items():
        groups.setdefault(other_value(key), []).append(facts)
    if all(len(g) == 1 for g in groups.values()):
        return None
    diff: set[tuple[CelestialBody, Component]] = set()
    for group in groups.values():
        diff |= _differing(group)
    body_order = {b: i for i, b in enumerate(CelestialBody)}
    comp_order = {c: i for i, c in enumerate(Component)}
    return tuple(sorted(diff, key=lambda bc: (body_order[bc[0]], comp_order[bc[1]])))


def _choice(
    choice_id: str,
    statement: str,
    options: type[Enum],
    selected: Enum | None,
    affected: tuple[tuple[CelestialBody, Component], ...] | None,
    reference: SourceReference,
) -> MethodologyChoice:
    common = dict(
        choice_id=choice_id,
        statement=statement,
        options=tuple(o.value for o in options),
        confidence=EvidenceConfidence.LOW,
        reference=reference,
    )
    if selected is not None:
        return MethodologyChoice(
            **common,  # type: ignore[arg-type]
            selection=ChoiceSelection.CALLER_CONFIGURED,
            selected=selected.value,
        )
    return MethodologyChoice(
        **common,  # type: ignore[arg-type]
        selection=ChoiceSelection.NOT_SELECTED,
        material_for_this_chart=bool(affected),
        affected=affected or (),
    )


def _agreement_planet(index: int, runs: list[RamanShadbalaFacts]) -> PlanetShadbala:
    base = runs[0].planets[index]
    leaves: list[ComponentResult] = []
    for c in LEAF_COMPONENTS:
        values = [r.planets[index].component(c) for r in runs]
        if all(_same(values[0], v) for v in values[1:]):
            leaves.append(values[0])
            continue
        leaves.append(
            ComponentResult(
                component=c,
                status=ComponentStatus.NOT_EVALUABLE,
                reason=ShadbalaReason.METHODOLOGY_READING_NOT_SELECTED,
                detail="values differ between Raman's readings: "
                + ", ".join("none" if v.virupas is None else f"{v.virupas:.4f}" for v in values),
                evidence_label=EvidenceLabel.UNRESOLVED_CONFLICT,
            )
        )
    return _assemble(base.body, leaves, base.saptavarga)


def _result(
    method: ShadbalaMethod,
    planets: tuple[PlanetShadbala, ...],
    *,
    choices: tuple[MethodologyChoice, ...],
    alternatives: tuple[ReadingAlternative, ...],
    facts: RamanShadbalaFacts | ShadbalaFacts | None,
    provenance: tuple[ComponentProvenance, ...],
    warnings: tuple[str, ...],
    time_precision: ShadbalaTimePrecision,
) -> ShadbalaMethodResult:
    produces_total = method is ShadbalaMethod.MODERN_RAMAN
    totals: list[PlanetTotal] = []
    missing_all: list[NotEvaluableComponent] = []
    for p in planets:
        missing = tuple(
            c for c in LEAF_COMPONENTS if p.component(c).status is ComponentStatus.NOT_EVALUABLE
        )
        for c in missing:
            r = p.component(c)
            missing_all.append(
                NotEvaluableComponent(
                    body=p.body,
                    component=c,
                    reason=r.reason or ShadbalaReason.COMPONENT_NOT_EVALUABLE,
                    detail=r.detail,
                )
            )
        total = p.component(Component.SHADBALA_TOTAL)
        complete = produces_total and total.status is ComponentStatus.SUCCESS
        totals.append(
            PlanetTotal(
                body=p.body,
                status=TotalStatus.COMPLETE if complete else TotalStatus.PARTIAL,
                total_rupas=(total.virupas or 0.0) / 60.0 if complete else None,
                missing_components=missing,
            )
        )
    return ShadbalaMethodResult(
        system=SHADBALA_SYSTEM_ID,
        method=method,
        method_version=METHOD_VERSION[method],
        is_default_user_facing_method=method is DEFAULT_USER_FACING_METHOD,
        profile_id=METHOD_PROFILE_ID[method],
        standards_version=SHADBALA_METHOD_STANDARDS_VERSION,
        engine_version=__version__,
        method_produces_total=produces_total,
        source_confidence=_SOURCE_CONFIDENCE[method],
        sources=tuple(dict.fromkeys(p.reference for p in provenance)),
        provenance=provenance,
        authority_note=_AUTHORITY_NOTE[method],
        assumptions=_ASSUMPTIONS[method],
        methodology_choices=choices,
        unresolved_choices=tuple(
            c.choice_id
            for c in choices
            if c.selection is ChoiceSelection.NOT_SELECTED and c.material_for_this_chart
        ),
        time_precision=time_precision,
        planets=planets,
        totals=tuple(totals),
        total_status=(
            TotalStatus.COMPLETE
            if totals and all(t.status is TotalStatus.COMPLETE for t in totals)
            else TotalStatus.PARTIAL
        ),
        not_evaluable_components=tuple(missing_all),
        alternatives=alternatives,
        facts=facts,
        warnings=warnings,
    )
