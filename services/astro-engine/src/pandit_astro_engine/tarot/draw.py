"""Deterministic Tarot draws (Phase 9 WP-I; `docs/ASTROLOGY_STANDARDS.md`
v1.19.0, TA-04 to TA-08).

Randomness is isolated here and is never taken from the system: the caller
supplies a seed string, and a SHA-256 counter stream turns it into uniform
integers by rejection sampling (`_SeededStream`). The deck is shuffled with
Fisher-Yates over that stream; when reversals are allowed each drawn card's
orientation is one further bit of the stream. The same seed, deck, spread
and reversal setting always give the same layout, on every platform and
Python version, because nothing depends on the `random` module.

Waite's physical procedure (shuffle, cut three times, lay out from the top)
is modelled by this seeded shuffle and top-of-pack deal -- an engineering
equivalent, not a claim that the two are the same act.
"""

from __future__ import annotations

import hashlib

STREAM_ID = "SHA256_COUNTER_REJECTION_V1"


class _SeededStream:
    def __init__(self, seed: str) -> None:
        self._key = hashlib.sha256(("pandit-tarot|" + seed).encode("utf-8")).digest()
        self._counter = 0
        self._buffer = b""

    def _bytes(self, n: int) -> bytes:
        while len(self._buffer) < n:
            block = hashlib.sha256(self._key + self._counter.to_bytes(8, "big")).digest()
            self._buffer += block
            self._counter += 1
        out, self._buffer = self._buffer[:n], self._buffer[n:]
        return out

    def below(self, n: int) -> int:
        """Uniform integer in [0, n) by rejection sampling on 32-bit words."""
        if n <= 0:
            raise ValueError("n must be positive")
        limit = (2**32 // n) * n
        while True:
            value = int.from_bytes(self._bytes(4), "big")
            if value < limit:
                return value % n


def seeded_shuffle(items: list[str], seed: str) -> tuple[list[str], _SeededStream]:
    """Fisher-Yates shuffle of a copy of `items`; returns the stream so the
    caller can continue drawing orientation bits from the same seed."""
    stream = _SeededStream(seed)
    out = list(items)
    for i in range(len(out) - 1, 0, -1):
        j = stream.below(i + 1)
        out[i], out[j] = out[j], out[i]
    return out, stream


def seed_digest(seed: str) -> str:
    """SHA-256 of the seed, recorded on results instead of the seed itself."""
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()
