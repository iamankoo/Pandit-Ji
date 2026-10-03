"""Pandit Ji shared contracts.

Phase 3 (Repository & Engineering Foundation) established the package boundary and the
`HealthStatus` contract shared by `server/` and every `services/*` component's health check.

Phase 13 adds the palm contracts (`palm`, `palm_canonical`, `palm_policy`, `palm_coverage`):
`PalmFactSet`, `PalmFact`, `PalmRuleEvaluation`, `PalmEvidenceBundle`, canonical serialization,
the prohibited-interpretation policy and the source coverage manifest models. Import them from
their modules (for example `pandit_contracts.palm`).

Phase 14 adds the self-hosted LLM contracts (`llm`): `LLMRequest`, `LLMResponse`,
the typed error and readiness vocabularies and the model provenance block.

Phase 15 adds the agent and narration contracts (`agent`): `AgentRequest`, `EvidenceRecord`,
`AgentContext`, `AgentPlan`, `NarrationResponse` with its structured, `UNVERIFIED` claims and
references, and the typed agent errors. Phase 14's `LLMContext` gains an additive, optional
`task` field (a trusted task instruction); request hashes without it are unchanged.

The Astrology Service Interfaces (`ChartRequest`/`ChartResponse`, `DashaRequest`/`DashaResponse`,
etc. -- see `docs/ARCHITECTURE.md` "Astrology Service Interfaces") are domain contracts defined
by the phase that implements the corresponding engine.
"""

from pandit_contracts.health import HealthStatus

__all__ = ["HealthStatus"]

__version__ = "0.4.0"
