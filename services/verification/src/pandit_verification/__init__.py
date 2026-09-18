"""verification: fact validation, rule validation, evidence validation,
unsupported-claim detection, contradiction detection; owns the
regression-test and backtesting framework.

Phase 3 scope only: package boundary, config, health check. Verification
logic is implemented starting `Phases.md` Phase 16 -- see
`docs/ARCHITECTURE.md` §"Verification Architecture" and
`docs/architecture/adr/ADR-006-verification-independent-layer.md`.

Never generates narrative content; never a generic grammar/style checker.
"""

from pandit_verification._version import __version__
from pandit_verification.health import get_health

__all__ = ["get_health", "__version__"]
