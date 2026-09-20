"""Dasha facts as consumed by the rule engine (Phase 7 -> Phase 6 contract).

`astro-engine` calculates and owns the Vimshottari facts; the rule engine only
reads them. This module is the adapter: it takes the JSON form of an
astro-engine `DashaFacts` (`DashaFacts.model_dump(mode="json")`), performs no
astronomical or astrological calculation, and preserves the status, profile
IDs, boundary convention, precision, provenance labels and every period
boundary, so a later rule can cite them and a result stays reproducible.

The rule engine does not import `astro-engine` (facts flow one direction).
No shipped Phase 6 rule reads Dasha facts yet: the `requires_dasha` reason is
still reserved for the later rules that will, and this evidence section only
makes the facts available and reproducible inside the bundle.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.hashing import canonical_json, sha256_hex
from pandit_rule_engine.vocab import Body

_USABLE = ("success", "approximate")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DashaPeriodRecord(_Model):
    period_id: str
    level: str
    lord: Body
    parent_id: str | None
    sequence_index: int
    start_utc: str
    end_utc: str
    truncated_at_birth: bool


class DashaProvenanceRecord(_Model):
    entry_id: str
    item: str
    evidence_label: str
    statement: str


class DashaEvidence(_Model):
    """One Vimshottari calculation, as the evidence bundle records it."""

    system_id: str
    status: str
    reason_code: str | None
    precision_status: str
    standards_version: str
    engine_version: str
    balance_profile_id: str
    year_length_profile_id: str
    subperiod_profile_id: str
    boundary_convention: str
    time_base: str
    starting_nakshatra: str | None = None
    starting_pada: int | None = None
    starting_lord: Body | None = None
    elapsed_fraction: str | None = None
    remaining_fraction: str | None = None
    remaining_duration_microseconds: int | None = None
    birth_utc: str | None = None
    timeline_start_utc: str | None = None
    timeline_end_utc: str | None = None
    depth: int | None = None
    periods: tuple[DashaPeriodRecord, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: tuple[DashaProvenanceRecord, ...] = ()
    facts_hash: str


def _require(mapping: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise FactsError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FactsError(f"{where}: expected an object")
    return value


def _fraction(value: Any, where: str) -> str:
    fraction = _mapping(value, where)
    return f"{_require(fraction, 'numerator', where)}/{_require(fraction, 'denominator', where)}"


def _body(value: Any, where: str) -> Body:
    try:
        return Body(value)
    except ValueError as exc:
        raise FactsError(f"{where}: unknown lord {value!r}") from exc


def _iso(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise FactsError(f"{where}: expected an ISO-8601 string")
    return value


def dasha_evidence_from_facts(facts: Mapping[str, Any]) -> DashaEvidence:
    """Build `DashaEvidence` from an astro-engine `DashaFacts` in JSON form."""
    try:
        return _evidence(facts)
    except ValidationError as exc:
        raise FactsError(f"dasha: malformed facts ({exc.error_count()} invalid fields)") from exc


def _evidence(facts: Mapping[str, Any]) -> DashaEvidence:
    where = "dasha"
    profiles = _mapping(_require(facts, "profile_ids", where), "dasha.profile_ids")
    precision = _mapping(_require(facts, "precision", where), "dasha.precision")
    status = _require(facts, "status", where)
    common: dict[str, Any] = {
        "system_id": _require(facts, "system_id", where),
        "status": status,
        "reason_code": facts.get("reason_code"),
        "precision_status": _require(precision, "birth_time_status", "dasha.precision"),
        "standards_version": _require(facts, "standards_version", where),
        "engine_version": _require(facts, "engine_version", where),
        "balance_profile_id": _require(profiles, "balance_profile_id", "dasha.profile_ids"),
        "year_length_profile_id": _require(profiles, "year_length_profile_id", "dasha.profile_ids"),
        "subperiod_profile_id": _require(profiles, "subperiod_profile_id", "dasha.profile_ids"),
        "boundary_convention": _require(facts, "boundary_convention", where),
        "time_base": _require(facts, "time_base", where),
        "warnings": tuple(facts.get("warnings") or ()),
        "provenance": tuple(
            DashaProvenanceRecord(
                entry_id=_require(entry, "entry_id", "dasha.provenance"),
                item=_require(entry, "item", "dasha.provenance"),
                evidence_label=_require(entry, "evidence_label", "dasha.provenance"),
                statement=_require(entry, "statement", "dasha.provenance"),
            )
            for entry in (
                _mapping(raw, "dasha.provenance[]") for raw in (facts.get("provenance") or ())
            )
        ),
        "facts_hash": sha256_hex(canonical_json(facts)),
    }
    if status not in _USABLE:
        if facts.get("reason_code") is None:
            raise FactsError("dasha: a non-success result must carry a reason_code")
        return DashaEvidence(**common)

    starting = _mapping(_require(facts, "starting", where), "dasha.starting")
    periods = tuple(
        DashaPeriodRecord(
            period_id=_require(node, "period_id", "dasha.periods[]"),
            level=_require(node, "level", "dasha.periods[]"),
            lord=_body(_require(node, "lord", "dasha.periods[]"), "dasha.periods[].lord"),
            parent_id=node.get("parent_id"),
            sequence_index=_require(node, "sequence_index", "dasha.periods[]"),
            start_utc=_iso(_require(node, "start_utc", "dasha.periods[]"), "start_utc"),
            end_utc=_iso(_require(node, "end_utc", "dasha.periods[]"), "end_utc"),
            truncated_at_birth=_require(node, "truncated_at_birth", "dasha.periods[]"),
        )
        for node in (_mapping(raw, "dasha.periods[]") for raw in _require(facts, "periods", where))
    )
    if not periods:
        raise FactsError("dasha: a successful result must carry periods")
    return DashaEvidence(
        **common,
        starting_nakshatra=_require(starting, "nakshatra", "dasha.starting"),
        starting_pada=_require(starting, "pada", "dasha.starting"),
        starting_lord=_body(_require(starting, "lord", "dasha.starting"), "dasha.starting.lord"),
        elapsed_fraction=_fraction(
            _require(starting, "elapsed_fraction", "dasha.starting"), "dasha.starting"
        ),
        remaining_fraction=_fraction(
            _require(starting, "remaining_fraction", "dasha.starting"), "dasha.starting"
        ),
        remaining_duration_microseconds=_require(
            starting, "remaining_duration_microseconds", "dasha.starting"
        ),
        birth_utc=_iso(_require(facts, "birth_utc", where), "birth_utc"),
        timeline_start_utc=_iso(_require(facts, "timeline_start_utc", where), "timeline_start_utc"),
        timeline_end_utc=_iso(_require(facts, "timeline_end_utc", where), "timeline_end_utc"),
        depth=_require(facts, "depth", where),
        periods=periods,
    )
