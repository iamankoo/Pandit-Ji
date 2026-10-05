"""verification: the Phase 16 verification engine (ADR-006, ADR-011).

``Verifier.verify(NarrationResponse)`` checks every generated claim against trusted deterministic
evidence (the Phase 13 palm bundle and the Phase 6 astrology bundle) that the verifier resolves
itself, and returns one ``VerificationResponse`` with a per-claim status, reasons, provenance and
uncertainty. It is the only component that may produce ``VERIFIED``.

Verified means *supported by the application's encoded evidence and rule model*. It does not mean
that astrology or palmistry is scientifically valid, and the text check is closed-vocabulary
lexical grounding, not natural-language entailment (see ``docs/ARCHITECTURE.md`` section 38).

It never generates narrative content, never calls a model, and has no network or persistence.
"""

from pandit_verification._version import __version__
from pandit_verification.engine import Verifier, VerifierConfig, verifier_identity
from pandit_verification.evidence import TrustedEvidence
from pandit_verification.health import get_health
from pandit_verification.pipeline import VerifiedOutcome, apply_report, verify_narration

__all__ = [
    "TrustedEvidence",
    "VerifiedOutcome",
    "Verifier",
    "VerifierConfig",
    "__version__",
    "apply_report",
    "get_health",
    "verifier_identity",
    "verify_narration",
]
