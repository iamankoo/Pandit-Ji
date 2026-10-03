from __future__ import annotations

import pytest

from pandit_contracts.palm_canonical import (
    FloatInCanonicalDataError,
    canonical_json,
    from_fixed,
    hash_list,
    is_sha256_hex,
    sha256_hex,
    to_basis_points,
    to_fixed,
)


def test_canonical_json_sorts_keys_and_is_compact() -> None:
    assert canonical_json({"b": 1, "a": [2, {"d": 4, "c": 3}]}) == '{"a":[2,{"c":3,"d":4}],"b":1}'


def test_key_order_does_not_change_the_hash() -> None:
    one = {"x": 1, "y": {"p": [1, 2], "q": "é"}}
    two = {"y": {"q": "é", "p": [1, 2]}, "x": 1}
    assert canonical_json(one) == canonical_json(two)
    assert sha256_hex(one) == sha256_hex(two)


def test_same_representation_same_hash_and_text_is_hashed_as_utf8() -> None:
    assert sha256_hex({"a": 1}) == sha256_hex('{"a":1}')
    assert is_sha256_hex(sha256_hex("x"))
    assert not is_sha256_hex("ABC")


@pytest.mark.parametrize(
    "value",
    [1.5, {"a": 0.1}, [1, 2.0], {"a": {"b": [(1, 2.5)]}}, (1.0,)],
)
def test_floats_cannot_enter_canonical_data(value: object) -> None:
    with pytest.raises(FloatInCanonicalDataError):
        canonical_json(value)


def test_integers_bools_strings_and_none_are_allowed() -> None:
    assert canonical_json({"a": True, "b": None, "c": "s", "d": -3}) == (
        '{"a":true,"b":null,"c":"s","d":-3}'
    )


def test_non_string_keys_are_rejected() -> None:
    with pytest.raises(TypeError):
        canonical_json({1: "a"})


def test_to_fixed_rounds_half_even_once() -> None:
    # Exactly representable ties (scale 1) go to the even integer.
    assert to_fixed(0.5, 1) == 0
    assert to_fixed(1.5, 1) == 2
    assert to_fixed(2.5, 1) == 2
    assert to_fixed(1.23456) == 12346
    assert to_fixed(-0.5) == -5000
    assert from_fixed(12346) == pytest.approx(1.2346)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_are_rejected_not_encoded(bad: float) -> None:
    with pytest.raises(ValueError):
        to_fixed(bad)
    with pytest.raises(ValueError):
        to_basis_points(bad)


def test_basis_points_clamp_to_the_valid_range() -> None:
    assert to_basis_points(0.9) == 9000
    assert to_basis_points(1.7) == 10_000
    assert to_basis_points(-0.2) == 0


def test_hash_list_ignores_order() -> None:
    assert hash_list(["b", "a", "c"]) == hash_list(["c", "b", "a"])
    assert hash_list(["a"]) != hash_list(["a", "b"])
