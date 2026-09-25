"""Phase 10 daily Panchang as consumed by the rule engine (evidence-bundle
integration; `docs/ASTROLOGY_STANDARDS.md` v1.23.0, PC-30).

`astro-engine` calculates the Panchang; the rule engine only records it.
The adapter takes the JSON form of one `DailyPanchang`, validates its
structure and invariants (a successful day has a sunrise, a sunset and a
next sunrise; each element list is contiguous, begins with the element
current at sunrise and ends with the one current at the next sunrise; a
not-evaluable day carries a reason and no elements), keeps the profile and
convention identifiers verbatim and records a hash of the whole input. It
performs no astrology computation and does not import `astro-engine`.

No shipped rule reads this section; it is omitted from bundles that do not
carry it, so earlier bundles serialize and hash exactly as before.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.hashing import canonical_json, sha256_hex

_SUCCESS = "success"
_NOT_EVALUABLE = "not_evaluable"
_OCCURRED = "occurred"
_KINDS = ("tithis", "nakshatras", "yogas", "karanas")


class _Record(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class PanchangElementRecord(_Record):
    kind: str
    index: int
    name: str
    start_utc: str
    end_utc: str
    start_jd: float
    end_jd: float
    current_at_sunrise: bool
    current_at_next_sunrise: bool
    kshaya: bool


class LunarMonthRecord(_Record):
    saura_frame: str
    amanta_month: str
    amanta_adhika: bool
    purnimanta_month: str
    purnimanta_adhika: bool
    paksha: str
    suppressed_month_before: str | None = None
    saka_year_expired: int | None = None
    vikrama_year_chaitradi_expired: int | None = None
    year_reason: str | None = None


class PanchangEvidence(_Record):
    system: str
    standards_version: str
    profile_id: str
    regional_convention: str
    sunrise_convention: str
    date: str
    timezone: str
    latitude: float
    longitude: float
    status: str
    reason: str | None = None
    sunrise_utc: str | None = None
    sunset_utc: str | None = None
    next_sunrise_utc: str | None = None
    vara: str | None = None
    elements: tuple[PanchangElementRecord, ...] = ()
    #: The selected saura frame (PC-15: Lahiri by default); the month facts
    #: of every frame are kept in `lunar_months`.
    saura_frame: str | None = None
    lunar_months: tuple[LunarMonthRecord, ...] = ()
    not_implemented: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    facts_hash: str

    @model_validator(mode="after")
    def _check(self) -> PanchangEvidence:
        if self.status == _NOT_EVALUABLE:
            if self.reason is None:
                raise ValueError("panchang: a not-evaluable day must carry a reason")
            if self.elements or self.lunar_months:
                raise ValueError("panchang: a not-evaluable day carries no elements")
            return self
        if self.status != _SUCCESS or self.reason is not None:
            raise ValueError("panchang: a successful day carries no reason")
        if None in (self.sunrise_utc, self.sunset_utc, self.next_sunrise_utc, self.vara):
            raise ValueError("panchang: a successful day needs sunrise, sunset and next sunrise")
        if not self.lunar_months:
            raise ValueError("panchang: a successful day needs its lunar month facts")
        if self.saura_frame not in {m.saura_frame for m in self.lunar_months}:
            raise ValueError("panchang: the selected saura frame has no month facts")
        return self


def _elements(facts: Mapping[str, Any]) -> tuple[PanchangElementRecord, ...]:
    out: list[PanchangElementRecord] = []
    for key in _KINDS:
        spans = facts[key]
        if facts["status"] == _SUCCESS and not spans:
            raise ValueError(f"panchang.{key}: empty")
        for i, span in enumerate(spans):
            record = PanchangElementRecord(
                kind=span["kind"],
                index=span["index"],
                name=span["name"],
                start_utc=span["start"]["utc"],
                end_utc=span["end"]["utc"],
                start_jd=span["start"]["julian_day_ut"],
                end_jd=span["end"]["julian_day_ut"],
                current_at_sunrise=span["current_at_sunrise"],
                current_at_next_sunrise=span["current_at_next_sunrise"],
                kshaya=span["kshaya"],
            )
            if record.end_jd <= record.start_jd:
                raise ValueError(f"panchang.{key}[{i}]: ends before it starts")
            if i == 0 and not record.current_at_sunrise:
                raise ValueError(f"panchang.{key}: must begin with the element at sunrise")
            if i > 0 and abs(record.start_jd - out[-1].end_jd) > 1e-5:
                raise ValueError(f"panchang.{key}[{i}]: not contiguous with the previous one")
            if i == len(spans) - 1 and not record.current_at_next_sunrise:
                raise ValueError(f"panchang.{key}: must end with the element at next sunrise")
            out.append(record)
    return tuple(out)


def _utc(event: Mapping[str, Any]) -> str | None:
    if event.get("status") != _OCCURRED:
        return None
    return str(event["instant"]["utc"])


def panchang_evidence_from_facts(facts: Mapping[str, Any]) -> PanchangEvidence:
    """One astro-engine `DailyPanchang` in JSON form."""
    if not isinstance(facts, Mapping):
        raise FactsError("panchang: expected an object")
    try:
        vara = facts.get("vara")
        return PanchangEvidence(
            system=facts["system"],
            standards_version=facts["standards_version"],
            profile_id=facts["profile_id"],
            regional_convention=facts["regional_convention"],
            sunrise_convention=facts["sunrise_convention"],
            date=facts["date"],
            timezone=facts["timezone"],
            latitude=facts["location"]["latitude"],
            longitude=facts["location"]["longitude"],
            status=facts["status"],
            reason=facts.get("reason"),
            sunrise_utc=_utc(facts["sunrise"]),
            sunset_utc=_utc(facts["sunset"]),
            next_sunrise_utc=_utc(facts["next_sunrise"]),
            vara=None if vara is None else vara["weekday"],
            elements=_elements(facts),
            saura_frame=facts.get("saura_frame"),
            lunar_months=tuple(facts.get("lunar_months", ())),
            not_implemented=tuple(n["item"] for n in facts.get("not_implemented", ())),
            provenance_ids=tuple(p["entry_id"] for p in facts.get("provenance", ())),
            facts_hash=sha256_hex(canonical_json(dict(facts))),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"panchang: malformed facts ({exc})") from exc
