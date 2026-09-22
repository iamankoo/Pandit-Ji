"""Shared test helpers for the Ashtakavarga suite (Phase 9 WP-A1)."""

from __future__ import annotations

import json
from pathlib import Path

from pandit_astro_engine.ashtakavarga.constants import Contributor

FIXTURES = Path(__file__).parent / "fixtures"


def load_source_comparison() -> dict:
    return json.loads((FIXTURES / "ashtakavarga_source_comparison.json").read_text())


def load_brihat_jataka_worked_example() -> dict:
    return json.loads((FIXTURES / "ashtakavarga_brihat_jataka_worked_example.json").read_text())


def natal_longitudes(raw: dict[str, float]) -> dict[Contributor, float]:
    return {Contributor(key): value for key, value in raw.items()}
