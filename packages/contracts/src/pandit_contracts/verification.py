"""Verification contracts (Phase 16).

The verification layer decides whether each generated claim of a ``NarrationResponse`` is supported
by trusted, deterministic evidence. It is the only layer allowed to produce ``VERIFIED``.

Invariants carried by these types:

* **Verified means supported by the encoded evidence and rule model.** It is not a statement that
  astrology or palmistry is scientifically valid, and it is not a statement about the real world.
* **Seven statuses, one precedence.** A claim ends in exactly one ``VerificationStatus``; only
  ``VERIFIED`` carries ``verified_by``.
* **Content-free audit.** Results hold identifiers, enumerated reason codes, hashes and versions.
  They never hold the claim text, a prompt, an image reference or model output (only a hash of the
  claim text, so a result can be matched to the claim it judged).
* **Deterministic.** Identical claim, evidence, rules, knowledge versions, verifier version and
  configuration give an identical result. There is deliberately no wall-clock timestamp.
* **Mixed outcomes are first-class.** One response carries one result per claim and an overall
  status; one unverifiable claim does not discard the rest.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from pandit_contracts.agent import ClaimType, Domain, EvidenceReference, UncertaintyFlag

VERIFICATION_CONTRACT_VERSION = "1.0.0"
VERIFIER_ID = "pandit-verification"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


class VerificationStatus(str, Enum):
    """The outcome for one claim. Exactly one applies."""

    VERIFIED = "VERIFIED"  # supported by trusted evidence and rules; the only verified outcome
    UNSUPPORTED = "UNSUPPORTED"  # the text asserts more, or something else, than the evidence
    UNVERIFIABLE = "UNVERIFIABLE"  # the verifier has no valid way to check this claim
    INVALID_REFERENCE = "INVALID_REFERENCE"  # a reference or provenance field does not resolve
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"  # contradicts the evidence, or merges profiles
    POLICY_BLOCKED = "POLICY_BLOCKED"  # prohibited content, forged authority or injection
    INSUFFICIENT_EVIDENCE = (
        "INSUFFICIENT_EVIDENCE"  # evidence is uncertain, missing or not evaluable
    )


class ReasonCode(str, Enum):
    """Why a claim ended where it did. Machine-readable; the detail never carries claim text."""

    # support
    SUPPORTED = "SUPPORTED"
    LIMITATION_SUPPORTED = "LIMITATION_SUPPORTED"
    # structure and references
    MALFORMED_CLAIM = "MALFORMED_CLAIM"
    DUPLICATE_CLAIM_ID = "DUPLICATE_CLAIM_ID"
    MISSING_REFERENCE = "MISSING_REFERENCE"
    EVIDENCE_NOT_FOUND = "EVIDENCE_NOT_FOUND"
    BUNDLE_MISMATCH = "BUNDLE_MISMATCH"
    BUNDLE_INTEGRITY_FAILURE = "BUNDLE_INTEGRITY_FAILURE"
    DOMAIN_MISMATCH = "DOMAIN_MISMATCH"
    REFERENCE_KIND_MISMATCH = "REFERENCE_KIND_MISMATCH"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"
    KNOWLEDGE_VERSION_MISMATCH = "KNOWLEDGE_VERSION_MISMATCH"
    RULE_VERSION_MISMATCH = "RULE_VERSION_MISMATCH"
    RULESET_HASH_MISMATCH = "RULESET_HASH_MISMATCH"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    # semantic class
    SEMANTIC_CLASS_MISMATCH = "SEMANTIC_CLASS_MISMATCH"
    CLASS_MISREPRESENTED = "CLASS_MISREPRESENTED"
    # rules
    RULE_NOT_TRIGGERED = "RULE_NOT_TRIGGERED"
    RULE_NOT_EVALUABLE = "RULE_NOT_EVALUABLE"
    MISSING_REQUIRED_FACT = "MISSING_REQUIRED_FACT"
    RULE_WITHOUT_FACT_BASIS = "RULE_WITHOUT_FACT_BASIS"
    INTERPRETATION_WITHOUT_RULE = "INTERPRETATION_WITHOUT_RULE"
    # uncertainty
    EVIDENCE_NOT_EVALUABLE = "EVIDENCE_NOT_EVALUABLE"
    EVIDENCE_NOT_VISIBLE = "EVIDENCE_NOT_VISIBLE"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    CONFIDENCE_UNCALIBRATED = "CONFIDENCE_UNCALIBRATED"
    BUNDLE_NOT_PRODUCTION_READY = "BUNDLE_NOT_PRODUCTION_READY"
    UNCERTAINTY_UNDERSTATED = "UNCERTAINTY_UNDERSTATED"
    # source profiles
    CONFLICTING_PROFILES_MERGED = "CONFLICTING_PROFILES_MERGED"
    CONFLICT_PROFILE_NOT_NAMED = "CONFLICT_PROFILE_NOT_NAMED"
    MULTI_PROFILE_NOT_ATTRIBUTABLE = "MULTI_PROFILE_NOT_ATTRIBUTABLE"
    # semantics
    CONTRADICTS_EVIDENCE = "CONTRADICTS_EVIDENCE"
    SELF_CONTRADICTION = "SELF_CONTRADICTION"
    UNGROUNDED_ENTITY = "UNGROUNDED_ENTITY"
    UNGROUNDED_NUMBER = "UNGROUNDED_NUMBER"
    TOPIC_NOT_IN_EVIDENCE = "TOPIC_NOT_IN_EVIDENCE"
    VALENCE_NOT_IN_EVIDENCE = "VALENCE_NOT_IN_EVIDENCE"
    VALENCE_CONTRADICTS_EFFECT_CLASS = "VALENCE_CONTRADICTS_EFFECT_CLASS"
    OVERSTATED_CERTAINTY = "OVERSTATED_CERTAINTY"
    UNSUPPORTED_ASSERTION = "UNSUPPORTED_ASSERTION"
    INTERPRETATION_PRESENTED_AS_FACT = "INTERPRETATION_PRESENTED_AS_FACT"
    NO_CHECKABLE_CONTENT = "NO_CHECKABLE_CONTENT"
    NO_LIMITATION_BASIS = "NO_LIMITATION_BASIS"
    # policy and authority
    PROHIBITED_CATEGORY = "PROHIBITED_CATEGORY"
    FORGED_VERIFICATION = "FORGED_VERIFICATION"
    EMBEDDED_AUTHORITY_OR_INJECTION = "EMBEDDED_AUTHORITY_OR_INJECTION"
    CLAIMS_VERIFICATION = "CLAIMS_VERIFICATION"


class ReleaseAction(str, Enum):
    """What the pipeline does with the narration (``Phases.md`` Phase 16: approve or regenerate)."""

    APPROVE = "APPROVE"  # every claim is VERIFIED
    RELEASE_VERIFIED_ONLY = (
        "RELEASE_VERIFIED_ONLY"  # strip the unverifiable and insufficient claims
    )
    REGENERATE = "REGENERATE"  # nothing verified, or a claim is wrong, blocked or invalid
    NOTHING_TO_VERIFY = "NOTHING_TO_VERIFY"  # a refusal, a failure or an empty narration


class OverallStatus(str, Enum):
    ALL_VERIFIED = "ALL_VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NONE_VERIFIED = "NONE_VERIFIED"
    NO_CLAIMS = "NO_CLAIMS"


class VerificationReason(_Frozen):
    code: ReasonCode
    # Identifiers and enumerated values only (for example ``rule_id=...``). Never claim text.
    detail: str | None = Field(default=None, max_length=300)
    evidence_id: str | None = None


class VerifiedProvenance(_Frozen):
    """Provenance resolved from the trusted evidence, never copied from the claim."""

    source_profiles: tuple[str, ...] = ()
    source_locations: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    version_refs: tuple[str, ...] = ()
    rule_versions: tuple[str, ...] = ()  # "rule_id@rule_version"
    bundle_refs: tuple[str, ...] = ()
    ruleset_hashes: tuple[str, ...] = ()


class ClaimVerification(_Frozen):
    """The verification result for one claim."""

    claim_id: str
    claim_type: ClaimType | None = None
    domain: Domain | None = None
    status: VerificationStatus
    # Set exactly when status is VERIFIED, and only by the Phase 16 verifier.
    verified_by: str | None = None
    claim_text_hash: str | None = None
    evidence_refs: tuple[EvidenceReference, ...] = ()
    rule_refs: tuple[str, ...] = ()
    reasons: tuple[VerificationReason, ...] = ()
    uncertainty: tuple[UncertaintyFlag, ...] = ()
    provenance: VerifiedProvenance = Field(default_factory=VerifiedProvenance)
    verifier_version: str
    checks_run: tuple[str, ...] = ()
    # The share of the claim's recognised tokens, in basis points, that the checker understood;
    # a measure of how much of the text the deterministic checker could actually read.
    text_coverage_bp: StrictInt | None = Field(default=None, ge=0, le=10000)

    @model_validator(mode="after")
    def _verified_by(self) -> ClaimVerification:
        verified = self.status is VerificationStatus.VERIFIED
        if verified != (self.verified_by is not None):
            raise ValueError("verified_by is set exactly when the status is VERIFIED")
        if self.claim_text_hash is not None and not _SHA256_RE.match(self.claim_text_hash):
            raise ValueError("claim_text_hash must be a lower-case sha256 hex digest")
        return self


class BundleIntegrity(_Frozen):
    bundle_ref: str
    domain: Domain
    ok: bool
    problems: tuple[str, ...] = ()


class VerificationTrace(_Frozen):
    """Content-free audit metadata for one verification run."""

    verifier_version: str
    policy_version: str
    config_hash: str
    input_hash: str  # over claim ids, claim text hashes and references; no claim text
    bundles: tuple[BundleIntegrity, ...] = ()
    bundle_refs: tuple[str, ...] = ()
    version_refs: tuple[str, ...] = ()
    ruleset_hashes: tuple[str, ...] = ()
    checks_catalog: tuple[str, ...] = ()
    input_forgery_detected: bool = False
    deterministic: bool = True


class VerificationError(_Frozen):
    code: str
    message: str


class VerificationResponse(_Frozen):
    schema_version: str = VERIFICATION_CONTRACT_VERSION
    request_id: str | None = None
    verifier_version: str
    overall_status: OverallStatus
    release_action: ReleaseAction
    claims: tuple[ClaimVerification, ...] = ()
    status_counts: tuple[tuple[VerificationStatus, int], ...] = ()
    verified_claim_ids: tuple[str, ...] = ()
    summary: str = ""
    trace: VerificationTrace
    error: VerificationError | None = None
    report_hash: str

    @model_validator(mode="after")
    def _consistent(self) -> VerificationResponse:
        verified = tuple(c.claim_id for c in self.claims if c.status is VerificationStatus.VERIFIED)
        if verified != self.verified_claim_ids:
            raise ValueError("verified_claim_ids must list exactly the VERIFIED claims")
        if self.overall_status is OverallStatus.ALL_VERIFIED and (
            not self.claims or len(verified) != len(self.claims)
        ):
            raise ValueError("ALL_VERIFIED requires every claim to be VERIFIED")
        if not _SHA256_RE.match(self.report_hash):
            raise ValueError("report_hash must be a lower-case sha256 hex digest")
        return self
