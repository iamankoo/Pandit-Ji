"""Muhurta (standards v1.23.0, MU-01 to MU-14): rule-set integrity, factor
evaluation, person-specific factors, overlapping source statements kept
separate, NOT_EVALUABLE inputs, search windows and determinism."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.muhurta import (
    PURPOSE_ALIASES,
    RULES,
    Classification,
    JanmaInput,
    MuhurtaEvaluateRequest,
    MuhurtaSearchRequest,
    MuhurtaService,
    Purpose,
)
from pandit_astro_engine.muhurta.models import FactorStatus, MomentFacts
from pandit_astro_engine.muhurta.rules import ALL_TITHIS, FactorKind, FactorRule
from pandit_astro_engine.muhurta.service import evaluate_factors, summarize, tithi_label
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.panchang.profiles import KALAP, RAMAN_MUH, EvidenceLabel
from pandit_astro_engine.rashi import Rashi

DELHI = Location(latitude=28.61, longitude=77.21)


@pytest.fixture(scope="module")
def service() -> MuhurtaService:
    return MuhurtaService(None)


# ------------------------------------------------------------ rule data


def test_purposes_and_aliases() -> None:
    assert set(RULES) == set(Purpose)
    assert PURPOSE_ALIASES["housewarming"] is Purpose.GRIHA_PRAVESHA
    assert PURPOSE_ALIASES["mundan"] is Purpose.CHAULA
    assert PURPOSE_ALIASES["marriage"] is Purpose.VIVAHA


@pytest.mark.parametrize("purpose", list(Purpose))
def test_rule_integrity(purpose: Purpose) -> None:
    rules = RULES[purpose]
    ids = [r.rule_id for r in rules]
    assert len(ids) == len(set(ids))
    for r in rules:
        assert r.purpose is purpose
        assert r.reference.source_id in (KALAP, RAMAN_MUH)
        assert r.statement
        buckets = [set(r.favourable), set(r.middling), set(r.unfavourable), set(r.conditional)]
        for i, a in enumerate(buckets):
            for b in buckets[i + 1 :]:
                assert not a & b, r.rule_id  # a value is in one class only
        if r.kind is FactorKind.TITHI:
            assert set().union(*buckets) <= set(ALL_TITHIS), r.rule_id
        if r.kind is FactorKind.NAKSHATRA:
            assert set().union(*buckets) <= {n.value for n in Nakshatra}, r.rule_id
        if r.kind is FactorKind.NOT_EVALUATED:
            assert r.not_evaluable_reason
        if r.reference.source_id == RAMAN_MUH:
            assert r.evidence_label is EvidenceLabel.MODERN_TRADITION


def test_no_effect_statement_or_policy_barred_input_is_encoded() -> None:
    text = json.dumps([r.model_dump(mode="json") for rs in RULES.values() for r in rs]).lower()
    for barred in ("widow", "prostitute", "death", "adultery", "bride", "poverty", "disease"):
        assert barred not in text, barred


def test_tithi_labels() -> None:
    assert [tithi_label(i) for i in (1, 15, 16, 29, 30)] == ["S1", "S15", "K1", "K14", "K30"]


# ---------------------------------------------------- factor evaluation


def _facts(**kw: object) -> MomentFacts:
    base: dict[str, object] = dict(
        tithi="S2", paksha="shukla", nakshatra=Nakshatra.ROHINI, yoga="siddhi", karana="bava",
        weekday="monday", lagna_sign=Rashi.GEMINI, lagna_navamsa=Rashi.ARIES,
        moon_sign=Rashi.TAURUS, sun_sign=Rashi.ARIES,
        planet_signs=(("sun", Rashi.ARIES), ("moon", Rashi.TAURUS), ("mars", Rashi.LEO),
                      ("mercury", Rashi.ARIES), ("jupiter", Rashi.CANCER),
                      ("venus", Rashi.PISCES), ("saturn", Rashi.AQUARIUS),
                      ("rahu", Rashi.LIBRA), ("ketu", Rashi.ARIES)),
        jupiter_combust=False, venus_combust=False, is_daytime=True, forenoon=True,
    )  # fmt: skip
    base.update(kw)
    return MomentFacts(**base)  # type: ignore[arg-type]


NUMBERS = {"tithi": 2, "nakshatra": 4, "weekday": 2, "lagna": 3}


def _by_id(purpose: Purpose, facts: MomentFacts, people: tuple[JanmaInput, ...] = ()) -> dict:  # type: ignore[type-arg]
    return {
        (f.rule_id, f.participant): f for f in evaluate_factors(purpose, facts, NUMBERS, people)
    }


def test_vivaha_overlapping_statements_are_reported_separately() -> None:
    """Dark 10 is 'best' in one sentence and 'after the 8th of the dark
    fortnight' in another; Taurus is 'middling' and also Prishtodaya. Both
    factors are reported; neither overrides the other."""
    by = _by_id(Purpose.VIVAHA, _facts(tithi="K10", paksha="krishna", lagna_sign=Rashi.TAURUS))
    assert by[("MU.VIVAHA.TITHI_BEST", None)].classification is Classification.FAVOURABLE
    assert by[("MU.VIVAHA.TITHI_AFTER_K8", None)].classification is Classification.UNFAVOURABLE
    assert by[("MU.VIVAHA.LAGNA", None)].classification is Classification.MIDDLING
    assert by[("MU.VIVAHA.PRISHTODAYA", None)].classification is Classification.UNFAVOURABLE
    assert by[("MU.VIVAHA.WANING_MOON", None)].classification is Classification.UNFAVOURABLE


def test_house_occupancy_and_conjunction() -> None:
    # Gemini rising: 7th is Sagittarius (vacant), 8th Capricorn (vacant)
    by = _by_id(Purpose.VIVAHA, _facts())
    assert by[("MU.VIVAHA.HOUSE7_VACANT", None)].value == "vacant"
    assert by[("MU.VIVAHA.MOON_CONJUNCTION", None)].value == "alone"
    busy = _facts(planet_signs=(("sun", Rashi.SAGITTARIUS), ("moon", Rashi.TAURUS),
                                ("mars", Rashi.TAURUS)))  # fmt: skip
    by = _by_id(Purpose.VIVAHA, busy)
    assert by[("MU.VIVAHA.HOUSE7_VACANT", None)].classification is Classification.UNFAVOURABLE
    assert by[("MU.VIVAHA.MOON_CONJUNCTION", None)].value == "conjunct"
    chaula = _by_id(Purpose.CHAULA, busy)
    assert chaula[("MU.CHAULA.HOUSE7", None)].value == "7:sun"
    assert chaula[("MU.CHAULA.HOUSE7", None)].classification is Classification.UNFAVOURABLE


def test_chaula_conditional_values_are_not_evaluable() -> None:
    by = _by_id(Purpose.CHAULA, _facts(weekday="wednesday", lagna_sign=Rashi.LEO))
    wed = by[("MU.CHAULA.WEEKDAY", None)]
    assert wed.status is FactorStatus.NOT_EVALUABLE and wed.classification is None
    assert by[("MU.CHAULA.LAGNA", None)].status is FactorStatus.NOT_EVALUABLE
    monday = _by_id(Purpose.CHAULA, _facts(paksha="krishna", tithi="K2"))
    assert monday[("MU.CHAULA.MONDAY", None)].classification is Classification.UNFAVOURABLE


def test_griha_pravesha_lagna_navamsa_exception() -> None:
    movable = _by_id(Purpose.GRIHA_PRAVESHA, _facts(lagna_sign=Rashi.ARIES))
    assert movable[("MU.GRIHA.LAGNA", None)].classification is Classification.UNFAVOURABLE
    taurus = _by_id(
        Purpose.GRIHA_PRAVESHA, _facts(lagna_sign=Rashi.ARIES, lagna_navamsa=Rashi.TAURUS)
    )
    assert taurus[("MU.GRIHA.LAGNA", None)].value == "movable_taurus_navamsa"
    assert taurus[("MU.GRIHA.LAGNA", None)].classification is Classification.FAVOURABLE
    after = _by_id(Purpose.GRIHA_PRAVESHA, _facts(forenoon=False))
    assert after[("MU.GRIHA.FORENOON", None)].value == "afternoon"


def test_person_specific_factors() -> None:
    none = _by_id(Purpose.VIVAHA, _facts())
    tara = none[("MU.VIVAHA.TARA", None)]
    assert tara.status is FactorStatus.NOT_EVALUABLE
    assert tara.reason == "requires_janma_nakshatra_and_rasi"
    people = (
        JanmaInput(janma_nakshatra=Nakshatra.ROHINI, janma_rasi=Rashi.TAURUS),
        JanmaInput(janma_nakshatra=Nakshatra.ASHWINI, janma_rasi=Rashi.ARIES),
    )
    by = _by_id(Purpose.VIVAHA, _facts(), people)
    assert by[("MU.VIVAHA.TARA", 0)].value == "1"  # the birth nakshatra itself
    assert by[("MU.VIVAHA.TARA", 0)].classification is Classification.UNFAVOURABLE
    assert by[("MU.VIVAHA.TARA", 1)].value == "4"
    assert by[("MU.VIVAHA.TARABALA_RAMAN", 1)].value == "kshema"
    assert by[("MU.VIVAHA.CHANDRABALA_RAMAN", 1)].value == "2"  # Taurus from Aries


def test_panchaka_remainder_classes() -> None:
    # 2 + 2 + 4 + 3 = 11 -> remainder 2: Agni
    by = _by_id(Purpose.VIVAHA, _facts())
    assert by[("MU.VIVAHA.PANCHAKA_RAMAN", None)].value == "agni"
    assert by[("MU.VIVAHA.PANCHAKA_RAMAN", None)].classification is Classification.MIDDLING
    gp = _by_id(Purpose.GRIHA_PRAVESHA, _facts())
    assert gp[("MU.GRIHA_PRAVESHA.PANCHAKA_RAMAN", None)].classification is (
        Classification.UNFAVOURABLE
    )
    assert not any(k[0].endswith("PANCHAKA_RAMAN") for k in _by_id(Purpose.CHAULA, _facts()))


def test_summary() -> None:
    factors = evaluate_factors(Purpose.GRIHA_PRAVESHA, _facts(), NUMBERS, ())
    s = summarize(factors)
    assert s.not_evaluable == sum(1 for f in factors if f.status is FactorStatus.NOT_EVALUABLE)
    assert set(s.not_evaluable_rule_ids) >= {"MU.GRIHA.VENUS_DIRECTION", "MU.GRIHA.OWNER_PREGNANCY"}
    assert s.no_unfavourable_factor is (s.unfavourable == 0)


# ---------------------------------------------------------- service


def test_evaluate_contract(service: MuhurtaService) -> None:
    r = service.evaluate(
        MuhurtaEvaluateRequest(
            purpose=Purpose.GRIHA_PRAVESHA,
            local_datetime=LocalDateTimeInput(
                year=2026, month=11, day=20, hour=9, minute=30, timezone="Asia/Kolkata"
            ),
            location=DELHI,
        )
    )
    assert r.status is FactorStatus.SUCCESS and r.purpose is Purpose.GRIHA_PRAVESHA
    assert r.standards_version == "1.24.0" and r.rules_version == "1.0.0"
    assert r.facts is not None and r.facts.tithi == "S11" and r.facts.weekday == "friday"
    assert {f.rule_id for f in r.factors} == {x.rule_id for x in RULES[Purpose.GRIHA_PRAVESHA]}
    assert r.notes


def test_evaluate_polar_night(service: MuhurtaService) -> None:
    r = service.evaluate(
        MuhurtaEvaluateRequest(
            purpose=Purpose.CHAULA,
            local_datetime=LocalDateTimeInput(
                year=2026, month=12, day=21, hour=12, timezone="Europe/Oslo"
            ),  # fmt: skip
            location=Location(latitude=69.65, longitude=18.96),
        )
    )
    assert r.status is FactorStatus.NOT_EVALUABLE and r.reason == "sunrise_not_occurring"


@pytest.fixture(scope="module")
def search(service: MuhurtaService):  # type: ignore[no-untyped-def]
    return service.search(
        MuhurtaSearchRequest(
            purpose=Purpose.GRIHA_PRAVESHA,
            start_date=dt.date(2026, 11, 15),
            days=7,
            location=DELHI,
            timezone="Asia/Kolkata",
        )
    )


def test_search_windows_have_no_unfavourable_factor(service: MuhurtaService, search) -> None:  # type: ignore[no-untyped-def]
    assert search.windows and search.segments_examined > 100
    for w in search.windows:
        assert w.start.julian_day_ut < w.end.julian_day_ut
        assert w.summary.no_unfavourable_factor
        mid = (w.start.julian_day_ut + w.end.julian_day_ut) / 2
        local = w.start.local + dt.timedelta(days=mid - w.start.julian_day_ut)
        check = service.evaluate(
            MuhurtaEvaluateRequest(
                purpose=Purpose.GRIHA_PRAVESHA,
                local_datetime=LocalDateTimeInput(
                    year=local.year, month=local.month, day=local.day, hour=local.hour,
                    minute=local.minute, second=local.second, timezone="Asia/Kolkata",
                ),
                location=DELHI,
            )
        )  # fmt: skip
        assert check.summary is not None and check.summary.no_unfavourable_factor
    for a, b in zip(search.windows, search.windows[1:], strict=False):
        assert a.end.julian_day_ut <= b.start.julian_day_ut


def test_search_is_deterministic(service: MuhurtaService, search) -> None:  # type: ignore[no-untyped-def]
    again = service.search(
        MuhurtaSearchRequest(
            purpose=Purpose.GRIHA_PRAVESHA,
            start_date=dt.date(2026, 11, 15),
            days=7,
            location=DELHI,
            timezone="Asia/Kolkata",
        )
    )
    assert json.dumps(again.model_dump(mode="json"), sort_keys=True) == json.dumps(
        search.model_dump(mode="json"), sort_keys=True
    )


def test_search_range_is_bounded() -> None:
    with pytest.raises(ValueError):
        MuhurtaSearchRequest(
            purpose=Purpose.VIVAHA, start_date=dt.date(2026, 1, 1), days=32, location=DELHI,
            timezone="Asia/Kolkata",
        )  # fmt: skip


def test_rules_are_frozen_data() -> None:
    rule = RULES[Purpose.VIVAHA][0]
    assert isinstance(rule, FactorRule)
    with pytest.raises(Exception):  # noqa: B017 - pydantic frozen instance
        rule.statement = "changed"  # type: ignore[misc]


def test_rules_export_is_versioned_and_complete() -> None:
    from pandit_astro_engine.muhurta import export_rules

    doc = json.loads(json.dumps(export_rules()))
    assert doc["rules_version"] == "1.0.0"
    assert set(doc["purposes"]) == {p.value for p in Purpose}
    for purpose, rules in doc["purposes"].items():
        assert [r["rule_id"] for r in rules] == [r.rule_id for r in RULES[Purpose(purpose)]]
        for r in rules:
            assert r["statement"] and r["evidence_label"]
            assert r["reference"]["source_id"] and r["reference"]["verification_level"]
            assert r["reference"]["locator"]
    assert doc["aliases"]["housewarming"] == "griha_pravesha"
