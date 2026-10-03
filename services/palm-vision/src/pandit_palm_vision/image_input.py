"""Image input: decoding, content hashing and capture context (Phase 13).

An image enters the pipeline as bytes (or, for synthetic fixtures, an array) and leaves it as
facts that reference it only by ``image_id`` and the SHA-256 of the original bytes. The decoded
pixel array is never part of a fact, a bundle or a log line.

``CaptureContext`` carries what the *capture* knows and the image cannot tell: whether the
image is mirrored (a selfie preview) and whether the palm faces the camera. Unknown values stay
``None`` and make the dependent facts ``NOT_EVALUABLE``: the pipeline never guesses them.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt
from pandit_contracts.palm import ImageRef
from pandit_contracts.palm_canonical import sha256_bytes

MIN_DIMENSION = 16
MAX_DIMENSION = 16_384

ImageArray = npt.NDArray[np.uint8]


class ImageDecodeError(ValueError):
    """The bytes are not a decodable image of a supported size."""


@dataclass(frozen=True)
class CaptureContext:
    """Capture facts supplied by the caller (never inferred from pixels)."""

    mirrored: bool | None = None
    palm_facing: bool | None = None


@dataclass(frozen=True)
class ImageInput:
    image_id: str
    content_sha256: str
    pixels: ImageArray  # BGR, uint8, height x width x 3
    normalized_input_sha256: str

    @property
    def ref(self) -> ImageRef:
        return ImageRef(image_id=self.image_id, content_sha256=self.content_sha256)

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])


def normalized_hash(pixels: ImageArray) -> str:
    """Hash of the decoded pixel array (shape included), so reproducibility is tested on pixels."""
    header = f"{pixels.shape[0]}x{pixels.shape[1]}x{pixels.shape[2]}:{pixels.dtype}".encode()
    return sha256_bytes(header + np.ascontiguousarray(pixels).tobytes())


def _check(pixels: ImageArray) -> None:
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint8:
        raise ImageDecodeError("expected an 8-bit three-channel image")
    height, width = int(pixels.shape[0]), int(pixels.shape[1])
    if min(height, width) < MIN_DIMENSION or max(height, width) > MAX_DIMENSION:
        raise ImageDecodeError("image dimensions are outside the supported range")


def decode_image(data: bytes, image_id: str) -> ImageInput:
    """Decode image bytes. The hash is of the original bytes, computed before any processing."""
    content_sha256 = sha256_bytes(data)
    if not data:
        raise ImageDecodeError("empty input")
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None:
        raise ImageDecodeError("the bytes are not a decodable image")
    pixels: ImageArray = np.asarray(decoded, dtype=np.uint8)
    _check(pixels)
    return ImageInput(image_id, content_sha256, pixels, normalized_hash(pixels))


def image_from_array(pixels: ImageArray, image_id: str) -> ImageInput:
    """Wrap an array (synthetic fixtures).

    The content hash is the hash of the raw pixel buffer with its shape header, not of an
    encoded file: encoders differ between library versions, the buffer does not.
    """
    _check(pixels)
    digest = normalized_hash(pixels)
    return ImageInput(image_id, digest, np.asarray(pixels), digest)
