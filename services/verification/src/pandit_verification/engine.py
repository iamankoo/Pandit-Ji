"""The Phase 16 verification engine.

``Verifier.verify(NarrationResponse) -> VerificationResponse`` judges each claim against trusted
evidence that the verifier resolves itself (``TrustedEvidence``). A claim becomes ``VERIFIED`` only
when every stage passes:

1. input authority and policy screen (forged ``VERIFIED``, injection, prohibited content),
2. reference resolution (the bundle, the evidence id, domain, kind, pinned versions),
3. provenance consistency (the claim's copied profiles, locations, versions and confidence),
4. semantic class (an observation is not a derivation, an interpretation is not a fact),
5. evidence state (triggered, evaluable, visible, complete fact basis, confidence),
6. source profiles (conflicting profiles are never merged; a conflicted source must be named),
7. text grounding (closed-vocabulary check of what the claim text asserts, see ``text.py``).

The result is deterministic: no clock, no randomness, no network, no model. The text check is
lexical grounding, not entailment: it can prove that the recognised assertions in a claim match the
evidence and that nothing it can recognise goes beyond the evidence. It cannot prove that arbitrary
prose is true, so unreadable text is ``UNVERIFIABLE`` rather than assumed supported.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pandit_contracts.agent import (
    AgentStatus,
    ClaimType,
    Domain,
    EvidenceClass,
    EvidenceReference,
    MissingCapability,
    NarrationClaim,
    NarrationResponse,
    UncertaintyFlag,
    VerificationState,
)
from pandit_contracts.verification import (
    BundleIntegrity,
    ClaimVerification,
    OverallStatus,
    ReasonCode,
    ReleaseAction,
    VerificationError,
    VerificationReason,
    VerificationResponse,
    VerificationStatus,
    VerificationTrace,
    VerifiedProvenance,
)
from pydantic import ValidationError

from pandit_verification._version import __version__
from pandit_verification.evidence import EvidenceItem, TrustedBundle, TrustedEvidence
from pandit_verification.policy import POLICY_VERSION, screen_text
from pandit_verification.text import TOPICS, TextAnalysis, alnum_only, analyze

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$")
S = VerificationStatus
R = ReasonCode

# The order in which a claim's failing categories decide its single status.
_PRECEDENCE: tuple[VerificationStatus, ...] = (
    S.POLICY_BLOCKED,
    S.INVALID_REFERENCE,
    S.CONFLICTING_EVIDENCE,
    S.INSUFFICIENT_EVIDENCE,
    S.UNSUPPORTED,
    S.UNVERIFIABLE,
)
_NOT_CLEAR = {"PARTIAL", "OCCLUDED", "NOT_VISIBLE"}
_LIMITATION_STATUSES = {
    "NOT_EVALUABLE",
    "NOT_TRIGGERED",
    "CANCELLED",
    "PARTIALLY_CANCELLED",
    "PARTIAL",
    "OCCLUDED",
    "NOT_VISIBLE",
    "NOT_PRODUCTION_READY",
}
_BACKING: dict[ClaimType, tuple[Domain, EvidenceClass]] = {
    ClaimType.CALCULATION_FACT: (Domain.ASTROLOGY, EvidenceClass.CALCULATED_FACT),
    ClaimType.OBSERVED_FEATURE: (Domain.PALMISTRY, EvidenceClass.OBSERVED_FACT),
    ClaimType.DERIVED_FEATURE: (Domain.PALMISTRY, EvidenceClass.DERIVED_FACT),
}
CHECKS_CATALOG: tuple[str, ...] = (
    "authority_and_policy",
    "reference_resolution",
    "bundle_integrity",
    "provenance_consistency",
    "semantic_class",
    "evidence_state",
    "source_profiles",
    "text_grounding",
)
_GENERIC_TAG_TOKENS = frozenset(
    {"general", "yoga", "hand", "indicated", "from", "with", "line", "left", "right", "map"}
)


def verifier_identity() -> str:
    return f"pandit-verification@{__version__}"


@dataclass(frozen=True)
class VerifierConfig:
    """Deterministic verifier configuration. It is hashed into every trace."""

    # A numeric confidence floor (basis points). ``None``: no floor. Phase 13 confidences are
    # uncalibrated, so no default floor is invented.
    min_confidence_bp: int | None = None
    require_calibrated_confidence: bool = False
    require_production_ready: bool = False
    expected_ruleset_hashes: frozenset[str] | None = None
    expected_knowledge_versions: frozenset[str] | None = None
    pinned_rule_versions: Mapping[str, str] = field(default_factory=dict)
    max_claims: int = 200

    def config_hash(self) -> str:
        body = {
            "min_confidence_bp": self.min_confidence_bp,
            "require_calibrated_confidence": self.require_calibrated_confidence,
            "require_production_ready": self.require_production_ready,
            "expected_ruleset_hashes": sorted(self.expected_ruleset_hashes or ()),
            "expected_knowledge_versions": sorted(self.expected_knowledge_versions or ()),
            "pinned_rule_versions": sorted(self.pinned_rule_versions.items()),
            "max_claims": self.max_claims,
            "policy_version": POLICY_VERSION,
            "verifier_version": __version__,
        }
        return _sha(json.dumps(body, sort_keys=True, separators=(",", ":")))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class _Malformed:
    claim_id: str
    detail: str


class _Outcome:
    """Collects reasons for one claim; the final status comes from ``_PRECEDENCE``."""

    def __init__(self) -> None:
        self.reasons: list[VerificationReason] = []
        self.categories: set[VerificationStatus] = set()
        self.checks: list[str] = []
        self.analysis: TextAnalysis | None = None

    def ran(self, check: str) -> None:
        if check not in self.checks:
            self.checks.append(check)

    def fail(
        self,
        status: VerificationStatus,
        code: ReasonCode,
        detail: str | None = None,
        evidence_id: str | None = None,
    ) -> None:
        self.categories.add(status)
        self.reasons.append(VerificationReason(code=code, detail=detail, evidence_id=evidence_id))

    def info(
        self, code: ReasonCode, detail: str | None = None, evidence_id: str | None = None
    ) -> None:
        self.reasons.append(VerificationReason(code=code, detail=detail, evidence_id=evidence_id))

    @property
    def failed(self) -> bool:
        return bool(self.categories)

    def status(self) -> VerificationStatus:
        for candidate in _PRECEDENCE:
            if candidate in self.categories:
                return candidate
        return S.VERIFIED


class Verifier:
    """Verifies the claims of a ``NarrationResponse`` against trusted evidence."""

    def __init__(
        self,
        evidence: TrustedEvidence,
        config: VerifierConfig | None = None,
        *,
        trusted_missing: Sequence[MissingCapability] = (),
    ) -> None:
        self._evidence = evidence
        self._config = config or VerifierConfig()
        self._missing = tuple(trusted_missing)

    @property
    def config(self) -> VerifierConfig:
        return self._config

    # -- entry points ------------------------------------------------------------------------

    def verify(self, response: NarrationResponse) -> VerificationResponse:
        forged = (
            response.verification is VerificationState.VERIFIED or response.verified_by is not None
        )
        nothing = response.status in {AgentStatus.REFUSED, AgentStatus.FAILED}
        items: list[NarrationClaim | _Malformed] = [] if nothing else list(response.claims)
        return self._run(items, response.request_id, forged)

    def verify_payload(self, payload: Mapping[str, Any] | str) -> VerificationResponse:
        """Verify a raw (untrusted) narration payload; malformed claims are reported, not raised."""
        data: Any = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except ValueError:
                return self._error("MALFORMED_PAYLOAD", "the payload is not valid JSON")
        if not isinstance(data, Mapping):
            return self._error("MALFORMED_PAYLOAD", "the payload is not an object")
        request_id = data.get("request_id")
        request_id = request_id if isinstance(request_id, str) else None
        forged = data.get("verification") == "VERIFIED" or data.get("verified_by") is not None
        sections = data.get("sections", [])
        items: list[NarrationClaim | _Malformed] = []
        if not isinstance(sections, list):
            return self._error("MALFORMED_PAYLOAD", "sections is not a list")
        counter = 0
        for section in sections:
            raw_claims = section.get("claims") if isinstance(section, Mapping) else None
            if not isinstance(raw_claims, list):
                counter += 1
                items.append(_Malformed(f"MALFORMED-{counter:03d}", "section without claims"))
                continue
            for raw in raw_claims:
                counter += 1
                try:
                    items.append(NarrationClaim.model_validate(raw))
                except ValidationError:
                    cid = raw.get("claim_id") if isinstance(raw, Mapping) else None
                    items.append(
                        _Malformed(
                            cid
                            if isinstance(cid, str) and _ID_RE.match(cid)
                            else f"MALFORMED-{counter:03d}",
                            "claim does not satisfy the claim contract",
                        )
                    )
        return self._run(items, request_id, forged)

    # -- orchestration -----------------------------------------------------------------------

    def _error(self, code: str, message: str) -> VerificationResponse:
        trace = self._trace([], "0" * 64, False)
        return self._assemble(None, [], trace, error=VerificationError(code=code, message=message))

    def _run(
        self,
        items: list[NarrationClaim | _Malformed],
        request_id: str | None,
        response_forged: bool,
    ) -> VerificationResponse:
        input_hash = _sha(
            json.dumps([self._descriptor(i) for i in items], sort_keys=True, separators=(",", ":"))
        )
        trace_forged = response_forged or any(
            isinstance(i, NarrationClaim)
            and (i.verification is VerificationState.VERIFIED or i.verified_by is not None)
            for i in items
        )
        if len(items) > self._config.max_claims:
            trace = self._trace([], input_hash, trace_forged)
            return self._assemble(
                request_id,
                [],
                trace,
                error=VerificationError(
                    code="TOO_MANY_CLAIMS", message="the narration exceeds the claim limit"
                ),
            )
        counts = Counter(i.claim_id for i in items)
        results: list[ClaimVerification] = []
        for item in items:
            if isinstance(item, _Malformed):
                results.append(self._malformed(item))
                continue
            if counts[item.claim_id] > 1:
                results.append(self._duplicate(item))
                continue
            results.append(self._verify_claim(item))
        trace = self._trace(results, input_hash, trace_forged)
        return self._assemble(request_id, results, trace)

    @staticmethod
    def _descriptor(item: NarrationClaim | _Malformed) -> list[Any]:
        if isinstance(item, _Malformed):
            return [item.claim_id, "malformed"]
        return [
            item.claim_id,
            _sha(item.text),
            item.claim_type.value,
            item.domain.value,
            [[r.evidence_id, r.domain.value, r.kind.value, r.bundle_ref] for r in item.references],
        ]

    # -- one claim ---------------------------------------------------------------------------

    def _verify_claim(self, claim: NarrationClaim) -> ClaimVerification:
        out = _Outcome()

        # 1. authority and policy: nothing below runs for a blocked claim
        out.ran("authority_and_policy")
        if claim.verification is VerificationState.VERIFIED or claim.verified_by is not None:
            out.fail(S.POLICY_BLOCKED, R.FORGED_VERIFICATION, "input claim carries VERIFIED state")
        screen = screen_text(claim.text, claim.domain)
        if screen.prohibited:
            out.fail(
                S.POLICY_BLOCKED,
                R.PROHIBITED_CATEGORY,
                ",".join(c.value for c in screen.prohibited),
            )
        if screen.death_timing:
            out.fail(S.POLICY_BLOCKED, R.PROHIBITED_CATEGORY, "LIFESPAN:death_timing")
        if screen.authority_hits:
            out.fail(
                S.POLICY_BLOCKED, R.EMBEDDED_AUTHORITY_OR_INJECTION, ",".join(screen.authority_hits)
            )
        if screen.claims_verification:
            out.fail(S.POLICY_BLOCKED, R.CLAIMS_VERIFICATION)
        if out.failed:
            return self._finish(claim, out, ())

        # 2-3. references and provenance
        items = self._resolve(claim, out)
        if out.failed:
            return self._finish(claim, out, items)

        if claim.claim_type is ClaimType.LIMITATION:
            self._limitation(claim, items, out)
            return self._finish(claim, out, items)

        # 4. semantic class
        self._semantic_class(claim, items, out)
        # 5. evidence state
        self._evidence_state(claim, items, out)
        # 6. source profiles
        analysis = analyze(claim.text)
        out.analysis = analysis
        self._profiles(claim, items, analysis, out)
        # 7. text grounding
        self._grounding(claim, items, analysis, out)
        return self._finish(claim, out, items)

    # -- stage 2/3: references -----------------------------------------------------------------

    def _resolve(self, claim: NarrationClaim, out: _Outcome) -> list[EvidenceItem]:
        out.ran("reference_resolution")
        if not claim.references:
            if claim.claim_type is not ClaimType.LIMITATION:
                out.fail(S.INVALID_REFERENCE, R.MISSING_REFERENCE)
            return []
        resolved: list[EvidenceItem] = []
        domain_bundles = [b for b in self._evidence.bundles.values() if b.domain is claim.domain]
        for ref in claim.references:
            item = self._resolve_one(claim, ref, domain_bundles, out)
            if item is not None:
                resolved.append(item)
        if out.failed:
            return resolved
        self._provenance(claim, resolved, out)
        return resolved

    def _resolve_one(
        self,
        claim: NarrationClaim,
        ref: EvidenceReference,
        domain_bundles: list[TrustedBundle],
        out: _Outcome,
    ) -> EvidenceItem | None:
        if not _ID_RE.match(ref.evidence_id):
            out.fail(S.INVALID_REFERENCE, R.MALFORMED_CLAIM, "evidence id is malformed")
            return None
        if ref.domain is not claim.domain:
            out.fail(S.INVALID_REFERENCE, R.DOMAIN_MISMATCH, "reference domain differs from claim")
            return None
        bundle = self._evidence.bundle(ref.bundle_ref)
        if bundle is None:
            if not domain_bundles:
                out.fail(S.UNVERIFIABLE, R.EVIDENCE_UNAVAILABLE, "no trusted bundle for the domain")
            else:
                out.fail(S.INVALID_REFERENCE, R.BUNDLE_MISMATCH, "bundle is not a trusted bundle")
            return None
        out.ran("bundle_integrity")
        if bundle.domain is not claim.domain:
            out.fail(S.INVALID_REFERENCE, R.DOMAIN_MISMATCH, "bundle belongs to another domain")
            return None
        if not bundle.ok:
            out.fail(
                S.INVALID_REFERENCE, R.BUNDLE_INTEGRITY_FAILURE, "; ".join(bundle.problems)[:280]
            )
            return None
        cfg = self._config
        if (
            cfg.expected_ruleset_hashes is not None
            and bundle.ruleset_hash is not None
            and bundle.ruleset_hash not in cfg.expected_ruleset_hashes
        ):
            out.fail(S.INVALID_REFERENCE, R.RULESET_HASH_MISMATCH, "ruleset hash is not pinned")
            return None
        if cfg.expected_knowledge_versions is not None and not set(bundle.version_refs) <= set(
            cfg.expected_knowledge_versions
        ):
            out.fail(S.INVALID_REFERENCE, R.KNOWLEDGE_VERSION_MISMATCH, "version is not pinned")
            return None
        item = bundle.items.get(ref.evidence_id)
        if item is None:
            out.fail(
                S.INVALID_REFERENCE,
                R.EVIDENCE_NOT_FOUND,
                "not in the referenced bundle",
                ref.evidence_id,
            )
            return None
        if item.reference_kind is not ref.kind:
            out.fail(S.INVALID_REFERENCE, R.REFERENCE_KIND_MISMATCH, None, ref.evidence_id)
            return None
        pinned = cfg.pinned_rule_versions.get(item.evidence_id)
        if pinned is not None and pinned != item.rule_version:
            out.fail(
                S.INVALID_REFERENCE,
                R.RULE_VERSION_MISMATCH,
                f"pinned={pinned} actual={item.rule_version}",
                item.evidence_id,
            )
            return None
        return item

    def _provenance(self, claim: NarrationClaim, items: list[EvidenceItem], out: _Outcome) -> None:
        out.ran("provenance_consistency")
        want_versions = {i.version_ref for i in items if i.version_ref}
        want_profiles = {i.source_profile for i in items if i.source_profile}
        want_locations = {i.source_location for i in items if i.source_location}
        trusted_versions = {v for b in self._evidence.bundles.values() for v in b.version_refs}
        if not set(claim.version_refs) <= trusted_versions:
            out.fail(S.INVALID_REFERENCE, R.KNOWLEDGE_VERSION_MISMATCH, "unknown version")
        elif set(claim.version_refs) != want_versions:
            out.fail(S.INVALID_REFERENCE, R.KNOWLEDGE_VERSION_MISMATCH, "version differs")
        if set(claim.source_profiles) != want_profiles:
            out.fail(S.INVALID_REFERENCE, R.PROVENANCE_MISMATCH, "source profile differs")
        if set(claim.source_locations) != want_locations:
            out.fail(S.INVALID_REFERENCE, R.PROVENANCE_MISMATCH, "source location differs")
        confidences = [i.confidence_bp for i in items if i.confidence_bp is not None]
        floor = min(confidences) if confidences else None
        if claim.min_confidence_bp is not None and (
            floor is None or claim.min_confidence_bp > floor
        ):
            out.fail(S.INVALID_REFERENCE, R.PROVENANCE_MISMATCH, "confidence is overstated")

    # -- stage 4: semantic class ---------------------------------------------------------------

    def _semantic_class(
        self, claim: NarrationClaim, items: list[EvidenceItem], out: _Outcome
    ) -> None:
        out.ran("semantic_class")
        ctype = claim.claim_type
        if ctype in _BACKING:
            want_domain, want_class = _BACKING[ctype]
            if claim.domain is not want_domain:
                out.fail(S.UNSUPPORTED, R.SEMANTIC_CLASS_MISMATCH, "claim type not in this domain")
            for item in items:
                if item.evidence_class is not want_class:
                    out.fail(
                        S.UNSUPPORTED,
                        R.SEMANTIC_CLASS_MISMATCH,
                        f"claim={ctype.value} evidence={item.evidence_class.value}",
                        item.evidence_id,
                    )
            return
        # TRADITIONAL_INTERPRETATION
        if not any(i.evidence_class is EvidenceClass.RULE_EVALUATION for i in items):
            out.fail(S.UNSUPPORTED, R.INTERPRETATION_WITHOUT_RULE)

    # -- stage 5: evidence state ---------------------------------------------------------------

    def _evidence_state(
        self, claim: NarrationClaim, items: list[EvidenceItem], out: _Outcome
    ) -> None:
        out.ran("evidence_state")
        cfg = self._config
        for item in items:
            bundle = self._evidence.bundle(item.bundle_ref)
            assert bundle is not None
            if item.evidence_class is EvidenceClass.RULE_EVALUATION:
                self._rule_state(item, bundle, out)
            elif item.evidence_class is not EvidenceClass.CONTEXT_STATUS:
                self._fact_state(item, out)
            if item.confidence_bp is not None and item.confidence_calibrated is False:
                if cfg.require_calibrated_confidence:
                    out.fail(
                        S.INSUFFICIENT_EVIDENCE,
                        R.CONFIDENCE_UNCALIBRATED,
                        None,
                        item.evidence_id,
                    )
                else:
                    out.info(R.CONFIDENCE_UNCALIBRATED, None, item.evidence_id)
            if item.bundle_production_ready is False:
                if cfg.require_production_ready:
                    out.fail(S.INSUFFICIENT_EVIDENCE, R.BUNDLE_NOT_PRODUCTION_READY)
                else:
                    out.info(R.BUNDLE_NOT_PRODUCTION_READY, None, item.evidence_id)

    def _fact_state(self, item: EvidenceItem, out: _Outcome) -> None:
        self._visibility(item, out)
        self._confidence(item, out)
        if item.missing_basis:
            out.fail(
                S.INSUFFICIENT_EVIDENCE,
                R.MISSING_REQUIRED_FACT,
                f"missing={len(item.missing_basis)}",
                item.evidence_id,
            )
        self._basis(item, out)

    def _rule_state(self, item: EvidenceItem, bundle: TrustedBundle, out: _Outcome) -> None:
        status = item.status or ""
        if status == "NOT_EVALUABLE":
            out.fail(S.INSUFFICIENT_EVIDENCE, R.RULE_NOT_EVALUABLE, None, item.evidence_id)
            return
        if status != "TRIGGERED":
            out.fail(S.UNSUPPORTED, R.RULE_NOT_TRIGGERED, f"status={status}", item.evidence_id)
            return
        if item.unresolved_dependencies:
            out.fail(
                S.INSUFFICIENT_EVIDENCE,
                R.MISSING_REQUIRED_FACT,
                f"unresolved={len(item.unresolved_dependencies)}",
                item.evidence_id,
            )
        if item.domain is Domain.PALMISTRY:
            if not item.fact_refs:
                out.fail(S.INSUFFICIENT_EVIDENCE, R.RULE_WITHOUT_FACT_BASIS, None, item.evidence_id)
            if item.missing_basis:
                out.fail(
                    S.INSUFFICIENT_EVIDENCE,
                    R.MISSING_REQUIRED_FACT,
                    f"missing={len(item.missing_basis)}",
                    item.evidence_id,
                )
            self._basis(item, out, bundle)

    def _basis(
        self, item: EvidenceItem, out: _Outcome, bundle: TrustedBundle | None = None
    ) -> None:
        trusted = bundle or self._evidence.bundle(item.bundle_ref)
        if trusted is None:
            return
        for fid in item.basis_ids:
            fact = trusted.items.get(fid)
            if fact is None or fact.evidence_id == item.evidence_id:
                continue
            self._visibility(fact, out, owner=item.evidence_id)
            self._confidence(fact, out, owner=item.evidence_id)

    def _visibility(self, item: EvidenceItem, out: _Outcome, owner: str | None = None) -> None:
        status = item.status or ""
        ref = owner or item.evidence_id
        if status == "NOT_EVALUABLE":
            out.fail(
                S.INSUFFICIENT_EVIDENCE, R.EVIDENCE_NOT_EVALUABLE, f"fact={item.evidence_id}", ref
            )
        elif status in _NOT_CLEAR:
            out.fail(
                S.INSUFFICIENT_EVIDENCE, R.EVIDENCE_NOT_VISIBLE, f"fact={item.evidence_id}", ref
            )

    def _confidence(self, item: EvidenceItem, out: _Outcome, owner: str | None = None) -> None:
        floor = self._config.min_confidence_bp
        if floor is not None and item.confidence_bp is not None and item.confidence_bp < floor:
            out.fail(
                S.INSUFFICIENT_EVIDENCE,
                R.CONFIDENCE_BELOW_THRESHOLD,
                f"fact={item.evidence_id}",
                owner or item.evidence_id,
            )

    # -- stage 6: source profiles --------------------------------------------------------------

    def _profiles(
        self,
        claim: NarrationClaim,
        items: list[EvidenceItem],
        analysis: TextAnalysis,
        out: _Outcome,
    ) -> None:
        out.ran("source_profiles")
        rules = [i for i in items if i.evidence_class is EvidenceClass.RULE_EVALUATION]
        if not rules or claim.claim_type is not ClaimType.TRADITIONAL_INTERPRETATION:
            return
        sources = {r.source_id or r.source_profile for r in rules}
        if len(sources) > 1:
            conflict_sets = [set(r.conflict_ids) for r in rules]
            overlapping = any(
                a & b for index, a in enumerate(conflict_sets) for b in conflict_sets[index + 1 :]
            )
            if overlapping:
                out.fail(S.CONFLICTING_EVIDENCE, R.CONFLICTING_PROFILES_MERGED)
            else:
                out.fail(S.UNVERIFIABLE, R.MULTI_PROFILE_NOT_ATTRIBUTABLE)
            return
        # one source; a conflicted source may be cited only when the claim names it
        haystack = alnum_only(claim.text)
        for rule in rules:
            if rule.conflict_ids and not any(t in haystack for t in rule.attribution):
                out.fail(
                    S.CONFLICTING_EVIDENCE,
                    R.CONFLICT_PROFILE_NOT_NAMED,
                    ",".join(rule.conflict_ids)[:200],
                    rule.evidence_id,
                )

    # -- stage 7: text grounding ---------------------------------------------------------------

    def _grounding(
        self,
        claim: NarrationClaim,
        items: list[EvidenceItem],
        a: TextAnalysis,
        out: _Outcome,
    ) -> None:
        out.ran("text_grounding")
        is_fact = claim.claim_type in _BACKING
        if a.certainty:
            out.fail(S.UNSUPPORTED, R.OVERSTATED_CERTAINTY)
        if claim.claim_type is ClaimType.OBSERVED_FEATURE and a.derivation_language:
            if not a.observation_language:
                out.fail(
                    S.UNSUPPORTED, R.CLASS_MISREPRESENTED, "derivation described as observed type"
                )
        if claim.claim_type is ClaimType.DERIVED_FEATURE and a.observation_language:
            if not a.derivation_language:
                out.fail(
                    S.UNSUPPORTED, R.CLASS_MISREPRESENTED, "observation language on a derived fact"
                )
        if is_fact:
            if a.outcome_words:
                out.fail(S.UNSUPPORTED, R.UNSUPPORTED_ASSERTION, "outcome or judgement wording")
            if a.topics:
                out.fail(S.UNSUPPORTED, R.TOPIC_NOT_IN_EVIDENCE, ",".join(sorted(a.topics)))
            if a.positive or a.negative:
                out.fail(S.UNSUPPORTED, R.VALENCE_NOT_IN_EVIDENCE)
        else:
            if not a.framed:
                out.fail(S.UNSUPPORTED, R.INTERPRETATION_PRESENTED_AS_FACT)
            self._interpretation_text(items, a, out)
        if claim.domain is Domain.ASTROLOGY:
            self._astrology_text(claim, items, a, out, is_fact)
        else:
            self._palm_text(items, a, out, is_fact)
        # numbers (anything not understood as a placement) must be present in the evidence
        known_numbers = {n for i in items for n in i.numbers}
        extra = sorted(a.numbers - known_numbers)
        if extra:
            out.fail(S.UNSUPPORTED, R.UNGROUNDED_NUMBER, f"count={len(extra)}")

    def _interpretation_text(
        self, items: list[EvidenceItem], a: TextAnalysis, out: _Outcome
    ) -> None:
        rules = [i for i in items if i.evidence_class is EvidenceClass.RULE_EVALUATION]
        tag_tokens = {
            tok for r in rules for tag in r.tags for tok in re.split(r"[._]", tag.lower()) if tok
        }
        for topic in sorted(a.topics):
            if not any(tok.startswith(stem) for stem in TOPICS[topic] for tok in tag_tokens):
                out.fail(S.UNSUPPORTED, R.TOPIC_NOT_IN_EVIDENCE, topic)
        effects = {r.effect_class for r in rules if r.effect_class}
        if a.positive or a.negative:
            if not effects:
                out.fail(S.UNSUPPORTED, R.VALENCE_NOT_IN_EVIDENCE)
            else:
                if a.positive and effects != {"supportive"}:
                    code = (
                        R.VALENCE_CONTRADICTS_EFFECT_CLASS
                        if "challenging" in effects
                        else R.VALENCE_NOT_IN_EVIDENCE
                    )
                    out.fail(
                        S.CONFLICTING_EVIDENCE if "challenging" in effects else S.UNSUPPORTED, code
                    )
                if a.negative and effects != {"challenging"}:
                    code = (
                        R.VALENCE_CONTRADICTS_EFFECT_CLASS
                        if "supportive" in effects
                        else R.VALENCE_NOT_IN_EVIDENCE
                    )
                    out.fail(
                        S.CONFLICTING_EVIDENCE if "supportive" in effects else S.UNSUPPORTED, code
                    )
        # positive support: the text must reflect at least one cited tag (or a stated hand)
        stems = {
            tok[:5]
            for r in rules
            for tag in r.tags
            for tok in re.split(r"[._]", tag.lower())
            if len(tok) >= 4 and tok not in _GENERIC_TAG_TOKENS
        }
        hand_support = any(a.hands & r.hands for r in rules)
        text_hit = any(re.search(r"\b" + re.escape(s), a.normalized) for s in stems)
        if not (text_hit or hand_support) and not out.failed:
            out.fail(
                S.UNVERIFIABLE, R.NO_CHECKABLE_CONTENT, "no cited tag is reflected in the text"
            )

    def _astrology_text(
        self,
        claim: NarrationClaim,
        items: list[EvidenceItem],
        a: TextAnalysis,
        out: _Outcome,
        is_fact: bool,
    ) -> None:
        bundles = {i.bundle_ref for i in items}
        chart: dict[str, EvidenceItem] = {}
        for ref in sorted(bundles):
            b = self._evidence.bundle(ref)
            if b is None:
                continue
            chart.update(b.planets)
            if b.lagna is not None:
                chart["lagna"] = b.lagna
        cited = {i.evidence_id for i in items}
        placements = len(a.planets) + len(a.signs) + len(a.houses) + len(a.dignities)
        if is_fact and placements == 0:
            out.fail(S.UNVERIFIABLE, R.NO_CHECKABLE_CONTENT, "no recognised placement")
        for entity, binding in sorted(a.bindings.items()):
            item = chart.get(entity)
            if item is None:
                out.fail(S.UNSUPPORTED, R.UNGROUNDED_ENTITY, f"entity={entity}")
                continue
            if is_fact and item.evidence_id not in cited:
                out.fail(S.UNSUPPORTED, R.UNGROUNDED_ENTITY, f"not cited: {entity}")
            if len(binding.signs) > 1 or len(binding.houses) > 1 or len(binding.retrograde) > 1:
                out.fail(S.CONFLICTING_EVIDENCE, R.SELF_CONTRADICTION, f"entity={entity}")
            if any(s != item.sign for s in binding.signs):
                out.fail(S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE, f"{entity}:sign")
            if entity != "lagna":
                if any(h != item.house for h in binding.houses):
                    out.fail(S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE, f"{entity}:house")
                if any(d != item.dignity for d in binding.dignities):
                    out.fail(S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE, f"{entity}:dignity")
                if any(r != item.retrograde for r in binding.retrograde):
                    out.fail(S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE, f"{entity}:retrograde")
        if is_fact:
            cited_items = [i for i in items if i.evidence_id in cited]
            signs = {i.sign for i in cited_items if i.sign}
            houses = {i.house for i in cited_items if i.house}
            dignities = {i.dignity for i in cited_items if i.dignity}
            for kind, said, have in (
                ("sign", a.unbound_signs, signs),
                ("house", a.unbound_houses, houses),
                ("dignity", a.unbound_dignities, dignities),
            ):
                if any(v not in have for v in said):
                    if have:
                        out.fail(S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE, f"unbound:{kind}")
                    else:
                        out.fail(S.UNSUPPORTED, R.UNGROUNDED_ENTITY, f"unbound:{kind}")

    def _palm_text(
        self, items: list[EvidenceItem], a: TextAnalysis, out: _Outcome, is_fact: bool
    ) -> None:
        if is_fact and not (a.hands or a.lines or a.mounts):
            out.fail(S.UNVERIFIABLE, R.NO_CHECKABLE_CONTENT, "no recognised palm entity")
        for kind, said, have in (
            ("hand", a.hands, set().union(*(i.hands for i in items)) if items else set()),
            ("line", a.lines, set().union(*(i.lines for i in items)) if items else set()),
            ("mount", a.mounts, set().union(*(i.mounts for i in items)) if items else set()),
        ):
            missing = said - have
            if not missing:
                continue
            if have:
                out.fail(S.CONFLICTING_EVIDENCE, R.CONTRADICTS_EVIDENCE, kind)
            else:
                out.fail(S.UNSUPPORTED, R.UNGROUNDED_ENTITY, kind)

    # -- limitations ---------------------------------------------------------------------------

    def _limitation(self, claim: NarrationClaim, items: list[EvidenceItem], out: _Outcome) -> None:
        out.ran("evidence_state")
        out.ran("text_grounding")
        a = analyze(claim.text)
        out.analysis = a
        if a.certainty:
            out.fail(S.UNSUPPORTED, R.OVERSTATED_CERTAINTY)
        if items:
            shows = False
            for item in items:
                if (
                    (item.status or "") in _LIMITATION_STATUSES
                    or item.conflict_ids
                    or item.unresolved_dependencies
                    or item.missing_basis
                ):
                    shows = True
            if shows:
                out.info(R.LIMITATION_SUPPORTED)
            else:
                out.fail(S.UNSUPPORTED, R.NO_LIMITATION_BASIS, "the cited evidence shows no gap")
            return
        text = claim.text.lower()
        for gap in self._missing:
            if gap.capability.value.lower() in text:
                out.info(R.LIMITATION_SUPPORTED, f"missing={gap.capability.value}")
                return
        out.fail(S.UNVERIFIABLE, R.NO_LIMITATION_BASIS, "no trusted record of this gap")

    # -- results -------------------------------------------------------------------------------

    def _uncertainty(
        self, claim: NarrationClaim, items: list[EvidenceItem]
    ) -> tuple[UncertaintyFlag, ...]:
        found: set[UncertaintyFlag] = set()
        for r in items:
            status = r.status or ""
            if status == "NOT_EVALUABLE":
                found.add(UncertaintyFlag.NOT_EVALUABLE)
            if status in {"NOT_TRIGGERED", "CANCELLED", "PARTIALLY_CANCELLED"}:
                found.add(UncertaintyFlag.NOT_TRIGGERED)
            if status in _NOT_CLEAR:
                found.add(UncertaintyFlag.NOT_VISIBLE)
            if r.conflict_ids:
                found.add(UncertaintyFlag.CONFLICTING_PROFILES)
            if r.confidence_bp is not None and not r.confidence_calibrated:
                found.add(UncertaintyFlag.UNCALIBRATED_CONFIDENCE)
            if r.bundle_production_ready is False:
                found.add(UncertaintyFlag.BUNDLE_NOT_PRODUCTION_READY)
        if UncertaintyFlag.EVIDENCE_TRIMMED in claim.uncertainty:
            found.add(UncertaintyFlag.EVIDENCE_TRIMMED)
        return tuple(f for f in UncertaintyFlag if f in found)

    def _finish(
        self, claim: NarrationClaim, out: _Outcome, items: Sequence[EvidenceItem]
    ) -> ClaimVerification:
        status = out.status()
        item_list = list(items)
        uncertainty = self._uncertainty(claim, item_list)
        understated = set(uncertainty) - set(claim.uncertainty)
        if status is S.VERIFIED:
            if understated:
                out.info(R.UNCERTAINTY_UNDERSTATED, ",".join(sorted(f.value for f in understated)))
            if not any(r.code is R.LIMITATION_SUPPORTED for r in out.reasons):
                out.info(R.SUPPORTED)
        bundle_refs = tuple(sorted({i.bundle_ref for i in item_list}))
        rule_items = [i for i in item_list if i.evidence_class is EvidenceClass.RULE_EVALUATION]
        provenance = VerifiedProvenance(
            source_profiles=tuple(
                sorted({i.source_profile for i in item_list if i.source_profile})
            ),
            source_locations=tuple(
                sorted({i.source_location for i in item_list if i.source_location})
            ),
            source_ids=tuple(sorted({i.source_id for i in item_list if i.source_id})),
            version_refs=tuple(sorted({i.version_ref for i in item_list if i.version_ref})),
            rule_versions=tuple(
                sorted(f"{i.evidence_id}@{i.rule_version}" for i in rule_items if i.rule_version)
            ),
            bundle_refs=bundle_refs,
            ruleset_hashes=tuple(
                sorted(
                    {
                        b.ruleset_hash
                        for ref in bundle_refs
                        if (b := self._evidence.bundle(ref)) is not None and b.ruleset_hash
                    }
                )
            ),
        )
        return ClaimVerification(
            claim_id=claim.claim_id,
            claim_type=claim.claim_type,
            domain=claim.domain,
            status=status,
            verified_by=verifier_identity() if status is S.VERIFIED else None,
            claim_text_hash=_sha(claim.text),
            evidence_refs=claim.references,
            rule_refs=tuple(i.evidence_id for i in rule_items),
            reasons=tuple(out.reasons),
            uncertainty=uncertainty,
            provenance=provenance,
            verifier_version=__version__,
            checks_run=tuple(out.checks),
            text_coverage_bp=out.analysis.coverage_bp if out.analysis is not None else None,
        )

    def _malformed(self, item: _Malformed) -> ClaimVerification:
        return ClaimVerification(
            claim_id=item.claim_id,
            status=S.INVALID_REFERENCE,
            reasons=(VerificationReason(code=R.MALFORMED_CLAIM, detail=item.detail),),
            verifier_version=__version__,
            checks_run=("authority_and_policy",),
        )

    def _duplicate(self, claim: NarrationClaim) -> ClaimVerification:
        return ClaimVerification(
            claim_id=claim.claim_id,
            claim_type=claim.claim_type,
            domain=claim.domain,
            status=S.INVALID_REFERENCE,
            claim_text_hash=_sha(claim.text),
            evidence_refs=claim.references,
            reasons=(VerificationReason(code=R.DUPLICATE_CLAIM_ID),),
            verifier_version=__version__,
            checks_run=("reference_resolution",),
        )

    # -- response ------------------------------------------------------------------------------

    def _trace(
        self, results: list[ClaimVerification], input_hash: str, forged: bool
    ) -> VerificationTrace:
        used = {r for res in results for r in res.provenance.bundle_refs}
        bundles = tuple(
            BundleIntegrity(
                bundle_ref=b.bundle_ref, domain=b.domain, ok=b.ok, problems=tuple(b.problems)
            )
            for b in sorted(self._evidence.bundles.values(), key=lambda x: x.bundle_ref)
        )
        return VerificationTrace(
            verifier_version=__version__,
            policy_version=POLICY_VERSION,
            config_hash=self._config.config_hash(),
            input_hash=input_hash,
            bundles=bundles,
            bundle_refs=tuple(sorted(used)),
            version_refs=tuple(sorted({v for r in results for v in r.provenance.version_refs})),
            ruleset_hashes=tuple(sorted({h for r in results for h in r.provenance.ruleset_hashes})),
            checks_catalog=CHECKS_CATALOG,
            input_forgery_detected=forged,
        )

    def _assemble(
        self,
        request_id: str | None,
        results: list[ClaimVerification],
        trace: VerificationTrace,
        error: VerificationError | None = None,
    ) -> VerificationResponse:
        counts = Counter(r.status for r in results)
        verified = tuple(r.claim_id for r in results if r.status is S.VERIFIED)
        if not results:
            overall = OverallStatus.NO_CLAIMS
        elif len(verified) == len(results):
            overall = OverallStatus.ALL_VERIFIED
        elif verified:
            overall = OverallStatus.PARTIALLY_VERIFIED
        else:
            overall = OverallStatus.NONE_VERIFIED
        release = _release(results, trace.input_forgery_detected, error is not None)
        status_counts = tuple((s, counts[s]) for s in VerificationStatus if counts[s])
        summary = (
            f"{len(results)} claims: "
            + (", ".join(f"{s.value}={n}" for s, n in status_counts) or "none")
            + f"; release={release.value}"
        )
        body = {
            "request_id": request_id,
            "overall": overall.value,
            "release": release.value,
            "claims": [r.model_dump(mode="json") for r in results],
            "trace": trace.model_dump(mode="json"),
            "error": error.model_dump(mode="json") if error else None,
        }
        report_hash = _sha(json.dumps(body, sort_keys=True, separators=(",", ":")))
        return VerificationResponse(
            request_id=request_id,
            verifier_version=__version__,
            overall_status=overall,
            release_action=release,
            claims=tuple(results),
            status_counts=status_counts,
            verified_claim_ids=verified,
            summary=summary,
            trace=trace,
            error=error,
            report_hash=report_hash,
        )


def _release(results: list[ClaimVerification], forged: bool, errored: bool) -> ReleaseAction:
    if errored or forged:
        return ReleaseAction.REGENERATE
    if not results:
        return ReleaseAction.NOTHING_TO_VERIFY
    statuses = {r.status for r in results}
    if statuses == {S.VERIFIED}:
        return ReleaseAction.APPROVE
    if S.VERIFIED not in statuses:
        return ReleaseAction.REGENERATE
    if statuses - {S.VERIFIED, S.UNVERIFIABLE, S.INSUFFICIENT_EVIDENCE}:
        return ReleaseAction.REGENERATE
    return ReleaseAction.RELEASE_VERIFIED_ONLY
