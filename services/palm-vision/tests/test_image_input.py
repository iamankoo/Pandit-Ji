from __future__ import annotations

import cv2
import numpy as np
import pytest
from pandit_contracts.palm_canonical import sha256_bytes

from pandit_palm_vision.image_input import (
    ImageDecodeError,
    decode_image,
    image_from_array,
    normalized_hash,
)


def _png(width: int = 64, height: int = 48) -> bytes:
    pixels = np.zeros((height, width, 3), dtype=np.uint8)
    pixels[:, : width // 2] = (200, 100, 50)
    ok, encoded = cv2.imencode(".png", pixels)
    assert ok
    return bytes(encoded.tobytes())


def test_the_content_hash_is_of_the_original_bytes() -> None:
    data = _png()
    image = decode_image(data, "IMG-1")
    assert image.content_sha256 == sha256_bytes(data)
    assert image.ref.content_sha256 == sha256_bytes(data)
    assert (image.width, image.height) == (64, 48)


def test_decoding_is_deterministic() -> None:
    one = decode_image(_png(), "IMG-1")
    two = decode_image(_png(), "IMG-1")
    assert one.normalized_input_sha256 == two.normalized_input_sha256
    assert one.normalized_input_sha256 == normalized_hash(one.pixels)


@pytest.mark.parametrize("data", [b"", b"not an image at all", b"\x89PNG\r\n\x1a\ntruncated"])
def test_undecodable_input_is_rejected(data: bytes) -> None:
    with pytest.raises(ImageDecodeError):
        decode_image(data, "IMG-X")


def test_unsupported_sizes_are_rejected() -> None:
    with pytest.raises(ImageDecodeError):
        decode_image(_png(width=4, height=4), "IMG-TINY")
    with pytest.raises(ImageDecodeError):
        image_from_array(np.zeros((40, 40), dtype=np.uint8), "IMG-GRAY")


def test_the_image_reference_never_carries_pixels() -> None:
    image = decode_image(_png(), "IMG-1")
    assert set(image.ref.model_dump()) == {"image_id", "content_sha256"}


def test_an_array_image_hash_is_of_the_raw_buffer() -> None:
    pixels = np.full((32, 32, 3), 7, dtype=np.uint8)
    one = image_from_array(pixels, "A")
    two = image_from_array(pixels.copy(), "B")
    assert one.content_sha256 == two.content_sha256
    assert one.content_sha256 != image_from_array(pixels + 1, "A").content_sha256
