"""Model loader: validate, verify, load, and report readiness honestly.

The loader never downloads anything. Acquisition is an explicit operator step (see
``services/agent/llm/README.md``); the loader only checks that what is present is what the
manifest pins, asks the runtime to make the model ready, and records the outcome. A service that
started but could not load its model reports ``MODEL_UNAVAILABLE`` or ``MODEL_ERROR``, never
``MODEL_READY``.
"""

from __future__ import annotations

import time
from pathlib import Path

from pandit_contracts.llm import LLMErrorCode, Readiness

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.manifest import ModelManifest, verify_model_directory
from pandit_agent.llm.runtime import LLMRuntime

# The model or its runtime is not there (or not yet): recoverable by an operator action.
_UNAVAILABLE = frozenset(
    {
        LLMErrorCode.MODEL_UNAVAILABLE,
        LLMErrorCode.RUNTIME_UNAVAILABLE,
        LLMErrorCode.GPU_UNAVAILABLE,
        LLMErrorCode.INSUFFICIENT_RESOURCES,
        LLMErrorCode.ENDPOINT_NOT_PERMITTED,
    }
)


class ReadinessTracker:
    def __init__(self) -> None:
        self.state = Readiness.SERVICE_STARTED
        self.last_error: LLMErrorCode | None = None
        self.load_ms: float | None = None
        self.artifacts_verified = False

    def begin_loading(self) -> None:
        self.state = Readiness.MODEL_LOADING
        self.last_error = None

    def ready(self, load_ms: float, *, artifacts_verified: bool) -> None:
        self.state = Readiness.MODEL_READY
        self.load_ms = load_ms
        self.artifacts_verified = artifacts_verified

    def fail(self, failure: LLMFailure) -> None:
        self.last_error = failure.code
        self.state = (
            Readiness.MODEL_UNAVAILABLE if failure.code in _UNAVAILABLE else Readiness.MODEL_ERROR
        )


class ModelLoader:
    def __init__(
        self,
        manifest: ModelManifest,
        runtime: LLMRuntime,
        tracker: ReadinessTracker,
        *,
        model_dir: Path | None = None,
        verify_artifacts: bool = True,
    ) -> None:
        self._manifest = manifest
        self._runtime = runtime
        self._tracker = tracker
        self._model_dir = model_dir
        self._verify = verify_artifacts

    def load(self) -> Readiness:
        self._tracker.begin_loading()
        started = time.perf_counter()
        verified = False
        try:
            if self._model_dir is not None and self._verify:
                verified = verify_model_directory(self._manifest, self._model_dir) > 0
            self._runtime.load(self._manifest)
        except LLMFailure as failure:
            self._tracker.fail(failure)
        else:
            self._tracker.ready(
                (time.perf_counter() - started) * 1000.0, artifacts_verified=verified
            )
        return self._tracker.state
