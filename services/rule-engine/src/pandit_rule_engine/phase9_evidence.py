"""Phase 9 WP-E to WP-I facts as consumed by the rule engine (evidence-bundle
integration; `docs/ASTROLOGY_STANDARDS.md` v1.21.0, EV-01 to EV-10).

`astro-engine` calculates and owns these facts; the rule engine only records
them. Each adapter takes the JSON form of one astro-engine result -- a KP
chart or horary chart, one Shadbala profile's facts, the WP-G Jaimini facts,
a Chinese Four Pillars chart, or a Tarot layout -- validates its structure
and status/reason invariants, keeps the profile identifiers, statuses,
reasons and provenance verbatim, and records a hash of the whole input so
the bundle stays reproducible. It performs no astrology computation and does
not import `astro-engine`.

No shipped Phase 6 rule reads any of these sections. Every section is
optional and omitted from a bundle that does not carry it, so existing
bundles serialize and hash exactly as before. A bundle carries at most one
Shadbala profile (the caller chooses BPHS-verse or Raman; the two are never
merged into one section), mirroring the Ashtakavarga precedent.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    ValidationError,
    model_serializer,
    model_validator,
)

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.hashing import canonical_json, sha256_hex

_SUCCESS = "success"
_NOT_EVALUABLE = "not_evaluable"
_NOT_APPLICABLE = "not_applicable"


class _Record(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


def _hash(raw: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(dict(raw)))


def _status_pair(status: str, reason: object, where: str) -> None:
    if status == _SUCCESS and reason is not None:
        raise ValueError(f"{where}: a successful result must not carry a reason")
    if status == _NOT_EVALUABLE and reason is None:
        raise ValueError(f"{where}: a not-evaluable result must carry a reason")
    if status not in (_SUCCESS, _NOT_EVALUABLE, _NOT_APPLICABLE):
        raise ValueError(f"{where}: unknown status {status!r}")


class ProvenanceRecord(_Record):
    item: str
    evidence_label: str
    source_ids: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# KP (WP-E)
# --------------------------------------------------------------------------


class KpLordshipRecord(_Record):
    sign: str
    sign_lord: str
    nakshatra: str
    star_lord: str
    sub_lord: str
    sub_sub_lord: str
    near_boundary: bool


class KpPlanetRecord(_Record):
    body: str
    longitude: float
    retrograde: bool
    lordship: KpLordshipRecord | None = None
    house: int | None = None


class KpCuspRecord(_Record):
    house: int
    longitude: float
    lordship: KpLordshipRecord


class KpCuspsRecord(_Record):
    status: str
    reason: str | None = None
    cusps: tuple[KpCuspRecord, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> KpCuspsRecord:
        _status_pair(self.status, self.reason, "kp.cusps")
        if self.status == _SUCCESS and len(self.cusps) != 12:
            raise ValueError("kp.cusps: a successful result must carry 12 cusps")
        if self.status != _SUCCESS and self.cusps:
            raise ValueError("kp.cusps: a not-evaluable result must carry no cusps")
        return self


class KpHouseSignificatorsRecord(_Record):
    house: int
    level_a_in_star_of_occupants: tuple[str, ...]
    level_b_occupants: tuple[str, ...]
    level_c_in_star_of_lord: tuple[str, ...]
    level_d_lord: tuple[str, ...]


class KpSignificatorsRecord(_Record):
    status: str
    reason: str | None = None
    houses: tuple[KpHouseSignificatorsRecord, ...] = ()
    not_evaluated: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> KpSignificatorsRecord:
        _status_pair(self.status, self.reason, "kp.significators")
        return self


class KpRulingMemberRecord(_Record):
    body: str
    role: str
    represents: str | None = None
    star_lord_of_body: str
    retrograde_star_flag: str


class KpRulingPlanetsRecord(_Record):
    status: str
    reason: str | None = None
    weekday_sunday_zero: int | None = None
    members: tuple[KpRulingMemberRecord, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> KpRulingPlanetsRecord:
        _status_pair(self.status, self.reason, "kp.ruling_planets")
        return self


class KpHoraryEntryRecord(_Record):
    number: int
    sign: str
    star_lord: str
    sub_lord: str
    start: float
    end: float


class KpEvidence(_Record):
    kind: str
    system: str
    standards_version: str
    profiles: dict[str, Any]
    time_precision: str | None = None
    ayanamsa_degrees: float
    planets: tuple[KpPlanetRecord, ...]
    cusps: KpCuspsRecord
    significators: KpSignificatorsRecord
    ruling_planets: KpRulingPlanetsRecord | None = None
    entry: KpHoraryEntryRecord | None = None
    provenance: tuple[ProvenanceRecord, ...]
    warnings: tuple[str, ...] = ()
    facts_hash: str


def _provenance(entries: Any, item_key: str) -> tuple[ProvenanceRecord, ...]:
    return tuple(
        ProvenanceRecord(
            item=e[item_key],
            evidence_label=e["evidence_label"],
            source_ids=tuple(r["source_id"] for r in e.get("references", ()))
            if "references" in e
            else ((e["reference"]["source_id"],) if "reference" in e else (e["source_id"],)),
        )
        for e in entries
    )


def kp_evidence_from_facts(facts: Mapping[str, Any]) -> KpEvidence:
    """A KP natal chart (`KpChartFacts`) or horary chart (`KpHoraryFacts`)."""
    if not isinstance(facts, Mapping):
        raise FactsError("kp: expected an object")
    try:
        return KpEvidence(
            kind="horary" if facts.get("entry") is not None else "natal",
            system=facts["system"],
            standards_version=facts["standards_version"],
            profiles=dict(facts["profiles"]),
            time_precision=facts.get("time_precision"),
            ayanamsa_degrees=facts["ayanamsa_degrees"],
            planets=tuple(KpPlanetRecord(**p) for p in facts["planets"]),
            cusps=KpCuspsRecord(**facts["cusps"]),
            significators=KpSignificatorsRecord(**facts["significators"]),
            ruling_planets=KpRulingPlanetsRecord(**facts["ruling_planets"])
            if facts.get("ruling_planets") is not None
            else None,
            entry=KpHoraryEntryRecord(**facts["entry"]) if facts.get("entry") else None,
            provenance=_provenance(facts["provenance"], "item"),
            warnings=tuple(facts.get("warnings", ())),
            facts_hash=_hash(facts),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"kp: malformed facts ({exc})") from exc


# --------------------------------------------------------------------------
# Shadbala (WP-F; BPHS-verse or Raman profile)
# --------------------------------------------------------------------------

_LEAVES = (
    "uchcha", "saptavargaja", "ojayugmarasyamsa", "kendradi", "drekkana", "dig",
    "nathonnatha", "paksha", "tribhaga", "abda", "masa", "vara", "hora", "ayana",
    "yuddha", "cheshta", "naisargika", "drik",
)  # fmt: skip


class ShadbalaComponentRecord(_Record):
    component: str
    status: str
    virupas: float | None = None
    reason: str | None = None
    evidence_label: str

    @model_validator(mode="after")
    def _check(self) -> ShadbalaComponentRecord:
        _status_pair(self.status, self.reason, f"shadbala.{self.component}")
        if (self.status == _SUCCESS) != (self.virupas is not None):
            raise ValueError(f"shadbala.{self.component}: virupas only with success")
        return self


class ShadbalaPlanetRecord(_Record):
    body: str
    components: tuple[ShadbalaComponentRecord, ...]

    @model_validator(mode="after")
    def _check(self) -> ShadbalaPlanetRecord:
        by = {c.component: c for c in self.components}
        total = by.get("shadbala_total")
        if total is None:
            raise ValueError(f"shadbala.{self.body}: missing shadbala_total")
        blocked = [k for k in _LEAVES if k in by and by[k].status == _NOT_EVALUABLE]
        if total.status == _SUCCESS and blocked:
            raise ValueError(
                f"shadbala.{self.body}: a total cannot be produced while {blocked} are "
                "not evaluable"
            )
        return self


#: Method identifiers of the Shadbala method policy (v1.22.0, SM-01 to SM-12)
#: and the one profile each method may carry.
SHADBALA_METHOD_PROFILE = {
    "MODERN_RAMAN": "SHADBALA_RAMAN_GRAHA_BHAVA_BALAS",
    "BPHS_VERSE_REFERENCE": "SHADBALA_BPHS_SANTHANAM_27_VERSE",
}
_COMPLETE = "complete"
_PARTIAL = "partial"
_NOT_SELECTED = "not_selected"


class ShadbalaChoiceRecord(_Record):
    choice_id: str
    options: tuple[str, ...]
    selection: str
    selected: str | None = None
    material_for_this_chart: bool | None = None
    affected: tuple[tuple[str, str], ...] = ()
    confidence: str


class ShadbalaTotalRecord(_Record):
    body: str
    status: str
    total_rupas: float | None = None
    missing_components: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ShadbalaTotalRecord:
        if self.status not in (_COMPLETE, _PARTIAL):
            raise ValueError(f"shadbala.total.{self.body}: unknown status {self.status!r}")
        if (self.status == _COMPLETE) != (self.total_rupas is not None):
            raise ValueError(f"shadbala.total.{self.body}: rupas only with a complete total")
        if self.status == _COMPLETE and self.missing_components:
            raise ValueError(f"shadbala.total.{self.body}: complete total with missing parts")
        return self


class ShadbalaMethodRecord(_Record):
    """The method-policy envelope of a `ShadbalaMethodResult` (SM-10)."""

    method: str
    method_version: str
    is_default_user_facing_method: bool
    method_produces_total: bool
    source_confidence: str
    source_ids: tuple[str, ...]
    authority_note: str
    assumption_ids: tuple[str, ...]
    choices: tuple[ShadbalaChoiceRecord, ...]
    unresolved_choices: tuple[str, ...]
    total_status: str
    totals: tuple[ShadbalaTotalRecord, ...]
    alternatives: tuple[dict[str, Any], ...] = ()


class ShadbalaEvidence(_Record):
    profile_id: str
    standards_version: str
    system: str
    time_precision: str
    readings: dict[str, str] = {}
    planets: tuple[ShadbalaPlanetRecord, ...]
    provenance: tuple[ProvenanceRecord, ...]
    warnings: tuple[str, ...] = ()
    facts_hash: str
    #: Present only when the section was built from a `ShadbalaMethodResult`;
    #: omitted when absent, so sections built from profile facts hash as before.
    method: ShadbalaMethodRecord | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_method(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if data.get("method") is None:
            data.pop("method", None)
        return data


def _method_record(
    result: Mapping[str, Any], planets: tuple[ShadbalaPlanetRecord, ...]
) -> ShadbalaMethodRecord:
    method = result["method"]
    if SHADBALA_METHOD_PROFILE.get(method) != result["profile_id"]:
        raise ValueError(
            f"method {method!r} cannot carry profile {result['profile_id']!r} "
            "(the two Shadbala methods are never mixed)"
        )
    record = ShadbalaMethodRecord(
        method=method,
        method_version=result["method_version"],
        is_default_user_facing_method=result["is_default_user_facing_method"],
        method_produces_total=result["method_produces_total"],
        source_confidence=result["source_confidence"],
        source_ids=tuple(dict.fromkeys(s["source_id"] for s in result["sources"])),
        authority_note=result["authority_note"],
        assumption_ids=tuple(a["assumption_id"] for a in result["assumptions"]),
        choices=tuple(result["methodology_choices"]),
        unresolved_choices=tuple(result["unresolved_choices"]),
        total_status=result["total_status"],
        totals=tuple(result["totals"]),
        alternatives=tuple(result.get("alternatives", ())),
    )
    if method == "BPHS_VERSE_REFERENCE" and (
        record.method_produces_total
        or record.choices
        or any(t.status == _COMPLETE for t in record.totals)
    ):
        raise ValueError("BPHS_VERSE_REFERENCE produces no total and has no reading choice")
    open_material = {
        c.choice_id
        for c in record.choices
        if c.selection == _NOT_SELECTED and c.material_for_this_chart
    }
    if open_material != set(record.unresolved_choices):
        raise ValueError("unresolved_choices must list exactly the open material choices")
    by_body = {p.body: {c.component: c for c in p.components} for p in planets}
    for t in record.totals:
        total = by_body.get(t.body, {}).get("shadbala_total")
        if total is None or (t.status == _COMPLETE) != (total.status == _SUCCESS):
            raise ValueError(f"shadbala.total.{t.body}: disagrees with the planet components")
    complete = bool(record.totals) and all(t.status == _COMPLETE for t in record.totals)
    if record.total_status != (_COMPLETE if complete else _PARTIAL):
        raise ValueError("total_status disagrees with the planet totals")
    return record


def shadbala_evidence_from_facts(facts: Mapping[str, Any]) -> ShadbalaEvidence:
    """One `ShadbalaFacts` (BPHS verse profile), one `RamanShadbalaFacts`, or
    one `ShadbalaMethodResult` (method policy, v1.22.0), which also records
    the method envelope."""
    if not isinstance(facts, Mapping):
        raise FactsError("shadbala: expected an object")
    if "method" in facts:
        return _shadbala_evidence_from_method_result(facts)
    try:
        readings = {k: facts[k] for k in ("drekkana_reading", "moon_paksha_reading") if k in facts}
        return ShadbalaEvidence(
            profile_id=facts["profile_id"],
            standards_version=facts["standards_version"],
            system=facts["system"],
            time_precision=facts["time_precision"],
            readings=readings,
            planets=tuple(
                ShadbalaPlanetRecord(body=p["body"], components=tuple(p["components"]))
                for p in facts["planets"]
            ),
            provenance=_provenance(facts["provenance"], "component"),
            warnings=tuple(facts.get("warnings", ())),
            facts_hash=_hash(facts),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"shadbala: malformed facts ({exc})") from exc


def _shadbala_evidence_from_method_result(result: Mapping[str, Any]) -> ShadbalaEvidence:
    try:
        planets = tuple(
            ShadbalaPlanetRecord(body=p["body"], components=tuple(p["components"]))
            for p in result["planets"]
        )
        readings = {
            c["choice_id"]: c["selected"]
            for c in result["methodology_choices"]
            if c.get("selected") is not None
        }
        return ShadbalaEvidence(
            profile_id=result["profile_id"],
            standards_version=result["standards_version"],
            system=result["system"],
            time_precision=result["time_precision"],
            readings=readings,
            planets=planets,
            provenance=_provenance(result["provenance"], "component"),
            warnings=tuple(result.get("warnings", ())),
            facts_hash=_hash(result),
            method=_method_record(result, planets),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"shadbala: malformed method result ({exc})") from exc


# --------------------------------------------------------------------------
# Jaimini WP-G
# --------------------------------------------------------------------------


class JaiminiDrishtiRecord(_Record):
    body: str
    sign: str
    aspected_signs: tuple[str, ...]
    aspected_bodies: tuple[str, ...]


class BhavaPadaRecord(_Record):
    house: int
    pada: str
    rule: str


class GrahaPadaRecord(_Record):
    body: str
    status: str
    pada: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _check(self) -> GrahaPadaRecord:
        _status_pair(self.status, self.reason, f"jaimini.graha_pada.{self.body}")
        return self


class KarakamsaRecord(_Record):
    chara_karaka_profile_id: str
    status: str
    atma_karaka: str | None = None
    karakamsa: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _check(self) -> KarakamsaRecord:
        _status_pair(self.status, self.reason, "jaimini.karakamsa")
        if self.status == _SUCCESS and self.karakamsa is None:
            raise ValueError("jaimini.karakamsa: success requires a sign")
        return self


class JaiminiEvidence(_Record):
    system: str
    standards_version: str
    lagna_sign: str
    chara_karaka_profile_id: str
    chara_karaka_status: str
    karakamsa: KarakamsaRecord
    planet_rashi_drishti: tuple[JaiminiDrishtiRecord, ...]
    bhava_padas: tuple[BhavaPadaRecord, ...]
    graha_padas: tuple[GrahaPadaRecord, ...]
    provenance: tuple[ProvenanceRecord, ...]
    facts_hash: str


def jaimini_evidence_from_facts(facts: Mapping[str, Any]) -> JaiminiEvidence:
    if not isinstance(facts, Mapping):
        raise FactsError("jaimini: expected an object")
    try:
        if len(facts["bhava_padas"]) != 12:
            raise ValueError("jaimini: twelve Bhava Padas are required")
        return JaiminiEvidence(
            system=facts["system"],
            standards_version=facts["standards_version"],
            lagna_sign=facts["lagna_sign"],
            chara_karaka_profile_id=facts["chara_karaka"]["profile_id"],
            chara_karaka_status=facts["chara_karaka"]["status"],
            karakamsa=KarakamsaRecord(**facts["karakamsa"]),
            planet_rashi_drishti=tuple(
                JaiminiDrishtiRecord(**r) for r in facts["planet_rashi_drishti"]
            ),
            bhava_padas=tuple(BhavaPadaRecord(**r) for r in facts["bhava_padas"]),
            graha_padas=tuple(GrahaPadaRecord(**r) for r in facts["graha_padas"]),
            provenance=_provenance(facts["provenance"], "profile_id"),
            facts_hash=_hash(facts),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"jaimini: malformed facts ({exc})") from exc


# --------------------------------------------------------------------------
# Chinese Four Pillars (WP-H)
# --------------------------------------------------------------------------


class PillarRecord(_Record):
    status: str
    reason: str | None = None
    sexagenary_index: int | None = None
    stem: str | None = None
    branch: str | None = None

    @model_validator(mode="after")
    def _check(self) -> PillarRecord:
        _status_pair(self.status, self.reason, "chinese.pillar")
        if self.status == _SUCCESS and (self.stem is None or self.branch is None):
            raise ValueError("chinese.pillar: success requires a stem and branch")
        return self


class ChineseEvidence(_Record):
    system: str
    standards_version: str
    profile_id: str
    time_precision: str
    time_basis: str
    day_boundary: str
    year: PillarRecord
    month: PillarRecord
    day: PillarRecord
    hour: PillarRecord
    not_evaluated: tuple[str, ...]
    provenance: tuple[ProvenanceRecord, ...]
    facts_hash: str


def chinese_evidence_from_facts(facts: Mapping[str, Any]) -> ChineseEvidence:
    if not isinstance(facts, Mapping):
        raise FactsError("chinese: expected an object")
    try:
        return ChineseEvidence(
            system=facts["system"],
            standards_version=facts["standards_version"],
            profile_id=facts["profile_id"],
            time_precision=facts["time_precision"],
            time_basis=facts["time_basis"],
            day_boundary=facts["day_boundary"],
            year=PillarRecord(**facts["year"]),
            month=PillarRecord(**facts["month"]),
            day=PillarRecord(**facts["day"]),
            hour=PillarRecord(**facts["hour"]),
            not_evaluated=tuple(facts.get("not_evaluated", ())),
            provenance=_provenance(facts["provenance"], "entry_id"),
            facts_hash=_hash(facts),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"chinese: malformed facts ({exc})") from exc


# --------------------------------------------------------------------------
# Tarot (WP-I)
# --------------------------------------------------------------------------


class TarotPlacementRecord(_Record):
    index: int
    position_id: str
    card_id: str
    reversed: bool


class TarotEvidence(_Record):
    system: str
    standards_version: str
    deck_id: str
    spread_id: str
    draw_method: str
    seed_sha256: str | None = None
    reversals_allowed: bool | None = None
    significator_card_id: str | None = None
    placements: tuple[TarotPlacementRecord, ...]
    notice: str
    provenance: tuple[ProvenanceRecord, ...]
    facts_hash: str


def tarot_evidence_from_layout(layout: Mapping[str, Any]) -> TarotEvidence:
    """A Tarot layout carries no chart fact and no meaning; recorded so a
    conversation's layout is reproducible, never read by an astrology rule."""
    if not isinstance(layout, Mapping):
        raise FactsError("tarot: expected an object")
    try:
        if layout.get("interpretation") is not None:
            raise ValueError("tarot: a layout must carry no interpretation")
        ids = [p["card"]["card_id"] for p in layout["placements"]]
        if len(set(ids)) != len(ids):
            raise ValueError("tarot: a card may appear only once")
        significator = layout.get("significator")
        return TarotEvidence(
            system=layout["system"],
            standards_version=layout["standards_version"],
            deck_id=layout["deck_id"],
            spread_id=layout["spread_id"],
            draw_method=layout["draw_method"],
            seed_sha256=layout.get("seed_sha256"),
            reversals_allowed=layout.get("reversals_allowed"),
            significator_card_id=significator["card_id"] if significator else None,
            placements=tuple(
                TarotPlacementRecord(
                    index=p["index"],
                    position_id=p["position_id"],
                    card_id=p["card"]["card_id"],
                    reversed=p["reversed"],
                )
                for p in layout["placements"]
            ),
            notice=layout["notice"],
            provenance=_provenance(layout.get("provenance", ()), "item"),
            facts_hash=_hash(layout),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"tarot: malformed layout ({exc})") from exc
