"""Dataset manifest and governance checks (Phase 13; standards PM-18, PM-19, PM-30).

This is the *interface* a consented dataset must satisfy; no dataset exists and none is
committed to git. A manifest lists, per image: identifiers, a content hash, a pseudonymous
contributor, the split, capture conditions, and the consent record, never pixels.

Governance enforced by :func:`validate_manifest`:

* **no silent user images**: every non-synthetic record names a consent record and attests an
  adult contributor; a record from production uploads is not a field of the schema;
* **contributor-independent splits**: a contributor appears in exactly one split;
* **no leakage**: a content hash appears in exactly one split;
* **no mandatory skin-tone (or any demographic) labels**: the schema forbids undeclared fields,
  so a ``skin_tone`` column cannot be added without changing the schema;
* **no prohibited label** (standards PM-13 and PM-25) in any label vocabulary;
* **diversity is reported, not assumed**: :func:`coverage_report` counts every stratum and lists
  the strata with no sample; it sets no target (stratum sizes are CALIBRATION_REQUIRED).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Literal

from pandit_contracts.palm import HandSide
from pandit_contracts.palm_canonical import is_sha256_hex, sha256_hex
from pandit_contracts.palm_policy import is_prohibited_label
from pydantic import BaseModel, ConfigDict, model_validator

Split = Literal["train", "validation", "test"]
LIGHTING = ("indoor", "outdoor", "mixed", "low")
BACKGROUND = ("plain", "cluttered", "textured")
RESOLUTION = ("low", "medium", "high")
ORIENTATION = ("upright", "rotated", "mirrored_capture")
OCCLUSION = ("none", "partial", "heavy")
ALLOWED_LABELS = frozenset(
    {
        "HAND_PRESENT",
        "HAND_SIDE",
        "LANDMARKS_21",
        "PALM_ROI_MASK",
        "LINE_TRACK_POLYLINE",
        "LINE_VISIBILITY",
        "IMAGE_ANALYSABLE",
        "ANALYSABLE_REASON",
    }
)
MANIFEST_SCHEMA_VERSION = "1"


class SampleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    image_id: str
    content_sha256: str
    contributor_id: str  # a pseudonym; never a name, contact or account identifier
    split: Split
    hand_side: HandSide
    device_id: str
    lighting: str
    background: str
    resolution: str
    orientation: str
    occlusion: str
    synthetic: bool = False
    consent_record_id: str | None = None
    adult_attested: bool = False
    annotation_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _checks(self) -> SampleRecord:
        if not is_sha256_hex(self.content_sha256):
            raise ValueError(f"{self.image_id}: content_sha256 must be a SHA-256")
        if self.hand_side is HandSide.UNDETERMINED:
            raise ValueError(f"{self.image_id}: a labelled sample has a known side")
        if not self.synthetic and not (self.consent_record_id and self.adult_attested):
            raise ValueError(
                f"{self.image_id}: a non-synthetic sample needs a consent record and an adult "
                "attestation (minors are excluded; no silent user images)"
            )
        return self


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = MANIFEST_SCHEMA_VERSION
    dataset_id: str
    dataset_version: str
    annotation_version: str
    guideline_version: str
    label_vocabulary: tuple[str, ...]
    synthetic: bool
    records: tuple[SampleRecord, ...]

    @property
    def manifest_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))


class ManifestError(ValueError):
    """The manifest violates the dataset governance rules."""


def validate_manifest(manifest: DatasetManifest) -> None:
    """Raise :class:`ManifestError` listing every governance violation."""
    problems: list[str] = []
    for label in manifest.label_vocabulary:
        if is_prohibited_label(label):
            problems.append(f"label {label!r} is in a prohibited interpretation category")
        elif label not in ALLOWED_LABELS:
            problems.append(f"label {label!r} is not an allowed annotation label")
    if manifest.synthetic != all(r.synthetic for r in manifest.records) and manifest.records:
        problems.append("manifest.synthetic must equal the synthetic flag of every record")
    ids = Counter(r.image_id for r in manifest.records)
    problems += [f"duplicate image_id {i}" for i, n in ids.items() if n > 1]
    by_contributor: dict[str, set[str]] = {}
    by_hash: dict[str, set[str]] = {}
    for rec in manifest.records:
        by_contributor.setdefault(rec.contributor_id, set()).add(rec.split)
        by_hash.setdefault(rec.content_sha256, set()).add(rec.split)
    for contributor, splits in sorted(by_contributor.items()):
        if len(splits) > 1:
            problems.append(f"contributor {contributor} appears in splits {sorted(splits)}")
    for digest, splits in sorted(by_hash.items()):
        if len(splits) > 1:
            problems.append(f"content hash {digest[:12]} leaks across splits {sorted(splits)}")
    if problems:
        raise ManifestError("; ".join(problems))


def coverage_report(manifest: DatasetManifest) -> dict[str, dict[str, int]]:
    """Counts per stratum, including strata with no sample. Sets no target."""

    def count(values: Sequence[str], expected: Sequence[str]) -> dict[str, int]:
        counted = Counter(values)
        out = {k: counted.get(k, 0) for k in expected}
        out.update({k: v for k, v in counted.items() if k not in out})
        return dict(sorted(out.items()))

    recs = manifest.records
    return {
        "split": count([r.split for r in recs], ("train", "validation", "test")),
        "hand_side": count([r.hand_side.value for r in recs], ("LEFT", "RIGHT")),
        "lighting": count([r.lighting for r in recs], LIGHTING),
        "background": count([r.background for r in recs], BACKGROUND),
        "resolution": count([r.resolution for r in recs], RESOLUTION),
        "orientation": count([r.orientation for r in recs], ORIENTATION),
        "occlusion": count([r.occlusion for r in recs], OCCLUSION),
        "device": count([r.device_id for r in recs], ()),
    }


def contributors_missing_a_hand(manifest: DatasetManifest) -> tuple[str, ...]:
    """Contributors who do not have both hands (the initial methodology wants both)."""
    sides: dict[str, set[str]] = {}
    for rec in manifest.records:
        sides.setdefault(rec.contributor_id, set()).add(rec.hand_side.value)
    return tuple(sorted(c for c, s in sides.items() if s != {"LEFT", "RIGHT"}))
