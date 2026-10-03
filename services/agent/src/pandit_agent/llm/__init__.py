"""Self-hosted LLM capability (Phase 14): the AI Reasoner interface behind ``agent``.

``LLMProvider`` (``provider``) is what Phase 15 calls. ``LLMService`` (``service``) implements it
over a runtime: ``VLLMServerRuntime`` for a self-hosted vLLM server, or the scripted
``MockRuntime`` in CI. This package has no planner, memory, tool selection, narration or
verification, and no client for any hosted third-party model API.
"""

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.provider import LLMProvider
from pandit_agent.llm.service import LLMService, create_service

__all__ = ["LLMFailure", "LLMProvider", "LLMService", "create_service"]
