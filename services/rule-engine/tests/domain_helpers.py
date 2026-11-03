"""Helpers for the Phase 17 domain ruleset tests (synthetic facts; no astronomy)."""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pandit_contracts.domain import DomainAnalysisRequest, LifeDomain

from pandit_rule_engine.adapters import facts_from_kundli
from pandit_rule_engine.dasha_evidence import DashaEvidence
from pandit_rule_engine.domain import (
    DomainRuleset,
    VargaPlacements,
    evaluate_domain,
    load_domain_ruleset,
    varga_from_kundli,
)
from pandit_rule_engine.facts import ChartFacts
from pandit_rule_engine.transit_evidence import TransitEvidence
from tests.chart_builder import BODIES, SIGNS, kundli_dict

REPO = Path(__file__).resolve().parents[3]
DOMAIN_RULES_DIR = REPO / "services" / "rule-engine" / "domain_rules"
VEDIC_RULES_DIR = REPO / "services" / "knowledge" / "rules"
KV = "KV-0000000000000000"

#: Lagna Aries: houses 1..12 are Aries..Pisces, so the lords are
#: Mars, Venus, Mercury, Moon, Sun, Mercury, Venus, Mars, Jupiter, Saturn, Saturn, Jupiter.
BASE = {
    "sun": "leo",
    "moon": "cancer",
    "mars": "aries",
    "mercury": "virgo",
    "jupiter": "sagittarius",
    "venus": "libra",
    "saturn": "aquarius",
    "rahu": "gemini",
    "ketu": "sagittarius",
}


@lru_cache(maxsize=1)
def ruleset() -> DomainRuleset:
    return load_domain_ruleset(DOMAIN_RULES_DIR)


def kundli(
    lagna: str = "aries",
    placements: dict[str, str] | None = None,
    varga: dict[int, dict[str, str]] | None = None,
) -> dict[str, Any]:
    chart = kundli_dict(lagna, dict(placements or BASE))
    if varga is not None:
        charts: dict[str, Any] = {}
        for number, signs in varga.items():
            charts[str(number)] = {
                "varga": number,
                "ascendant_rashi": signs.get("lagna", lagna),
                "planets": [{"body": b, "rashi": s} for b, s in signs.items() if b != "lagna"],
            }
        chart["charts"] = charts
    return chart


def facts(lagna: str = "aries", placements: dict[str, str] | None = None) -> ChartFacts:
    return facts_from_kundli(kundli(lagna, placements))


def varga_of(
    numbers: tuple[int, ...] = (2, 3, 7, 9, 10, 12, 20, 24),
    signs: dict[str, str] | None = None,
) -> VargaPlacements:
    placements = signs or {b: "taurus" for b in BODIES}
    chart = kundli("aries", BASE, {n: dict(placements) for n in numbers})
    got = varga_from_kundli(chart)
    assert got is not None
    return got


def dasha(periods: list[tuple[str, str, str, str]], *, status: str = "success") -> DashaEvidence:
    """``periods`` are (level, lord, start_utc, end_utc)."""
    return DashaEvidence.model_validate(
        {
            "system_id": "vimshottari",
            "status": status,
            "reason_code": None if status == "success" else "birth_time_unknown",
            "precision_status": "exact",
            "standards_version": "1.5.0",
            "engine_version": "test",
            "balance_profile_id": "b",
            "year_length_profile_id": "y",
            "subperiod_profile_id": "s",
            "boundary_convention": "start_inclusive_end_exclusive",
            "time_base": "utc",
            "periods": [
                {
                    "period_id": f"P{i}",
                    "level": level,
                    "lord": lord,
                    "parent_id": None,
                    "sequence_index": i,
                    "start_utc": start,
                    "end_utc": end,
                    "truncated_at_birth": False,
                }
                for i, (level, lord, start, end) in enumerate(periods)
            ],
            "facts_hash": "d" * 64,
        }
    )


def transit(
    signs: dict[str, str], *, status: str = "success", at: str = "2026-09-21T12:00:00+00:00"
) -> TransitEvidence:
    states = [
        {
            "body": body,
            "sign": sign,
            "degree_in_sign": 10.0,
            "nakshatra": "x",
            "pada": 1,
            "speed_longitude": 1.0,
            "retrograde": False,
            "ephemeris_mode": "test",
        }
        for body, sign in signs.items()
    ]
    return TransitEvidence.model_validate(
        {
            "system_id": "gochar",
            "status": status,
            "reason_code": None if status == "success" else "not_available",
            "standards_version": "1.6.0",
            "engine_version": "test",
            "boundary_convention": "b",
            "time_base": "utc",
            "profile_ids": {
                "reference_profile_id": "r",
                "favourable_reading_ids": [],
                "boundary_profile_id": "b",
            },
            "snapshot": {
                "at_utc": at,
                "julian_day_ut": 2461000.0,
                "states": states,
                "moon_relative_status": "success",
                "contacts_status": "success",
                "lagna_status": "success",
            },
            "facts_hash": "e" * 64,
        }
    )


def evaluate(
    domain: LifeDomain,
    *,
    adult: bool | None = True,
    chart: ChartFacts | None = None,
    rs: DomainRuleset | None = None,
    as_of: str | None = None,
    **inputs: Any,
) -> Any:
    request = DomainAnalysisRequest(
        analysis_id="t1", domain=domain, subject_adult_confirmed=adult, as_of_utc=as_of
    )
    return evaluate_domain(
        rs or ruleset(), request, chart or facts(), knowledge_version=KV, **inputs
    )


def copy_ruleset(tmp_path: Path) -> Path:
    target = tmp_path / "domain_rules"
    shutil.copytree(DOMAIN_RULES_DIR, target)
    return target


def read_docs(path: Path) -> list[dict[str, Any]]:
    return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]


def write_docs(path: Path, docs: list[dict[str, Any]]) -> None:
    path.write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")


def sign_of(house: int, lagna: str = "aries") -> str:
    return SIGNS[(SIGNS.index(lagna) + house - 1) % 12]
