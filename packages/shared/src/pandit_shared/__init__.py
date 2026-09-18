"""Cross-cutting utilities shared by `server/` and `services/*`.

Phase 3 scope only: a base settings class (`BaseServiceSettings`) and a
structured JSON logging setup (`configure_logging`). No astrology, agent,
or domain logic lives here -- see `docs/ARCHITECTURE.md` "Repository
Structure" for what `packages/shared` is and is not for.
"""

from pandit_shared.config import BaseServiceSettings
from pandit_shared.logging import configure_logging

__all__ = ["BaseServiceSettings", "configure_logging"]

__version__ = "0.1.0"
