"""Canonical serialization and content hashing (Phase 6E).

The ruleset content hash identifies exactly which rules and tables produced a
result. It is computed from the *logical* parsed documents -- never from file
bytes, file paths, YAML key order, comments or filesystem traversal order --
so two rulesets that mean the same thing hash the same.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pandit_rule_engine.loader import Ruleset

HASH_ALGORITHM = "sha256"


def canonical_json(value: Any) -> str:
    """Deterministic JSON: sorted keys, no insignificant whitespace, UTF-8-safe."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ruleset_content_hash(ruleset: Ruleset) -> str:
    """Hash of every logical document in the ruleset, in sorted-ID order."""
    payload = {
        "algorithm": HASH_ALGORITHM,
        "documents": [ruleset.documents[key] for key in sorted(ruleset.documents)],
    }
    return sha256_hex(canonical_json(payload))
