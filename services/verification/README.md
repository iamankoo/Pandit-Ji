# verification

Independent verification layer (`docs/architecture/adr/ADR-006-verification-independent-layer.md`, `ADR-011-verification-engine.md`). Canonical service name. **Phase 16: implemented** (`pandit_verification` 0.2.0).

**Responsible for**: deciding whether each generated claim of a `NarrationResponse` is supported by trusted, deterministic evidence: reference and bundle resolution, provenance and version checks, semantic-class checks, rule and uncertainty checks, source-conflict handling, closed-vocabulary text grounding, safety enforcement, a typed per-claim and per-response result, and the release recommendation. It is the **only** component that may produce `VERIFIED`.

**Not responsible for**: generating narrative content, planning, calling or hosting a model, palm vision, calculating astrology, creating rules, persistence, upload or consent infrastructure, voice or reports, or being a generic grammar/style checker.

## What `VERIFIED` means

A claim is `VERIFIED` when every stage passed against evidence the verifier resolved itself: the claim is supported by the application's encoded evidence and rule model. It does **not** mean astrology or palmistry is scientifically valid or that a prediction is true, and it does not mean the evidence is production-grade (a bundle that is not production ready still carries the `BUNDLE_NOT_PRODUCTION_READY` flag in the result; `VerifierConfig(require_production_ready=True)` makes it blocking).

## Use

```python
from pandit_verification import TrustedEvidence, Verifier, VerifierConfig, verify_narration

evidence = TrustedEvidence().add_palm(palm_bundle).add_astrology(astro_bundle)
verifier = Verifier(evidence, VerifierConfig(expected_ruleset_hashes=frozenset({PHASE6_HASH})))

# VerificationResponse: one result per claim
report = verifier.verify(narration)
# the report plus the releasable narration
outcome = verify_narration(narration, verifier)
```

`verify_payload(dict | str)` accepts a raw, untrusted narration payload and reports malformed claims instead of raising.

## Statuses (`pandit_contracts.verification`)

| Status | Meaning |
| --- | --- |
| `VERIFIED` | supported by trusted evidence and rules (the only verified outcome) |
| `UNSUPPORTED` | the text asserts more, or something else, than the evidence (wrong class, certainty, ungrounded entity or topic, rule not triggered) |
| `UNVERIFIABLE` | the verifier has no valid way to check it (no readable content, evidence not supplied, no trusted record of a limitation, several non-conflicting sources) |
| `INVALID_REFERENCE` | a reference, bundle, id, version, pin or copied provenance does not resolve; malformed claim; duplicate claim id |
| `CONFLICTING_EVIDENCE` | contradicts the evidence or itself, merges conflicting source profiles, or cites a conflicted source without naming it |
| `POLICY_BLOCKED` | prohibited content, forged `VERIFIED`, claimed verification, injection or embedded evidence |
| `INSUFFICIENT_EVIDENCE` | the evidence is not evaluable, not visible, below a configured floor, or lacks a fact basis |

Precedence when several apply: `POLICY_BLOCKED`, `INVALID_REFERENCE`, `CONFLICTING_EVIDENCE`, `INSUFFICIENT_EVIDENCE`, `UNSUPPORTED`, `UNVERIFIABLE`. Every reason is kept in the result.

## Release decision

`APPROVE` (all verified), `RELEASE_VERIFIED_ONLY` (some verified, the rest only unverifiable or insufficient), `REGENERATE` (nothing verified, or a claim is wrong, blocked or invalid), `NOTHING_TO_VERIFY` (refusal or empty). Mixed results are always reported per claim. The regenerate loop itself belongs to the composing layer (Phase 18).

## Layout

| Module | Role |
| --- | --- |
| `evidence.py` | trusted evidence resolution from the bundles; bundle integrity; optional independent recomputation |
| `text.py` | closed-vocabulary text analysis (English first; small Hindi and Hinglish vocabulary) |
| `policy.py` | prohibited categories, death timing, injection, forged authority, claimed verification |
| `engine.py` | `Verifier`, `VerifierConfig`, the stages and the response assembly |
| `pipeline.py` | `verify_narration`, `apply_report` (the only place `VERIFIED` is applied) |

## Determinism, audit, safety

No clock, randomness, network or model. Identical inputs give an identical `report_hash`. A result holds ids, reason codes, hashes and versions, a hash of the claim text, never the text, a prompt or an image reference. Narration is untrusted: a claim cannot mark itself verified, embed evidence, change a version or instruct a tool; it can only be judged against the bundles.

## Known limitations

- The text check is lexical grounding over a closed vocabulary, not entailment. It cannot judge prose outside the vocabulary (that is `UNVERIFIABLE`) and it checks an interpretation against the rule's tags, effect class, source and status, not against the source's full wording.
- Hindi and Hinglish coverage is a small vocabulary (`CALIBRATION_REQUIRED`); the Phase 13 lexicon is English only.
- Astrology rules are not re-derived. The injected recomputation hook is the independent check; independent recalculation from birth data is not done (the verifier is given no birth data).
- Claims built on several non-conflicting source profiles are `UNVERIFIABLE` (no source-policy rule exists for merging profiles).
- Not built (Phase 18): the regenerate loop, persistence of results, a signed attestation, an HTTP surface.
- No real model has been run anywhere in the chain; every integration test used the scripted Phase 14 runtime.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

The unit tests need only the contracts: the palm bundle is a real `PalmEvidenceBundle` built from synthetic facts, and the astrology bundle is a structural stand-in with the Phase 6 hashing rule. `tests/integration/test_verification_phase16.py` runs the real Phase 13 and Phase 6 bundles through the real agent and the verifier.
