"""Palm fact, rule-evaluation and evidence-bundle contracts (Phase 13).

Specification: `research/PALM_READING.md` section 8 and 15; standards PM-14 to PM-16, PM-25
to PM-31. The vision service (`services/palm-vision`) produces :class:`PalmFactSet`; the rule
engine (palm ruleset) produces :class:`PalmRuleEvaluation`; :func:`build_palm_evidence_bundle`
joins them for later phases.

Invariants enforced here, not only documented:

* a :class:`PalmFact` is OBSERVED or DERIVED. INTERPRETED is not a fact class: interpretation
  exists only in :class:`PalmRuleEvaluation`;
* every identifier is content-addressed (``fact_id`` from ``fact_hash``) and verified when the
  object is built, so a tampered or inconsistent fact cannot be constructed;
* no floating-point number is part of the canonical form (:mod:`pandit_contracts.palm_canonical`);
* timestamps and other runtime fields are excluded from every content identity;
* an image is referenced by content hash and identifier, never embedded.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

from pandit_contracts.palm_canonical import (
    BASIS_POINTS,
    canonical_json,
    hash_list,
    is_sha256_hex,
    sha256_hex,
)

PALM_SCHEMA_VERSION = "1.0.0"
PALM_BUNDLE_VERSION = "1.0.0"
PALM_STANDARDS_VERSION = "1.28.0"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ----------------------------------------------------------------------------- vocabularies
class FactClass(str, Enum):
    """INTERPRETED is deliberately absent: an interpretation is never a palm fact."""

    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"


class HandSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UNDETERMINED = "UNDETERMINED"


class VisibilityState(str, Enum):
    CLEAR = "CLEAR"
    PARTIAL = "PARTIAL"
    OCCLUDED = "OCCLUDED"
    NOT_VISIBLE = "NOT_VISIBLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class FactType(str, Enum):
    HAND_SIDE = "HAND_SIDE"
    PALM_REGION = "PALM_REGION"
    LANDMARK_SET = "LANDMARK_SET"
    LINE_TRACK = "LINE_TRACK"
    LINE_ROLE_CANDIDATE = "LINE_ROLE_CANDIDATE"
    LINE_ATTRIBUTE = "LINE_ATTRIBUTE"
    LINE_BREAK = "LINE_BREAK"
    LINE_BRANCH = "LINE_BRANCH"
    LINE_INTERSECTION = "LINE_INTERSECTION"
    REGION_GEOMETRY = "REGION_GEOMETRY"
    MOUNT_REGION = "MOUNT_REGION"
    RATIO = "RATIO"


class QualityOutcome(str, Enum):
    ACCEPT = "ACCEPT"
    RETRY = "RETRY"
    REJECT = "REJECT"


class QualityCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"  # a threshold is uncalibrated or the metric could not be measured
    NOT_EVALUATED = "NOT_EVALUATED"  # a prerequisite failed (no hand, undecodable image)


class CalibrationStatus(str, Enum):
    CALIBRATION_REQUIRED = "CALIBRATION_REQUIRED"
    FIXTURE_ONLY = "FIXTURE_ONLY"  # values for tests and synthetic fixtures, never production
    CALIBRATED = "CALIBRATED"


class LineAnalysisStatus(str, Enum):
    """Honest state of the palm-line analysis (decision: infrastructure is not a model)."""

    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_UNVALIDATED = "MODEL_UNVALIDATED"  # an artifact exists but has no validation report
    BASELINE_EXPERIMENTAL = "BASELINE_EXPERIMENTAL"
    FIXTURE_SYNTHETIC = "FIXTURE_SYNTHETIC"
    TRAINED_MODEL = "TRAINED_MODEL"


class RuleStatus(str, Enum):
    TRIGGERED = "TRIGGERED"
    NOT_TRIGGERED = "NOT_TRIGGERED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


# ----------------------------------------------------------------------------- value objects
class ImageRef(_Frozen):
    """A content-addressed reference. The bytes are never part of a fact."""

    image_id: str = Field(min_length=1)
    content_sha256: str

    @model_validator(mode="after")
    def _hash(self) -> ImageRef:
        if not is_sha256_hex(self.content_sha256):
            raise ValueError("content_sha256 must be 64 lower-case hex characters")
        return self


class ConfidenceScore(_Frozen):
    """Integer basis points. A probability only when ``calibrated`` and a calibration is named."""

    score_bp: StrictInt = Field(ge=0, le=BASIS_POINTS)
    calibrated: bool = False
    calibration_id: str | None = None

    @model_validator(mode="after")
    def _calibration(self) -> ConfidenceScore:
        if self.calibrated != (self.calibration_id is not None):
            raise ValueError("calibrated requires a calibration_id and the reverse")
        return self


class Uncertainty(_Frozen):
    kind: Literal["NONE", "INTERVAL", "SPREAD"] = "NONE"
    lo_fixed: StrictInt | None = None
    hi_fixed: StrictInt | None = None

    @model_validator(mode="after")
    def _bounds(self) -> Uncertainty:
        if self.kind == "NONE":
            if self.lo_fixed is not None or self.hi_fixed is not None:
                raise ValueError("kind NONE carries no bounds")
        elif self.lo_fixed is None or self.hi_fixed is None or self.lo_fixed > self.hi_fixed:
            raise ValueError("an interval or spread needs lo_fixed <= hi_fixed")
        return self


class Visibility(_Frozen):
    state: VisibilityState
    reason: str | None = None

    @model_validator(mode="after")
    def _reason(self) -> Visibility:
        if self.state is VisibilityState.NOT_EVALUABLE and not self.reason:
            raise ValueError("NOT_EVALUABLE needs a reason")
        return self


class Geometry(_Frozen):
    """Fixed-point coordinates in the palm-canonical frame (``PCF-1``, 10^-4 palm unit)."""

    frame_id: Literal["PCF-1"] = "PCF-1"
    kind: Literal["POINT", "POLYLINE", "POLYGON", "POINT_SET"]
    coords_fixed: tuple[tuple[StrictInt, StrictInt], ...]
    sampling_spec: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> Geometry:
        n = len(self.coords_fixed)
        if self.kind == "POINT" and n != 1:
            raise ValueError("a POINT has exactly one coordinate")
        if self.kind == "POLYLINE" and n < 2:
            raise ValueError("a POLYLINE has at least two coordinates")
        if self.kind == "POLYGON" and n < 3:
            raise ValueError("a POLYGON has at least three coordinates")
        return self


class FactValue(_Frozen):
    kind: Literal["NONE", "INT", "ENUM", "BOOL", "RATIO_FIXED"] = "NONE"
    v: StrictBool | StrictInt | StrictStr | None = None
    unit: str | None = None

    @model_validator(mode="after")
    def _kind(self) -> FactValue:
        ok = {
            "NONE": self.v is None,
            "INT": isinstance(self.v, int) and not isinstance(self.v, bool),
            "RATIO_FIXED": isinstance(self.v, int) and not isinstance(self.v, bool),
            "ENUM": isinstance(self.v, str),
            "BOOL": isinstance(self.v, bool),
        }
        if not ok[self.kind]:
            raise ValueError(f"value does not match kind {self.kind}")
        return self


class Derivation(_Frozen):
    method_id: str
    method_version: str


class Labelling(_Frozen):
    """A palmistry name given to a detected structure (a DERIVED fact, profile-specific)."""

    source_profile: str
    source_id: str
    source_location: str
    rule: str


class ModelArtifactRef(_Frozen):
    """Identity of a model artifact used by the pipeline (policy: no artifact, no claim)."""

    artifact_id: str
    version: str
    sha256: str | None = None
    role: str
    licence_id: str | None = None

    @model_validator(mode="after")
    def _hash(self) -> ModelArtifactRef:
        if self.sha256 is not None and not is_sha256_hex(self.sha256):
            raise ValueError("sha256 must be 64 lower-case hex characters")
        return self


class RuntimeIdentity(_Frozen):
    python: str
    packages: tuple[tuple[str, str], ...] = ()  # sorted (name, version) pairs
    device_class: str = "CPU"
    determinism_mode: str = "UNSPECIFIED"
    threads: int | None = None


class Provenance(_Frozen):
    """What produced a fact set: exact image, pipeline, models, configuration and runtime."""

    pipeline_version: str
    preprocessing_id: str
    preprocessing_version: str
    parameters_sha256: str
    normalized_input_sha256: str
    quality_config_id: str
    quality_config_version: str
    quality_calibration_status: CalibrationStatus
    inference_config_sha256: str
    line_analysis_status: LineAnalysisStatus
    models: tuple[ModelArtifactRef, ...] = ()
    runtime: RuntimeIdentity

    @property
    def provenance_id(self) -> str:
        return "PV-" + sha256_hex(self.model_dump(mode="json"))[:16]


class QualityCheckResult(_Frozen):
    check: str
    status: QualityCheckStatus
    metric_fixed: StrictInt | None = None  # measured value, fixed-point (scale per check)
    threshold_fixed: StrictInt | None = None
    reason: str | None = None


class QualityResult(_Frozen):
    outcome: QualityOutcome
    checks: tuple[QualityCheckResult, ...]
    reasons: tuple[str, ...] = ()
    config_id: str
    config_version: str
    calibration_status: CalibrationStatus

    @property
    def quality_ref(self) -> str:
        return "QR-" + sha256_hex(self.model_dump(mode="json"))[:16]


# ----------------------------------------------------------------------------- the fact
class PalmFact(_Frozen):
    schema_version: str = PALM_SCHEMA_VERSION
    fact_id: str
    fact_hash: str
    analysis_id: str
    fact_class: FactClass
    fact_type: FactType
    hand_side: HandSide
    region_id: str | None = None
    geometry: Geometry | None = None
    value: FactValue = Field(default_factory=FactValue)
    confidence: ConfidenceScore
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    visibility: Visibility
    quality_ref: str
    derived_from: tuple[str, ...] = ()
    derivation: Derivation | None = None
    labelling: Labelling | None = None
    provenance: str  # the provenance_id of a block carried by the PalmFactSet
    image_ref: ImageRef

    @model_validator(mode="after")
    def _consistent(self) -> PalmFact:
        if self.fact_class is FactClass.OBSERVED and (self.derived_from or self.derivation):
            raise ValueError("an OBSERVED fact has no derivation")
        if self.fact_class is FactClass.DERIVED and not (self.derived_from and self.derivation):
            raise ValueError("a DERIVED fact names its source facts and its method")
        if self.labelling is not None and self.fact_class is not FactClass.DERIVED:
            raise ValueError("a palmistry label is a DERIVED fact, never an OBSERVED one")
        digest = fact_hash_of(self)
        if self.fact_hash != digest:
            raise ValueError("fact_hash does not match the canonical content")
        if self.fact_id != "PF-" + digest[:16]:
            raise ValueError("fact_id does not match fact_hash")
        return self


def _fact_content(fact_like: Any) -> dict[str, Any]:
    data: dict[str, Any] = fact_like.model_dump(mode="json")
    data.pop("fact_id", None)
    data.pop("fact_hash", None)
    return data


def fact_hash_of(fact: PalmFact) -> str:
    return sha256_hex(_fact_content(fact))


class PalmFactContent(_Frozen):
    """A fact without its identifiers: the exact content that is hashed."""

    schema_version: str = PALM_SCHEMA_VERSION
    analysis_id: str
    fact_class: FactClass
    fact_type: FactType
    hand_side: HandSide
    region_id: str | None = None
    geometry: Geometry | None = None
    value: FactValue = Field(default_factory=FactValue)
    confidence: ConfidenceScore
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    visibility: Visibility
    quality_ref: str
    derived_from: tuple[str, ...] = ()
    derivation: Derivation | None = None
    labelling: Labelling | None = None
    provenance: str
    image_ref: ImageRef


def build_palm_fact(**fields: Any) -> PalmFact:
    """Construct a fact, computing ``fact_hash`` and ``fact_id`` from its canonical content."""
    content = PalmFactContent(**fields)
    digest = sha256_hex(content.model_dump(mode="json"))
    return PalmFact(**fields, fact_id="PF-" + digest[:16], fact_hash=digest)


# ----------------------------------------------------------------------------- the fact set
class PalmFactSet(_Frozen):
    schema_version: str = PALM_SCHEMA_VERSION
    analysis_id: str
    image_ref: ImageRef
    quality_result: QualityResult
    facts: tuple[PalmFact, ...]
    provenance_blocks: tuple[Provenance, ...]
    fact_set_hash: str
    # Runtime fields: never part of any content identity (PM-14).
    created_at: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> PalmFactSet:
        provenance_ids = {p.provenance_id for p in self.provenance_blocks}
        fact_ids = {f.fact_id for f in self.facts}
        if len(fact_ids) != len(self.facts):
            raise ValueError("duplicate fact identifiers")
        quality_ref = self.quality_result.quality_ref
        for fact in self.facts:
            if fact.analysis_id != self.analysis_id:
                raise ValueError(f"{fact.fact_id}: analysis_id differs from the fact set")
            if fact.image_ref != self.image_ref:
                raise ValueError(f"{fact.fact_id}: image_ref differs from the fact set")
            if fact.provenance not in provenance_ids:
                raise ValueError(f"{fact.fact_id}: unknown provenance block")
            if fact.quality_ref != quality_ref:
                raise ValueError(f"{fact.fact_id}: quality_ref differs from the quality result")
            for parent in fact.derived_from:
                if parent not in fact_ids:
                    raise ValueError(f"{fact.fact_id}: derived_from names an unknown fact")
        if self.fact_set_hash != compute_fact_set_hash(self.facts):
            raise ValueError("fact_set_hash does not match the facts")
        return self

    def fact(self, fact_id: str) -> PalmFact:
        for fact in self.facts:
            if fact.fact_id == fact_id:
                return fact
        raise KeyError(fact_id)

    def facts_of_type(self, fact_type: FactType) -> tuple[PalmFact, ...]:
        return tuple(f for f in self.facts if f.fact_type is fact_type)


def compute_fact_set_hash(facts: tuple[PalmFact, ...] | list[PalmFact]) -> str:
    """SHA-256 over the sorted fact hashes (order never matters; timestamps never enter)."""
    return hash_list([f.fact_hash for f in facts])


def build_palm_fact_set(
    *,
    analysis_id: str,
    image_ref: ImageRef,
    quality_result: QualityResult,
    facts: list[PalmFact],
    provenance_blocks: list[Provenance],
    created_at: str | None = None,
) -> PalmFactSet:
    ordered = sorted(facts, key=lambda f: f.fact_id)
    blocks = sorted(provenance_blocks, key=lambda p: p.provenance_id)
    return PalmFactSet(
        analysis_id=analysis_id,
        image_ref=image_ref,
        quality_result=quality_result,
        facts=tuple(ordered),
        provenance_blocks=tuple(blocks),
        fact_set_hash=compute_fact_set_hash(ordered),
        created_at=created_at,
    )


def make_analysis_id(image_ref: ImageRef, provenance: Provenance) -> str:
    """Deterministic: the same image and the same pipeline identity give the same analysis."""
    return (
        "PA-"
        + sha256_hex({"image": image_ref.content_sha256, "provenance": provenance.provenance_id})[
            :16
        ]
    )


# ----------------------------------------------------------------------------- rule evaluation
class PalmRuleEvaluation(_Frozen):
    """The INTERPRETED layer: a source-backed rule evaluated over palm facts. Tags only."""

    rule_id: str
    rule_version: str
    source_profile: str
    source_location: str
    status: RuleStatus
    fact_refs: tuple[str, ...] = ()
    knowledge_version: str
    # Kept from the research specification (no contradiction with the final lock):
    ruleset_id: str
    source_id: str
    standards_version: str
    interpretation_tags: tuple[str, ...] = ()
    reason: str | None = None  # why NOT_EVALUABLE / NOT_TRIGGERED
    conflict_ids: tuple[str, ...] = ()  # recorded UNRESOLVED_CONFLICT items touching this rule

    @model_validator(mode="after")
    def _consistent(self) -> PalmRuleEvaluation:
        if self.status is RuleStatus.NOT_EVALUABLE and not self.reason:
            raise ValueError("NOT_EVALUABLE needs a reason")
        if self.status is not RuleStatus.TRIGGERED and self.interpretation_tags:
            raise ValueError("only a TRIGGERED rule carries interpretation tags")
        if self.status is RuleStatus.TRIGGERED and not self.fact_refs:
            raise ValueError("a TRIGGERED rule cites the facts that triggered it")
        return self

    @property
    def evaluation_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


# ----------------------------------------------------------------------------- evidence bundle
class SourceRef(_Frozen):
    source_profile: str
    source_id: str
    source_location: str


class UncertaintySummary(_Frozen):
    facts_total: int
    by_visibility: tuple[tuple[str, int], ...]
    min_confidence_bp: int | None
    rules_by_status: tuple[tuple[str, int], ...]


class PalmEvidenceBundle(_Frozen):
    """Everything a later phase needs to verify a palm claim without pixels (PM-16)."""

    bundle_version: str = PALM_BUNDLE_VERSION
    analysis_id: str
    standards_version: str
    knowledge_version: str
    image_ref: ImageRef
    quality_result: QualityResult
    hand_fact_ids: tuple[str, ...]
    region_fact_ids: tuple[str, ...]
    landmark_fact_ids: tuple[str, ...]
    line_fact_ids: tuple[str, ...]
    fact_set: PalmFactSet
    rule_evaluations: tuple[PalmRuleEvaluation, ...]
    source_refs: tuple[SourceRef, ...]
    model_versions: tuple[ModelArtifactRef, ...]
    uncertainty_summary: UncertaintySummary
    production_ready: bool
    readiness_blockers: tuple[str, ...]
    bundle_hash: str

    @model_validator(mode="after")
    def _consistent(self) -> PalmEvidenceBundle:
        if self.fact_set.analysis_id != self.analysis_id:
            raise ValueError("fact set belongs to another analysis")
        known = {f.fact_id for f in self.fact_set.facts}
        for ev in self.rule_evaluations:
            for ref in ev.fact_refs:
                if ref not in known:
                    raise ValueError(f"{ev.rule_id}: fact_refs names a fact not in the bundle")
            if ev.knowledge_version != self.knowledge_version:
                raise ValueError(f"{ev.rule_id}: knowledge_version differs from the bundle")
        if self.bundle_hash != bundle_hash_of(self):
            raise ValueError("bundle_hash does not match the bundle content")
        return self

    def claimable_ids(self) -> frozenset[str]:
        """Identifiers a later phase may cite: fact ids and rule ids (never pixels)."""
        return frozenset(
            {f.fact_id for f in self.fact_set.facts} | {e.rule_id for e in self.rule_evaluations}
        )

    def is_claim_supported(self, cited_id: str) -> bool:
        """Phase 16 interface: a claim that cites an id absent from the bundle is unsupported."""
        return cited_id in self.claimable_ids()

    def triggered(self) -> tuple[PalmRuleEvaluation, ...]:
        return tuple(e for e in self.rule_evaluations if e.status is RuleStatus.TRIGGERED)


def bundle_hash_of(bundle: PalmEvidenceBundle) -> str:
    content = bundle.model_dump(mode="json")
    content.pop("bundle_hash", None)
    # runtime fields never enter the identity
    content["fact_set"].pop("created_at", None)
    return sha256_hex(content)


_HAND_TYPES = {FactType.HAND_SIDE}
_REGION_TYPES = {FactType.PALM_REGION, FactType.MOUNT_REGION, FactType.REGION_GEOMETRY}
_LANDMARK_TYPES = {FactType.LANDMARK_SET}
_LINE_TYPES = {
    FactType.LINE_TRACK,
    FactType.LINE_ROLE_CANDIDATE,
    FactType.LINE_ATTRIBUTE,
    FactType.LINE_BREAK,
    FactType.LINE_BRANCH,
    FactType.LINE_INTERSECTION,
}


def readiness_blockers(fact_set: PalmFactSet) -> tuple[str, ...]:
    """Honest reasons a bundle is not production-ready (never silently empty)."""
    blockers: set[str] = set()
    for prov in fact_set.provenance_blocks:
        if prov.line_analysis_status is not LineAnalysisStatus.TRAINED_MODEL:
            blockers.add(f"LINE_ANALYSIS_{prov.line_analysis_status.value}")
        if prov.quality_calibration_status is not CalibrationStatus.CALIBRATED:
            blockers.add(f"QUALITY_THRESHOLDS_{prov.quality_calibration_status.value}")
        for model in prov.models:
            if model.sha256 is None or model.licence_id is None:
                blockers.add(f"MODEL_ARTIFACT_UNVERIFIED_{model.artifact_id}")
    blockers.add("REPRODUCIBILITY_TOLERANCES_CALIBRATION_REQUIRED")
    blockers.add("LEGAL_REVIEW_GATE_OPEN")
    return tuple(sorted(blockers))


def build_palm_evidence_bundle(
    *,
    fact_set: PalmFactSet,
    rule_evaluations: list[PalmRuleEvaluation],
    knowledge_version: str,
    source_refs: list[SourceRef] | None = None,
    standards_version: str = PALM_STANDARDS_VERSION,
) -> PalmEvidenceBundle:
    """Join a fact set and its rule evaluations into one bundle with a content hash."""
    evaluations = sorted(rule_evaluations, key=lambda e: (e.rule_id, e.rule_version))
    refs = sorted(
        {(e.source_profile, e.source_id, e.source_location) for e in evaluations}
        | {(r.source_profile, r.source_id, r.source_location) for r in (source_refs or [])}
    )
    facts = fact_set.facts

    def ids(types: set[FactType]) -> tuple[str, ...]:
        return tuple(sorted(f.fact_id for f in facts if f.fact_type in types))

    visibility: dict[str, int] = {}
    for fact in facts:
        visibility[fact.visibility.state.value] = visibility.get(fact.visibility.state.value, 0) + 1
    statuses: dict[str, int] = {}
    for ev in evaluations:
        statuses[ev.status.value] = statuses.get(ev.status.value, 0) + 1
    models: dict[tuple[str, str, str], ModelArtifactRef] = {}
    for prov in fact_set.provenance_blocks:
        for model in prov.models:
            models[(model.artifact_id, model.version, model.role)] = model
    blockers = readiness_blockers(fact_set)
    draft: dict[str, Any] = {
        "analysis_id": fact_set.analysis_id,
        "standards_version": standards_version,
        "knowledge_version": knowledge_version,
        "image_ref": fact_set.image_ref,
        "quality_result": fact_set.quality_result,
        "hand_fact_ids": ids(_HAND_TYPES),
        "region_fact_ids": ids(_REGION_TYPES),
        "landmark_fact_ids": ids(_LANDMARK_TYPES),
        "line_fact_ids": ids(_LINE_TYPES),
        "fact_set": fact_set,
        "rule_evaluations": tuple(evaluations),
        "source_refs": tuple(
            SourceRef(source_profile=p, source_id=s, source_location=loc) for p, s, loc in refs
        ),
        "model_versions": tuple(models[k] for k in sorted(models)),
        "uncertainty_summary": UncertaintySummary(
            facts_total=len(facts),
            by_visibility=tuple(sorted(visibility.items())),
            min_confidence_bp=min((f.confidence.score_bp for f in facts), default=None),
            rules_by_status=tuple(sorted(statuses.items())),
        ),
        "production_ready": not blockers,
        "readiness_blockers": blockers,
    }
    unsigned = PalmEvidenceBundleContent(**draft)
    content = unsigned.model_dump(mode="json")
    content["fact_set"].pop("created_at", None)
    return PalmEvidenceBundle(**draft, bundle_hash=sha256_hex(content))


class PalmEvidenceBundleContent(_Frozen):
    """The bundle without its hash (the exact content that is hashed)."""

    bundle_version: str = PALM_BUNDLE_VERSION
    analysis_id: str
    standards_version: str
    knowledge_version: str
    image_ref: ImageRef
    quality_result: QualityResult
    hand_fact_ids: tuple[str, ...]
    region_fact_ids: tuple[str, ...]
    landmark_fact_ids: tuple[str, ...]
    line_fact_ids: tuple[str, ...]
    fact_set: PalmFactSet
    rule_evaluations: tuple[PalmRuleEvaluation, ...]
    source_refs: tuple[SourceRef, ...]
    model_versions: tuple[ModelArtifactRef, ...]
    uncertainty_summary: UncertaintySummary
    production_ready: bool
    readiness_blockers: tuple[str, ...]


def canonical_form(model: BaseModel) -> str:
    """The canonical JSON of any contract object (floats raise)."""
    return canonical_json(model.model_dump(mode="json"))
