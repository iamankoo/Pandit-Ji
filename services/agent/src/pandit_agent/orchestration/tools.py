"""Typed evidence tools: a closed, allow-listed registry the planner can draw on.

A tool contributes deterministic evidence for named capabilities. It takes **no free-form
arguments**: the only input is the set of capabilities the plan asked for, so there is nothing a
user can steer, no code to execute and no query to inject. Each tool declares a timeout and a call
budget, runs on a worker thread so a slow tool fails with a typed result, and returns typed
``EvidenceRecord`` objects. The agent never computes a fact itself: tools hand over what the
deterministic components (Phase 13 evidence, the astrology evidence bundle) already produced.
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Protocol

from pandit_contracts.agent import (
    AgentErrorCode,
    Domain,
    EvidenceCapability,
    EvidenceRecord,
)

from pandit_agent.orchestration.errors import AgentFailure


@dataclass(frozen=True)
class ToolSpec:
    name: str
    domain: Domain
    capabilities: frozenset[EvidenceCapability]
    timeout_s: float = 5.0
    max_calls: int = 1


@dataclass(frozen=True)
class ToolResult:
    records: tuple[EvidenceRecord, ...]


class EvidenceTool(Protocol):
    @property
    def spec(self) -> ToolSpec: ...

    def invoke(self, capabilities: frozenset[EvidenceCapability]) -> ToolResult: ...


class ToolRegistry:
    """The allow-list. Only tools registered here can ever be planned or called."""

    def __init__(self, tools: Iterable[EvidenceTool] = ()) -> None:
        self._tools: dict[str, EvidenceTool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: EvidenceTool) -> None:
        spec = tool.spec
        if spec.name in self._tools:
            raise ValueError(f"duplicate tool name {spec.name!r}")
        if spec.timeout_s <= 0 or spec.max_calls < 1:
            raise ValueError("a tool needs a positive timeout and call budget")
        self._tools[spec.name] = tool

    def get(self, name: str) -> EvidenceTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise AgentFailure(
                AgentErrorCode.TOOL_NOT_ALLOWED, f"tool {name!r} is not in the allow-list"
            ) from exc

    def tools_for(self, capability: EvidenceCapability, domain: Domain) -> tuple[ToolSpec, ...]:
        return tuple(
            t.spec
            for t in self._tools.values()
            if capability in t.spec.capabilities and t.spec.domain is domain
        )

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))


def run_tool(tool: EvidenceTool, capabilities: frozenset[EvidenceCapability]) -> ToolResult:
    """Run one tool call with its declared timeout. Failures are typed, never raw exceptions."""
    spec = tool.spec
    allowed = capabilities & spec.capabilities
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pj-tool")
    future = pool.submit(tool.invoke, allowed)
    try:
        result = future.result(timeout=spec.timeout_s)
    except FutureTimeout as exc:
        raise AgentFailure(
            AgentErrorCode.TOOL_TIMEOUT, f"tool {spec.name!r} exceeded its timeout", retryable=True
        ) from exc
    except AgentFailure:
        raise
    except Exception as exc:  # a tool is third-party-shaped code: contain it, never leak it
        raise AgentFailure(
            AgentErrorCode.TOOL_FAILURE, f"tool {spec.name!r} failed ({type(exc).__name__})"
        ) from exc
    finally:
        pool.shutdown(wait=False)
    for record in result.records:
        if record.domain is not spec.domain:
            raise AgentFailure(
                AgentErrorCode.TOOL_FAILURE,
                f"tool {spec.name!r} returned evidence of another domain",
            )
    return result
