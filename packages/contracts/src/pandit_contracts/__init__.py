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

Phase 16 adds the verification contracts (`verification`): `VerificationStatus`,
`ClaimVerification`, `VerificationResponse`, the reason codes and the release action. Only the
verification layer may produce `VERIFIED`; the agent contracts are unchanged.

Phase 17 adds the life-domain contracts (`domain`): `LifeDomain` (the 27 domains and the
extensions), `DomainAnalysisRequest` (no sex field, no inferred age), `DomainAnalysisResult` with
its facts, rule results, versions and typed reasons. `EvidenceCapability` gains the additive
`ASTRO_DOMAIN`; nothing else in the agent or verification contracts changes.

The Astrology Service Interfaces (`ChartRequest`/`ChartResponse`, `DashaRequest`/`DashaResponse`,
etc. -- see `docs/ARCHITECTURE.md` "Astrology Service Interfaces") are domain contracts defined
by the phase that implements the corresponding engine.
"""

from pandit_contracts.health import HealthStatus

__all__ = ["HealthStatus"]

__version__ = "0.6.0"
