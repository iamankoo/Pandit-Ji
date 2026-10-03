"""Pipeline, preprocessing and runtime identities (provenance inputs; standards PM-14, PM-15).

Every fact must answer "what exact image, pipeline, model, configuration and upstream facts
produced me": these identities are the pipeline, preprocessing and runtime part of that answer.
Nothing here records personal data.
"""

from __future__ import annotations

import platform
from importlib import metadata

from pandit_contracts.palm import RuntimeIdentity
from pandit_contracts.palm_canonical import sha256_hex

from pandit_palm_vision._version import __version__

PIPELINE_VERSION = __version__
PREPROCESSING_ID = "PALM_PREPROCESSING"
PREPROCESSING_VERSION = "1"
# Decoder behaviour is part of the preprocessing identity: the decoder applies the EXIF
# orientation, and colour is handled as 8-bit BGR.
PREPROCESSING_PARAMETERS: dict[str, str | int] = {
    "decoder": "cv2.imdecode",
    "color": "BGR8",
    "exif_orientation": "APPLIED_BY_DECODER",
    "gray": "cv2.COLOR_BGR2GRAY",
    "roi_size": 256,
}
INFERENCE_CONFIG: dict[str, str | int] = {
    "inference": "DETERMINISTIC_CPU",
    "float_dtype": "float64",
    "rounding": "ROUND_HALF_EVEN_ONCE_AT_OUTPUT",
}

TRACKED_PACKAGES = ("numpy", "opencv-python-headless", "pydantic", "mediapipe", "torch")


def preprocessing_parameters_sha256() -> str:
    return sha256_hex(PREPROCESSING_PARAMETERS)


def inference_config_sha256() -> str:
    return sha256_hex(INFERENCE_CONFIG)


def _version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def runtime_identity(threads: int | None = None) -> RuntimeIdentity:
    """Interpreter and the tracked library versions (sorted, absent packages omitted)."""
    packages = tuple(
        sorted((name, version) for name in TRACKED_PACKAGES if (version := _version(name)))
    )
    return RuntimeIdentity(
        python=platform.python_version(),
        packages=packages,
        device_class="CPU",
        determinism_mode="DETERMINISTIC_CPU_FLOAT64",
        threads=threads,
    )
