"""palm-vision: the deterministic palm image pipeline (Phase 13).

IMAGE -> QUALITY -> HAND -> SIDE -> REGION -> LANDMARKS -> LINE/FEATURE ANALYSIS -> FACTS.

It produces structured OBSERVED and DERIVED palm facts (`pandit_contracts.palm.PalmFactSet`) and
nothing else: no knowledge text, no palmistry rules, no narration, no LLM, no upload or storage
API. **No trained palm-line model exists yet**: line analysis honestly reports
``MODEL_UNAVAILABLE`` (or a baseline marked EXPERIMENTAL). Quality thresholds and reproducibility
tolerances are ``CALIBRATION_REQUIRED``. See `docs/ARCHITECTURE.md` section 35, ADR-008 and
`research/PALM_READING.md`.
"""

from pandit_palm_vision._version import __version__
from pandit_palm_vision.health import get_health

__all__ = ["get_health", "__version__"]
