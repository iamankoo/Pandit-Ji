"""Bounded, short-lived conversation memory (Phase 15 scope).

What Phase 15 owns: *conversation context* inside a session. What it does not own: persistent
long-term memory (saved profiles, a journal, feedback history). That needs user-scoped storage,
consent, retention and deletion infrastructure, which are Phase 18 (``docs/ARCHITECTURE.md``
section 17; `FUTURE_PHASE`). A persistent store would implement the ``ConversationMemory``
protocol later.

Privacy by construction: the in-memory implementation stores only the *labels* of earlier turns
(domain, intent, language), never the user's text, never a generated narration, never evidence and
never an image. It lives in process memory only, expires, is size-bounded, and can be erased with
``forget``. Memory can only influence how a follow-up is routed; it cannot add, change or supply a
fact (``docs/ARCHITECTURE.md`` section 17).
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pandit_contracts.agent import Domain, Intent
from pandit_contracts.llm import LLMLanguage


@dataclass(frozen=True)
class MemorySnapshot:
    last_domain: Domain | None
    last_intent: Intent | None
    topics: tuple[Intent, ...]
    turns: int


class ConversationMemory(Protocol):
    def recall(self, conversation_id: str) -> MemorySnapshot | None: ...

    def remember(
        self, conversation_id: str, domain: Domain, intent: Intent, language: LLMLanguage
    ) -> None: ...

    def forget(self, conversation_id: str) -> None: ...


@dataclass
class _Entry:
    turns: list[tuple[Domain, Intent, LLMLanguage]]
    touched_at: float


class InMemoryConversationMemory:
    def __init__(
        self,
        *,
        max_conversations: int = 1000,
        max_turns: int = 6,
        ttl_s: float = 1800.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_conversations = max_conversations
        self._max_turns = max_turns
        self._ttl_s = ttl_s
        self._clock = clock
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    def _expire(self) -> None:
        now = self._clock()
        for key in [k for k, e in self._entries.items() if now - e.touched_at > self._ttl_s]:
            del self._entries[key]

    def recall(self, conversation_id: str) -> MemorySnapshot | None:
        self._expire()
        entry = self._entries.get(conversation_id)
        if entry is None or not entry.turns:
            return None
        domain, intent, _ = entry.turns[-1]
        topics = tuple(dict.fromkeys(t[1] for t in entry.turns))
        return MemorySnapshot(domain, intent, topics, len(entry.turns))

    def remember(
        self, conversation_id: str, domain: Domain, intent: Intent, language: LLMLanguage
    ) -> None:
        self._expire()
        entry = self._entries.pop(conversation_id, None) or _Entry([], self._clock())
        entry.turns.append((domain, intent, language))
        del entry.turns[: -self._max_turns]
        entry.touched_at = self._clock()
        self._entries[conversation_id] = entry
        while len(self._entries) > self._max_conversations:
            self._entries.popitem(last=False)

    def forget(self, conversation_id: str) -> None:
        self._entries.pop(conversation_id, None)

    def __len__(self) -> int:
        return len(self._entries)
