"""agent (Agent Orchestrator): intent detection, planning, tool invocation,
evidence assembly, AI Reasoner invocation, verification invocation, memory
access.

Phase 3 scope only: package boundary, config, health check, and empty
`voice/`/`reports/` subpackages (per `docs/ARCHITECTURE.md` §"Repository
Structure" note -- these are subpackages of `agent`, not top-level
services). Planning/orchestration logic is implemented starting
`Phases.md` Phase 15; see ADR-003 for the service boundary.

Never computes an astrology fact itself; never bypasses `verification`
for a response type where verification is mandatory.
"""

from pandit_agent._version import __version__
from pandit_agent.health import get_health

__all__ = ["get_health", "__version__"]
