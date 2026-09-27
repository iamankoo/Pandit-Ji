"""Phase 11 compatibility and numerology facts as consumed by the rule engine
(evidence-bundle integration; `docs/ASTROLOGY_STANDARDS.md` v1.25.0, EV-11 to
EV-16).

`astro-engine` calculates matching and numerology; the rule engine records
them. The adapters take the JSON form of one astro-engine
`CompatibilityFacts` or `NumerologyFacts`, check the Phase 11 invariants
(one profile per section and the right factor set for it; a blocked or
invalid result carries no facts; a 36-point total only when all eight kutas
are evaluated and equal to their sum; a factor that is not evaluated carries
a reason and no outcome; the Chaldean profile never retains master numbers)
and record a hash of the whole input. They perform no astrology computation
and do not import `astro-engine`. The numerology record keeps the numbers,
not the name or the date of birth (data minimisation; the hash still pins
the input).

`kuja_partner_comparison` sets two people's Phase 6 Kuja (Mangal) results
side by side, reading by reading, for BPHS Ch. 80 v. 49 ("the yoga ceases
when both partners have it"). It reads rule results only and gives no
verdict. No shipped rule reads these sections; each is omitted from bundles
that do not carry it, so earlier bundles hash exactly as before.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.hashing import canonical_json, sha256_hex
from pandit_rule_engine.results import RuleResult
from pandit_rule_engine.vocab import Status

ASHTAKOOT_PROFILE = "ASHTAKOOT_MUHURTA_CHINTAMANI_VIVAHA_21_37_V1"
PORUTHAM_PROFILE = "TEN_PORUTHAM_KALAPRAKASIKA_IYER_1917_XIII_V1"
PROFILE_SYSTEM = {
    ASHTAKOOT_PROFILE: "NORTH_INDIAN_ASHTAKOOT",
    PORUTHAM_PROFILE: "SOUTH_INDIAN_TEN_PORUTHAM",
}
ASHTAKOOT_FACTORS = (
    "varna",
    "vashya",
    "tara",
    "yoni",
    "graha_maitri",
    "gana",
    "bhakoot",
    "nadi",
)
PORUTHAM_FACTORS = (
    "dhinam",
    "ganam",
    "mahendhram",
    "sthree_dheergham",
    "yoni",
    "rasi",
    "rasyadhipathi",
    "vasyam",
    "rajju",
    "vedhai",
)
_REFUSALS = {"blocked_by_policy", "invalid_input", "internal_error"}
_EVALUATED = "evaluated"

NUMEROLOGY_PROFILES = {
    "NUMEROLOGY_CHALDEAN_CHEIRO_1926_V1": "chaldean",
    "NUMEROLOGY_PYTHAGOREAN_BALLIETT_1908_V1": "pythagorean",
}

#: Phase 6 Kuja rules and what each says about the partner's chart.
KUJA_RULES = {
    "BPHS_KAPOOR_80_47_49_MARS_HOUSES": "bphs_80_49",
    "JP_KUJA_DOSHA": None,
}


class _Record(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


# --------------------------------------------------------------------------
# Compatibility
# --------------------------------------------------------------------------


class PlacementRecord(_Record):
    participant: str
    birth_time_status: str
    nakshatra: str | None = None
    pada: int | None = None
    rashi: str | None = None


class FactorRecord(_Record):
    factor_id: str
    status: str
    reason: str | None = None
    points: float | None = None
    max_points: float | None = None
    classification: str | None = None
    role_dependent: bool
    role_invariant: bool | None = None
    label: str
    facts: dict[str, Any] = {}

    @model_validator(mode="after")
    def _check(self) -> FactorRecord:
        evaluated = self.status == _EVALUATED
        if evaluated == (self.reason is not None):
            raise ValueError(f"{self.factor_id}: a reason exactly when not evaluated")
        if not evaluated and (self.points is not None or self.classification is not None):
            raise ValueError(f"{self.factor_id}: no outcome when not evaluated")
        if evaluated and self.role_dependent and self.role_invariant is not True:
            raise ValueError(f"{self.factor_id}: a role-dependent result must be role-invariant")
        if self.points is not None and self.max_points is not None:
            if not 0 <= self.points <= self.max_points:
                raise ValueError(f"{self.factor_id}: points out of range")
        return self


class DoshaRecord(_Record):
    dosha_id: str
    state: str
    reason: str | None = None
    exception_conditions: dict[str, bool | None] = {}
    cancellation_state: str


class AshtakootTotalRecord(_Record):
    status: str
    reason: str | None = None
    points: float | None = None
    max_points: float
    missing_factors: tuple[str, ...] = ()


class PoruthamSummaryRecord(_Record):
    agreements: int
    disagreements: int
    neutral: int
    not_evaluable: int


class PolicyRecord(_Record):
    participant: str
    minimum_age_met: bool | None = None
    reason: str | None = None


class KujaReadingComparison(_Record):
    rule_id: str
    reading_id: str
    detected_a: str
    detected_b: str
    #: `source_condition_met` only for BPHS v. 49 with both partners detected.
    partner_condition: str


class KujaPartnerComparison(_Record):
    ruleset_content_hash: str
    readings: tuple[KujaReadingComparison, ...]
    statement: str = (
        "Each person's Phase 6 Kuja result, reading by reading. BPHS Ch. 80 v. 49 says the "
        "yoga ceases when both partners have it; Jataka Parijata's passage read gives no "
        "partner rule. Reported without a verdict."
    )


class CompatibilityEvidence(_Record):
    system: str
    profile_id: str
    methodology_version: str
    standards_version: str
    engine_version: str
    status: str
    reason: str | None = None
    as_of_date: str
    minimum_age_years: int
    policy_checks: tuple[PolicyRecord, ...] = ()
    placements: tuple[PlacementRecord, ...] = ()
    factors: tuple[FactorRecord, ...] = ()
    doshas: tuple[DoshaRecord, ...] = ()
    ashtakoot_total: AshtakootTotalRecord | None = None
    porutham_summary: PoruthamSummaryRecord | None = None
    unresolved_choices: tuple[str, ...] = ()
    not_implemented: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    kuja_partner_comparison: KujaPartnerComparison | None = None
    facts_hash: str

    @model_validator(mode="after")
    def _check(self) -> CompatibilityEvidence:
        if PROFILE_SYSTEM.get(self.profile_id) != self.system:
            raise ValueError("compatibility: unknown profile or profile/system mismatch")
        if self.status in _REFUSALS:
            if self.reason is None:
                raise ValueError("compatibility: a refused result needs a reason")
            if (
                self.placements
                or self.factors
                or self.doshas
                or self.ashtakoot_total
                or self.porutham_summary
            ):
                raise ValueError("compatibility: a refused result carries no facts")
            return self
        ids = tuple(f.factor_id for f in self.factors)
        evaluated = [f for f in self.factors if f.status == _EVALUATED]
        if self.profile_id == ASHTAKOOT_PROFILE:
            if ids != ASHTAKOOT_FACTORS:
                raise ValueError("compatibility: the Ashtakoot needs exactly its eight kutas")
            if self.porutham_summary is not None or any(f.classification for f in self.factors):
                raise ValueError("compatibility: an Ashtakoot result carries no porutham outcome")
            total = self.ashtakoot_total
            if total is None:
                raise ValueError("compatibility: an Ashtakoot result carries its total record")
            if len(evaluated) == len(ids):
                expected = sum(f.points or 0.0 for f in self.factors)
                if total.status != _EVALUATED or total.points != expected:
                    raise ValueError("compatibility: the total must equal the eight kutas' sum")
            elif total.status == _EVALUATED or total.points is not None:
                raise ValueError("compatibility: no 36-point total from a partial set of kutas")
        else:
            if ids != PORUTHAM_FACTORS:
                raise ValueError("compatibility: the ten poruthams need exactly their ten ids")
            if self.ashtakoot_total is not None or any(f.points is not None for f in self.factors):
                raise ValueError("compatibility: a porutham result carries no points or total")
            summary = self.porutham_summary
            if summary is None or summary.not_evaluable != len(ids) - len(evaluated):
                raise ValueError("compatibility: the porutham summary does not match")
        if self.status == "complete" and len(evaluated) != len(ids):
            raise ValueError("compatibility: 'complete' needs every factor evaluated")
        return self


def compatibility_evidence_from_facts(
    facts: Mapping[str, Any], kuja: KujaPartnerComparison | None = None
) -> CompatibilityEvidence:
    """One astro-engine `CompatibilityFacts` in JSON form, plus an optional
    Kuja comparison from `kuja_partner_comparison`."""
    if not isinstance(facts, Mapping):
        raise FactsError("compatibility: expected an object")
    try:
        copied = set(CompatibilityEvidence.model_fields) - {
            "not_implemented",
            "provenance_ids",
            "kuja_partner_comparison",
            "facts_hash",
        }
        return CompatibilityEvidence(
            **{key: facts[key] for key in copied if key in facts},
            not_implemented=tuple(item["item"] for item in facts.get("not_implemented", ())),
            provenance_ids=tuple(p["entry_id"] for p in facts.get("provenance", ())),
            kuja_partner_comparison=kuja,
            facts_hash=sha256_hex(canonical_json(dict(facts))),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"compatibility: malformed facts ({exc})") from exc


def kuja_partner_comparison(
    results_a: Sequence[RuleResult],
    results_b: Sequence[RuleResult],
    ruleset_hash_a: str,
    ruleset_hash_b: str,
) -> KujaPartnerComparison:
    """Compare two people's Phase 6 Kuja results (from two bundles built with
    the same ruleset). Detected statuses are the readings' own conditions,
    before the partner dependency made the BPHS rule not evaluable."""
    if ruleset_hash_a != ruleset_hash_b:
        raise FactsError("kuja: the two bundles were built with different rulesets")
    by_id_a = {r.rule_id: r for r in results_a}
    by_id_b = {r.rule_id: r for r in results_b}
    rows: list[KujaReadingComparison] = []
    for rule_id, partner_rule in KUJA_RULES.items():
        if rule_id not in by_id_a or rule_id not in by_id_b:
            raise FactsError(f"kuja: rule {rule_id} is missing from a bundle")
        readings_b = {r.reading_id: r for r in by_id_b[rule_id].readings}
        for reading in by_id_a[rule_id].readings:
            other = readings_b.get(reading.reading_id)
            if other is None:
                raise FactsError(f"kuja: reading {reading.reading_id} missing from a bundle")
            a, b = reading.detected_status, other.detected_status
            if partner_rule is None:
                condition = "not_specified_by_source"
            elif Status.NOT_EVALUABLE in (a, b):
                condition = "not_evaluable"
            elif a is Status.TRIGGERED and b is Status.TRIGGERED:
                condition = "source_condition_met"
            else:
                condition = "source_condition_not_met"
            rows.append(
                KujaReadingComparison(
                    rule_id=rule_id,
                    reading_id=reading.reading_id,
                    detected_a=a.value,
                    detected_b=b.value,
                    partner_condition=condition,
                )
            )
    return KujaPartnerComparison(ruleset_content_hash=ruleset_hash_a, readings=tuple(rows))


# --------------------------------------------------------------------------
# Numerology
# --------------------------------------------------------------------------


class ReductionRecord(_Record):
    chain: tuple[int, ...]
    value: int
    compound: int | None = None
    master_retained: bool


class NumberRecord(_Record):
    item_id: str
    status: str
    reason: str | None = None
    label: str
    reduction: ReductionRecord | None = None

    @model_validator(mode="after")
    def _check(self) -> NumberRecord:
        if (self.status == _EVALUATED) != (self.reduction is not None):
            raise ValueError(f"{self.item_id}: a reduction exactly when evaluated")
        if (self.status == _EVALUATED) == (self.reason is not None):
            raise ValueError(f"{self.item_id}: a reason exactly when not evaluated")
        if self.reduction is not None and self.reduction.chain[-1] != self.reduction.value:
            raise ValueError(f"{self.item_id}: the chain must end with the value")
        return self


class NameNumberRecord(_Record):
    status: str
    reason: str | None = None
    word_count: int
    reduction: ReductionRecord | None = None


class NumerologyEvidence(_Record):
    system: str
    profile_id: str
    methodology_version: str
    standards_version: str
    engine_version: str
    master_number_policy: str
    date_supplied: bool
    moolank: NumberRecord
    bhagyank: NumberRecord
    date_numbers: tuple[NumberRecord, ...] = ()
    name_number: NameNumberRecord
    associated_numbers_status: str
    interpretation_status: str
    provenance_ids: tuple[str, ...] = ()
    facts_hash: str

    @model_validator(mode="after")
    def _check(self) -> NumerologyEvidence:
        if NUMEROLOGY_PROFILES.get(self.profile_id) != self.system:
            raise ValueError("numerology: unknown profile or profile/system mismatch")
        if self.system == "chaldean" and self.master_number_policy != "none":
            raise ValueError("numerology: the Chaldean profile retains no master numbers")
        reductions = [r.reduction for r in (self.moolank, self.bhagyank, *self.date_numbers)]
        reductions.append(self.name_number.reduction)
        if self.master_number_policy == "none" and any(
            r is not None and r.master_retained for r in reductions
        ):
            raise ValueError("numerology: a master number retained under policy 'none'")
        return self


def numerology_evidence_from_facts(facts: Mapping[str, Any]) -> NumerologyEvidence:
    """One astro-engine `NumerologyFacts` in JSON form. The name and the date
    of birth are not copied (the hash pins them)."""
    if not isinstance(facts, Mapping):
        raise FactsError("numerology: expected an object")
    try:
        name = facts["name_number"]
        return NumerologyEvidence(
            system=facts["system"],
            profile_id=facts["profile_id"],
            methodology_version=facts["methodology_version"],
            standards_version=facts["standards_version"],
            engine_version=facts["engine_version"],
            master_number_policy=facts["master_number_policy"],
            date_supplied=facts.get("date_of_birth") is not None,
            moolank=facts["moolank"],
            bhagyank=facts["bhagyank"],
            date_numbers=tuple(facts.get("date_numbers", ())),
            name_number=NameNumberRecord(
                status=name["status"],
                reason=name.get("reason"),
                word_count=len(name.get("words", ())),
                reduction=name.get("reduction"),
            ),
            associated_numbers_status=facts["associated_numbers"]["status"],
            interpretation_status=facts["interpretation"]["status"],
            provenance_ids=tuple(p["entry_id"] for p in facts.get("provenance", ())),
            facts_hash=sha256_hex(canonical_json(dict(facts))),
        )
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise FactsError(f"numerology: malformed facts ({exc})") from exc
