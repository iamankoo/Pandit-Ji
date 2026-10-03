# palm-vision

The deterministic palm image pipeline (`Phases.md` Phase 13; `docs/architecture/adr/ADR-008-palm-vision-component.md`; `docs/ARCHITECTURE.md` section 35). Canonical service name, do not rename.

```
IMAGE -> QUALITY -> HAND -> SIDE -> REGION -> LANDMARKS -> LINE/FEATURE ANALYSIS -> FACTS
```

It produces structured **OBSERVED** and **DERIVED** palm facts (`pandit_contracts.palm.PalmFactSet`) with provenance, and nothing else. It owns no palm rules (those live in `services/rule-engine/palm_rules/`), no knowledge text, no narration, no LLM, and no upload or storage API. It depends only on `packages/contracts` and `packages/shared`; a test asserts it imports no other service.

## Status (honest)

| Area | State |
| --- | --- |
| Quality gate, hand/side abstraction, PCF-1 frame, landmarks, facts, evidence inputs, artifact policy, reproducibility comparison, evaluation harness | IMPLEMENTED (synthetic and fixture data only) |
| Palm-line / feature analysis | PARTIALLY IMPLEMENTED: interface and an EXPERIMENTAL classical baseline; without a pinned model the status is `MODEL_UNAVAILABLE` |
| Trained and validated palm-line model, hand and landmark model artifact | MODEL_REQUIRED (none exists; no accuracy is claimed) |
| Consented evaluation dataset | DATASET_REQUIRED (nothing in git; the synthetic set only proves the metric plumbing) |
| Quality thresholds, reproducibility tolerances, acceptance thresholds | CALIBRATION_REQUIRED (the default configuration never returns ACCEPT; tolerances are stored under `tolerances/`) |
| Consent, retention, minors, training reuse | LEGAL_GATE (not implemented, not resolved; Phase 18 owns the workflows) |

## Behaviour that must not change

- The hand side is never guessed: it is `UNDETERMINED` when it cannot be established. Mirroring is explicit, never silent.
- Missing visual information is `NOT_EVALUABLE`, never inferred. Mount volume is not observable from one 2D image.
- Facts are canonical: integers only, geometry in PCF-1 at 10^-4 palm unit, scores in basis points, SHA-256 identities, timestamps never part of identity. Image bytes never enter a fact, a log or the evidence; the image is referenced by id and content hash.
- Model weights are never committed. Every artifact needs an id, version, SHA-256, source and licence; a missing or mismatched artifact is a failure, not a silent fallback. MediaPipe is optional and only localises the hand; it is not palmistry.

## Development

```
pip install -e ../../packages/contracts -e ../../packages/shared -e ".[dev]"
python -m ruff check . && python -m ruff format --check . && python -m mypy src && python -m pytest -q
```

CI needs no GPU, no model weights and no user data.
