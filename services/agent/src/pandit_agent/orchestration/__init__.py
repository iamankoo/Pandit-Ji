"""Agent orchestration and narration (Phase 15).

``AgentOrchestrator.run(AgentRequest) -> NarrationResponse`` is the entry point. Everything the
model sees is built from trusted templates and typed evidence; everything it returns is parsed into
grounded, ``UNVERIFIED`` claims that Phase 16 can verify. This package owns planning, bounded tool
selection over allow-listed evidence tools, context assembly, narration, policy enforcement and
short-lived conversation context. It does not compute facts, run a model, verify claims or persist
user data.
"""

from pandit_agent.orchestration.adapters import AstrologyBundleTool, PalmBundleTool
from pandit_agent.orchestration.memory import InMemoryConversationMemory
from pandit_agent.orchestration.orchestrator import AgentConfig, AgentOrchestrator
from pandit_agent.orchestration.prompts import narration_schema_registry
from pandit_agent.orchestration.tools import ToolRegistry

__all__ = [
    "AgentConfig",
    "AgentOrchestrator",
    "AstrologyBundleTool",
    "InMemoryConversationMemory",
    "PalmBundleTool",
    "ToolRegistry",
    "narration_schema_registry",
]
