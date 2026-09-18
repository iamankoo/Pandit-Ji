# pandit-contracts

Shared Pydantic contracts used by `server/` and every `services/*` component.

## Phase 3 scope

Only `HealthStatus` (component/state/version) exists so far — the common shape every health check returns.

## Future scope (not implemented here)

The Astrology Service Interfaces defined in `docs/ARCHITECTURE.md` §"Astrology Service Interfaces" (`ChartRequest`/`ChartResponse`, `DashaRequest`/`DashaResponse`, `TransitRequest`/`TransitResponse`, `PanchangRequest`/`PanchangResponse`, `CompatibilityRequest`/`CompatibilityResponse`, `NumerologyRequest`/`NumerologyResponse`, `RuleEvaluationRequest`/`RuleEvaluationResponse`, `KnowledgeRetrievalRequest`/`KnowledgeRetrievalResponse`) belong here, added starting with the `Phases.md` phase that implements the corresponding engine — not defined speculatively in Phase 3.

## Install (editable, for local development)

```
pip install -e ".[dev]"
```
