"""Phase 9 closure evidence sections (v1.21.0 EV-01 to EV-10): KP, Shadbala,
Jaimini WP-G, Chinese Four Pillars and Tarot. Fixtures were generated from
real astro-engine service calls; these tests always run (no astro-engine
import)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine._version import __version__
from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.bundle import build_bundle
from pandit_rule_engine.evaluator import evaluate_ruleset
from pandit_rule_engine.phase9_evidence import (
    chinese_evidence_from_facts,
    jaimini_evidence_from_facts,
    kp_evidence_from_facts,
    shadbala_evidence_from_facts,
    tarot_evidence_from_layout,
)
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset

_FIX = Path(__file__).parent / "fixtures" / "phase9"
SECTIONS = ("kp", "shadbala", "jaimini", "chinese", "tarot")


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIX / f"{name}.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


# --------------------------------------------------------------------------
# Adapters
# --------------------------------------------------------------------------


def test_kp_natal_and_horary() -> None:
    natal = kp_evidence_from_facts(_load("kp_natal"))
    assert natal.kind == "natal" and natal.system == "kp_krishnamurti_paddhati"
    assert natal.standards_version == "1.15.0"
    assert natal.cusps.status == "success" and len(natal.cusps.cusps) == 12
    assert natal.significators.not_evaluated == (
        "level_e_conjunction",
        "level_f_aspect",
        "node_agency",
    )
    horary = kp_evidence_from_facts(_load("kp_horary"))
    assert horary.kind == "horary" and horary.entry is not None and horary.entry.number == 29
    assert horary.ruling_planets is not None and horary.ruling_planets.status == "success"
    seventh = horary.cusps.cusps[6].lordship
    assert (seventh.star_lord, seventh.sub_lord) == ("saturn", "venus")
    assert {p.item.split(": ")[1] for p in horary.provenance} >= {"KP_HORARY_NUMBER_249_READER_VI"}


def test_kp_polar_not_evaluable_is_preserved() -> None:
    polar = kp_evidence_from_facts(_load("kp_polar"))
    assert polar.cusps.status == "not_evaluable"
    assert polar.cusps.reason == "placidus_polar_circle"
    assert polar.significators.reason == "placidus_polar_circle"


def test_shadbala_both_profiles_kept_distinct() -> None:
    bphs = shadbala_evidence_from_facts(_load("shadbala_bphs"))
    raman = shadbala_evidence_from_facts(_load("shadbala_raman"))
    assert bphs.profile_id == "SHADBALA_BPHS_SANTHANAM_27_VERSE"
    assert raman.profile_id == "SHADBALA_RAMAN_GRAHA_BHAVA_BALAS"
    assert bphs.readings == {}
    assert raman.readings == {
        "drekkana_reading": "worked_example_12",
        "moon_paksha_reading": "waxing_half",
    }
    for p in bphs.planets:
        total = next(c for c in p.components if c.component == "shadbala_total")
        assert total.status == "not_evaluable"
    for p in raman.planets:
        total = next(c for c in p.components if c.component == "shadbala_total")
        assert total.status == "success" and total.virupas is not None
    assert all("SRC-RAMAN-GRAHA-BHAVA-BALAS" in p.source_ids for p in raman.provenance)
    assert all("SRC-BPHS-SANTHANAM-1984" in p.source_ids for p in bphs.provenance)


def test_shadbala_total_cannot_hide_a_missing_component() -> None:
    raw = _load("shadbala_raman")
    comps = raw["planets"][0]["components"]
    for c in comps:
        if c["component"] == "drik":
            c.update(status="not_evaluable", virupas=None, reason="drik_nature_undetermined")
    with pytest.raises(FactsError):
        shadbala_evidence_from_facts(raw)


def test_shadbala_status_invariants() -> None:
    raw = _load("shadbala_bphs")
    raw["planets"][0]["components"][0]["reason"] = "birth_time_unknown"
    with pytest.raises(FactsError):
        shadbala_evidence_from_facts(raw)
    raw = _load("shadbala_bphs")
    raw["planets"][0]["components"][0]["virupas"] = None
    with pytest.raises(FactsError):
        shadbala_evidence_from_facts(raw)


def test_jaimini() -> None:
    ev = jaimini_evidence_from_facts(_load("jaimini"))
    assert ev.standards_version == "1.21.0"
    assert len(ev.bhava_padas) == 12
    assert ev.karakamsa.status == "success" and ev.karakamsa.karakamsa is not None
    assert ev.chara_karaka_profile_id == "JAIMINI_CHARA_KARAKA_EIGHT_BODY_BPHS_32_1_17"
    assert {p.item for p in ev.provenance} >= {
        "RASHI_DRISHTI_PLANET_BPHS_8_4_5",
        "ARUDHA_BHAVA_PADA_BPHS_29_1_5",
        "KARAKAMSA_BPHS_33_1_2",
    }
    raw = _load("jaimini")
    raw["bhava_padas"] = raw["bhava_padas"][:11]
    with pytest.raises(FactsError):
        jaimini_evidence_from_facts(raw)


def test_chinese_and_unknown_time() -> None:
    ev = chinese_evidence_from_facts(_load("chinese"))
    assert ev.profile_id == "CHINESE_BAZI_FOUR_PILLARS_SOLAR_TERMS_V1"
    assert all(p.status == "success" for p in (ev.year, ev.month, ev.day, ev.hour))
    unknown = chinese_evidence_from_facts(_load("chinese_unknown_time"))
    assert unknown.hour.status == "not_evaluable" and unknown.hour.reason == "birth_time_unknown"
    assert "luck_cycles_require_sex_not_collected" in unknown.not_evaluated
    raw = _load("chinese")
    raw["year"]["stem"] = None
    with pytest.raises(FactsError):
        chinese_evidence_from_facts(raw)


def test_tarot() -> None:
    ev = tarot_evidence_from_layout(_load("tarot_celtic"))
    assert ev.spread_id == "TAROT_SPREAD_WAITE_CELTIC_METHOD_1910"
    assert len(ev.placements) == 10 and ev.significator_card_id == "cups_queen"
    assert ev.seed_sha256 is not None and "fixture-seed" not in ev.model_dump_json()
    assert {p.item for p in ev.provenance} >= {"TAROT_DECK_WAITE_SMITH_1910"}
    raw = _load("tarot_celtic")
    raw["interpretation"] = "a meaning"
    with pytest.raises(FactsError):
        tarot_evidence_from_layout(raw)
    raw = _load("tarot_celtic")
    raw["placements"][1]["card"] = copy.deepcopy(raw["placements"][0]["card"])
    with pytest.raises(FactsError):
        tarot_evidence_from_layout(raw)


@pytest.mark.parametrize(
    "adapter", [kp_evidence_from_facts, shadbala_evidence_from_facts, jaimini_evidence_from_facts,
                chinese_evidence_from_facts, tarot_evidence_from_layout]
)  # fmt: skip
def test_adapters_reject_non_objects_and_missing_fields(adapter) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(FactsError):
        adapter([])
    with pytest.raises(FactsError):
        adapter({})


def test_facts_hash_is_deterministic_and_input_sensitive() -> None:
    a = kp_evidence_from_facts(_load("kp_natal"))
    b = kp_evidence_from_facts(_load("kp_natal"))
    assert a.facts_hash == b.facts_hash
    raw = _load("kp_natal")
    raw["ayanamsa_degrees"] += 1e-9
    assert kp_evidence_from_facts(raw).facts_hash != a.facts_hash


# --------------------------------------------------------------------------
# Bundle compatibility
# --------------------------------------------------------------------------


@pytest.fixture()
def ruleset(tmp_path: Path):  # type: ignore[no-untyped-def]
    from pandit_rule_engine.loader import load_ruleset

    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "bphs/a.yaml": rule_doc(rule_id="TEST_A", profile="TEST_A"),
        },
    )
    return load_ruleset(tmp_path)


def _build(ruleset, **sections):  # type: ignore[no-untyped-def]
    facts = chart("aries", full_placements())
    return build_bundle(
        ruleset=ruleset,
        facts=facts,
        results=evaluate_ruleset(ruleset, facts, StubDerived()),
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
        **sections,
    )


def _all_sections() -> dict[str, Any]:
    return {
        "kp": kp_evidence_from_facts(_load("kp_natal")),
        "shadbala": shadbala_evidence_from_facts(_load("shadbala_raman")),
        "jaimini": jaimini_evidence_from_facts(_load("jaimini")),
        "chinese": chinese_evidence_from_facts(_load("chinese")),
        "tarot": tarot_evidence_from_layout(_load("tarot_celtic")),
    }


def test_bundle_without_new_sections_is_unchanged(ruleset) -> None:  # type: ignore[no-untyped-def]
    plain = _build(ruleset)
    explicit_none = _build(ruleset, **{k: None for k in SECTIONS})
    assert plain.bundle_hash == explicit_none.bundle_hash
    dumped = plain.model_dump(mode="json")
    for key in SECTIONS:
        assert key not in dumped


def test_each_section_changes_the_hash_and_is_serialized(ruleset) -> None:  # type: ignore[no-untyped-def]
    base = _build(ruleset).bundle_hash
    sections = _all_sections()
    hashes = set()
    for key, value in sections.items():
        bundle = _build(ruleset, **{key: value})
        assert bundle.bundle_hash != base
        assert key in json.loads(bundle.canonical_json())
        hashes.add(bundle.bundle_hash)
    assert len(hashes) == len(sections)
    full = _build(ruleset, **sections)
    again = _build(ruleset, **_all_sections())
    assert full.bundle_hash == again.bundle_hash


def test_shadbala_profiles_give_different_bundles(ruleset) -> None:  # type: ignore[no-untyped-def]
    a = _build(ruleset, shadbala=shadbala_evidence_from_facts(_load("shadbala_bphs")))
    b = _build(ruleset, shadbala=shadbala_evidence_from_facts(_load("shadbala_raman")))
    assert a.bundle_hash != b.bundle_hash
