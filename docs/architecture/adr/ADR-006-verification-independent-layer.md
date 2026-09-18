# ADR-006: Verification as an independent layer

Status: Locked (Phase 1/Phase 2)

## Context
A claim-checking step embedded inside the `agent`'s own generation loop could be skipped, weakened, or silently bypassed under prompt/agent changes, since it would share fate with the component it's supposed to check.

## Decision
`verification` is its own canonical service (not a submodule of `agent`), with direct access to the same evidence bundle the `agent` used to produce a draft response, plus the draft response itself. It performs fact validation, rule validation, evidence validation, unsupported-claim detection, and contradiction detection, and returns PASS or REGENERATE (see `docs/ARCHITECTURE.md` §"Verification Architecture"). `agent` must call `verification` before releasing any response for which verification is mandatory (per `docs/ASTROLOGY_STANDARDS.md`'s Prediction Language Policy and the Verification & Evaluation table) and must not release an unverified response in that case.

## Consequences
- `verification` can be tested, versioned, and improved independently of `agent`'s prompt/model changes.
- `verification` is not a generic spell-checker or a second LLM call with a vague "does this look right" prompt — it operates against the same structured evidence bundle, checking specific, enumerable failure modes.
- A verification failure is a first-class outcome (regenerate, strip claim, or add caveat), not an exception path.
