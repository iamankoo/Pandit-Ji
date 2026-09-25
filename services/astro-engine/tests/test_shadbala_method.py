"""Shadbala method policy (standards v1.22.0, SM-01 to SM-12).

MODERN_RAMAN is the default user-facing method; BPHS_VERSE_REFERENCE stays a
separate reference method without a total. The tests prove that the two
methods stay separate, that method identifiers are preserved, that no
component is carried from one method into the other, that Raman's
contradictory readings are visible and reproducible rather than silently
defaulted, that missing inputs give NOT_EVALUABLE, and that the underlying
profile results are unchanged.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.shadbala import (
    DEFAULT_USER_FACING_METHOD,
    ShadbalaMethod,
    ShadbalaMethodRequest,
    ShadbalaMethodService,
)
from pandit_astro_engine.shadbala.method import (
    METHOD_PROFILE_ID,
    METHOD_VERSION,
    ChoiceSelection,
    EvidenceConfidence,
    TotalStatus,
)
from pandit_astro_engine.shadbala.models import (
    ComponentStatus,
    RamanShadbalaFacts,
    RamanShadbalaRequest,
    ShadbalaFacts,
    ShadbalaReason,
    ShadbalaRequest,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala.profiles import PROFILE_ID, RAMAN_PROFILE_ID, Component
from pandit_astro_engine.shadbala.raman import DrekkanaReading, MoonPakshaReading
from pandit_astro_engine.shadbala.raman_service import RamanShadbalaService
from pandit_astro_engine.shadbala.service import LEAF_COMPONENTS, ShadbalaService

STANDARD = LocalDateTimeInput(year=1918, month=10, day=16, hour=8, minute=49, second=40,
                              timezone="UTC")  # fmt: skip
BANGALORE = Location(latitude=13.0, longitude=77.5833)
RAMAN_SRC = "SRC-RAMAN-GRAHA-BHAVA-BALAS"
BPHS_SRC = "SRC-BPHS-SANTHANAM-1984"


def _req(
    method: ShadbalaMethod = ShadbalaMethod.MODERN_RAMAN, **kw: object
) -> ShadbalaMethodRequest:
    base: dict[str, object] = dict(
        method=method,
        local_datetime=STANDARD,
        location=BANGALORE,
        time_precision=ShadbalaTimePrecision.EXACT,
    )
    base.update(kw)
    return ShadbalaMethodRequest(**base)  # type: ignore[arg-type]


def _configured(**kw: object) -> ShadbalaMethodRequest:
    readings: dict[str, object] = dict(
        drekkana_reading=DrekkanaReading.WORKED_EXAMPLE_12,
        moon_paksha_reading=MoonPakshaReading.WAXING_HALF,
    )
    readings.update(kw)
    return _req(**readings)


@pytest.fixture(scope="module")
def service() -> ShadbalaMethodService:
    return ShadbalaMethodService(None)


# ---------------------------------------------------------------- identity


def test_default_user_facing_method_is_modern_raman() -> None:
    assert DEFAULT_USER_FACING_METHOD is ShadbalaMethod.MODERN_RAMAN
    assert METHOD_PROFILE_ID == {
        ShadbalaMethod.MODERN_RAMAN: RAMAN_PROFILE_ID,
        ShadbalaMethod.BPHS_VERSE_REFERENCE: PROFILE_ID,
    }


def test_method_is_required() -> None:
    with pytest.raises(ValidationError):
        ShadbalaMethodRequest(  # type: ignore[call-arg]
            local_datetime=STANDARD, location=BANGALORE, time_precision=ShadbalaTimePrecision.EXACT
        )


@pytest.mark.parametrize("method", list(ShadbalaMethod))
def test_every_result_exposes_the_required_metadata(
    service: ShadbalaMethodService, method: ShadbalaMethod
) -> None:
    kw = {} if method is ShadbalaMethod.BPHS_VERSE_REFERENCE else dict(
        drekkana_reading=DrekkanaReading.TEXT_ARTICLE_36,
        moon_paksha_reading=MoonPakshaReading.EIGHTH_DAY_WINDOW,
    )  # fmt: skip
    r = service.calculate(_req(method, **kw))
    assert r.method is method
    assert r.method_version == METHOD_VERSION[method]
    assert r.profile_id == METHOD_PROFILE_ID[method]
    assert r.standards_version == "1.22.0"
    assert r.is_default_user_facing_method is (method is ShadbalaMethod.MODERN_RAMAN)
    assert r.sources and r.assumptions and r.authority_note
    assert isinstance(r.source_confidence, EvidenceConfidence)
    assert r.total_status in (TotalStatus.COMPLETE, TotalStatus.PARTIAL)
    assert len(r.totals) == 7
    # the flattened NOT_EVALUABLE list matches the planets exactly
    listed = {(n.body, n.component) for n in r.not_evaluable_components}
    actual = {
        (p.body, c)
        for p in r.planets
        for c in LEAF_COMPONENTS
        if p.component(c).status is ComponentStatus.NOT_EVALUABLE
    }
    assert listed == actual


def test_raman_authority_note_does_not_claim_universal_authority(
    service: ShadbalaMethodService,
) -> None:
    r = service.calculate(_configured())
    assert "not a universally authoritative" in r.authority_note
    assert r.source_confidence is EvidenceConfidence.HIGH
    assert all(c.confidence is EvidenceConfidence.LOW for c in r.methodology_choices)


# ------------------------------------------------------------- separation


def test_methods_stay_separate_and_sources_never_mix(service: ShadbalaMethodService) -> None:
    raman = service.calculate(_configured())
    bphs = service.calculate(_req(ShadbalaMethod.BPHS_VERSE_REFERENCE))
    assert {s.source_id for s in raman.sources} == {RAMAN_SRC}
    assert {s.source_id for s in bphs.sources} == {BPHS_SRC}
    assert isinstance(raman.facts, RamanShadbalaFacts)
    assert isinstance(bphs.facts, ShadbalaFacts)
    assert raman.facts.profile_id == RAMAN_PROFILE_ID
    assert bphs.facts.profile_id == PROFILE_ID
    assert bphs.methodology_choices == () and bphs.alternatives == ()


def test_no_component_is_carried_between_methods(service: ShadbalaMethodService) -> None:
    """Each method's planets equal its own profile's output exactly; a
    component BPHS cannot evaluate is never filled from Raman."""
    raman = service.calculate(_configured())
    bphs = service.calculate(_req(ShadbalaMethod.BPHS_VERSE_REFERENCE))
    raman_direct = RamanShadbalaService(None).calculate(
        RamanShadbalaRequest(
            local_datetime=STANDARD,
            location=BANGALORE,
            time_precision=ShadbalaTimePrecision.EXACT,
            drekkana_reading=DrekkanaReading.WORKED_EXAMPLE_12,
            moon_paksha_reading=MoonPakshaReading.WAXING_HALF,
        )
    )
    bphs_direct = ShadbalaService(None).calculate(
        ShadbalaRequest(
            local_datetime=STANDARD, location=BANGALORE, time_precision=ShadbalaTimePrecision.EXACT
        )
    )
    assert raman.planets == raman_direct.planets
    assert bphs.planets == bphs_direct.planets
    for rp, bp in zip(raman.planets, bphs.planets, strict=True):
        for c in (Component.ABDA, Component.MASA, Component.HORA, Component.DRIK):
            assert bp.component(c).status is ComponentStatus.NOT_EVALUABLE
            assert rp.component(c).status is ComponentStatus.SUCCESS


def test_bphs_reference_still_has_no_total(service: ShadbalaMethodService) -> None:
    r = service.calculate(_req(ShadbalaMethod.BPHS_VERSE_REFERENCE))
    assert r.method_produces_total is False
    assert r.total_status is TotalStatus.PARTIAL
    for t in r.totals:
        assert t.status is TotalStatus.PARTIAL and t.total_rupas is None
        assert t.missing_components
    for p in r.planets:
        assert p.component(Component.SHADBALA_TOTAL).status is ComponentStatus.NOT_EVALUABLE


def test_readings_are_rejected_for_the_bphs_reference() -> None:
    with pytest.raises(ValidationError):
        _req(ShadbalaMethod.BPHS_VERSE_REFERENCE, drekkana_reading=DrekkanaReading.TEXT_ARTICLE_36)
    with pytest.raises(ValidationError):
        _req(
            ShadbalaMethod.BPHS_VERSE_REFERENCE,
            moon_paksha_reading=MoonPakshaReading.WAXING_HALF,
        )


def test_configured_raman_total_is_complete(service: ShadbalaMethodService) -> None:
    r = service.calculate(_configured())
    assert r.total_status is TotalStatus.COMPLETE
    assert r.unresolved_choices == ()
    assert all(c.selection is ChoiceSelection.CALLER_CONFIGURED for c in r.methodology_choices)
    assert r.facts is not None
    assert dict((t.body, t.total_rupas) for t in r.totals) == dict(r.facts.totals_in_rupas)


# ------------------------------------------------------ no hidden default


def test_unconfigured_material_choice_is_not_resolved_silently(
    service: ShadbalaMethodService,
) -> None:
    r = service.calculate(_req())
    assert r.facts is None
    assert r.unresolved_choices == ("RAMAN_DREKKANA_ORDER",)
    drek = r.methodology_choices[0]
    assert drek.selection is ChoiceSelection.NOT_SELECTED and drek.selected is None
    assert drek.material_for_this_chart is True
    assert drek.affected == ((B.VENUS, Component.DREKKANA),)
    moon_rule = r.methodology_choices[1]
    assert moon_rule.material_for_this_chart is False and moon_rule.affected == ()
    venus = next(p for p in r.planets if p.body is B.VENUS)
    assert venus.component(Component.DREKKANA).reason is (
        ShadbalaReason.METHODOLOGY_READING_NOT_SELECTED
    )
    totals = {t.body: t for t in r.totals}
    assert totals[B.VENUS].status is TotalStatus.PARTIAL
    assert totals[B.VENUS].total_rupas is None
    assert r.total_status is TotalStatus.PARTIAL
    # planets the choice does not touch keep their (identical) totals
    assert totals[B.SUN].status is TotalStatus.COMPLETE


def test_alternatives_make_the_contradiction_visible_and_reproducible(
    service: ShadbalaMethodService,
) -> None:
    r = service.calculate(_req())
    assert len(r.alternatives) == 4
    for alt in r.alternatives:
        again = service.calculate(
            _configured(
                drekkana_reading=alt.drekkana_reading,
                moon_paksha_reading=alt.moon_paksha_reading,
            )
        )
        assert again.facts is not None
        assert alt.totals_in_rupas == again.facts.totals_in_rupas
    venus = {alt.drekkana_reading: dict(alt.totals_in_rupas)[B.VENUS] for alt in r.alternatives}
    assert venus[DrekkanaReading.WORKED_EXAMPLE_12] != venus[DrekkanaReading.TEXT_ARTICLE_36]


def test_partly_configured_request_runs_only_the_open_choice(
    service: ShadbalaMethodService,
) -> None:
    r = service.calculate(_req(drekkana_reading=DrekkanaReading.WORKED_EXAMPLE_12))
    assert len(r.alternatives) == 2
    assert {a.drekkana_reading for a in r.alternatives} == {DrekkanaReading.WORKED_EXAMPLE_12}
    assert r.unresolved_choices == ()  # the Moon rule does not matter for this chart
    assert r.total_status is TotalStatus.COMPLETE
    assert r.methodology_choices[0].selection is ChoiceSelection.CALLER_CONFIGURED
    assert r.methodology_choices[1].selection is ChoiceSelection.NOT_SELECTED


def test_moon_rule_is_reported_when_it_matters(service: ShadbalaMethodService) -> None:
    """A date whose Moon lies between the 1st and the 8th day of the bright
    half (elongation below 84 degrees): waxing, yet outside the 8th-day
    window, so the two Moon rules disagree."""
    new_moon_plus_4 = LocalDateTimeInput(year=2024, month=1, day=15, hour=6, minute=0, second=0,
                                         timezone="UTC")  # fmt: skip
    r = service.calculate(
        _req(local_datetime=new_moon_plus_4, drekkana_reading=DrekkanaReading.TEXT_ARTICLE_36)
    )
    assert "RAMAN_MOON_BENEFIC_RULE" in r.unresolved_choices
    affected = r.methodology_choices[1].affected
    assert (B.MOON, Component.PAKSHA) in affected
    moon = next(p for p in r.planets if p.body is B.MOON)
    assert moon.component(Component.PAKSHA).status is ComponentStatus.NOT_EVALUABLE


# ---------------------------------------------------------- missing input


@pytest.mark.parametrize("method", list(ShadbalaMethod))
def test_unknown_birth_time_is_not_evaluable(
    service: ShadbalaMethodService, method: ShadbalaMethod
) -> None:
    r = service.calculate(_req(method, time_precision=ShadbalaTimePrecision.UNKNOWN))
    assert r.total_status is TotalStatus.PARTIAL
    assert r.unresolved_choices == ()
    for p in r.planets:
        assert p.component(Component.NAISARGIKA).status is ComponentStatus.SUCCESS
    reasons = {n.reason for n in r.not_evaluable_components}
    assert ShadbalaReason.BIRTH_TIME_UNKNOWN in reasons
    assert ShadbalaReason.METHODOLOGY_READING_NOT_SELECTED not in reasons


# ------------------------------------------------------------ determinism


def test_deterministic(service: ShadbalaMethodService) -> None:
    a = service.calculate(_req()).model_dump(mode="json")
    b = service.calculate(_req()).model_dump(mode="json")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
