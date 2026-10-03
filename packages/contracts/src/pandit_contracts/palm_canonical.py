"""Canonical serialization, fixed-point numbers and hashing for palm facts (Phase 13).

`docs/ASTROLOGY_STANDARDS.md` v1.27.0 PM-14: canonical JSON with sorted keys and no
insignificant whitespace, **no floating-point numbers**, geometry as fixed-point integers
(`PCF-1`, 10^-4 of the palm unit), scores as integer basis points, SHA-256 hashes. Runtime
fields (timestamps, host names, timings) never enter a content identity.

The rule is enforced, not documented only: `canonical_json` raises `FloatInCanonicalDataError`
for any float anywhere in the value, so a float cannot silently enter a fact, a bundle or a
report.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

# Palm-canonical frame, version 1 (PM-14): origin at the wrist landmark, unit = distance from
# the wrist landmark to the middle-finger base landmark, "up" along that vector.
PCF_FRAME_ID = "PCF-1"
# 10^-4 of the palm unit.
PCF_SCALE = 10_000
# Integer basis points: 0..10_000 is 0..100 percent.
BASIS_POINTS = 10_000

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class FloatInCanonicalDataError(TypeError):
    """A floating-point number reached canonical data."""


def to_fixed(value: float, scale: int = PCF_SCALE) -> int:
    """Quantize a float to a fixed-point integer, round-half-even, once, at the model output.

    ``NaN`` and infinities are rejected: a missing measurement is represented by an explicit
    visibility state, never by a special float.
    """
    if not math.isfinite(value):
        raise ValueError("a non-finite value cannot be quantized")
    return round(value * scale)


def from_fixed(value: int, scale: int = PCF_SCALE) -> float:
    """Convert a fixed-point integer back to a float (for computation only, never stored)."""
    return value / scale


def to_basis_points(fraction: float) -> int:
    """A fraction in [0, 1] as integer basis points, clamped to the valid range."""
    if not math.isfinite(fraction):
        raise ValueError("a non-finite score cannot be quantized")
    return min(BASIS_POINTS, max(0, round(fraction * BASIS_POINTS)))


def _reject_floats(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise FloatInCanonicalDataError(f"floating-point number at {path}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"non-string key at {path}")
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


def canonical_json(value: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, UTF-8 text, no floats."""
    _reject_floats(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(value: Any) -> str:
    """SHA-256 of a string (as UTF-8) or of the canonical JSON of any other value."""
    text = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha256_hex(value: str) -> bool:
    return bool(SHA256_PATTERN.match(value))


def hash_list(hashes: Sequence[str]) -> str:
    """SHA-256 over the *sorted* list of hashes (order of the input never matters)."""
    return sha256_hex(sorted(hashes))
