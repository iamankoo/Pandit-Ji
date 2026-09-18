"""rule-engine: structured astrology rules and deterministic rule evaluation.

Phase 3 scope only: package boundary, config, and a health check. Rule
schema/evaluation logic (see `docs/ARCHITECTURE.md` §"Rule Engine
Architecture" and `docs/ASTROLOGY_STANDARDS.md` §"Yoga / Dosha standards")
is implemented starting `Phases.md` Phase 6.

Consumes `astro-engine` output only; never computes chart facts itself and
never produces user-facing natural language.
"""

from pandit_rule_engine._version import __version__
from pandit_rule_engine.health import get_health

__all__ = ["get_health", "__version__"]
