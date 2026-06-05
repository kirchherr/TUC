from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
    reference_softmax,
)

_GOLDEN_DIR = Path(__file__).parent / "golden" / "kernels"
_GOLDEN_FILES = (
    "matmul.json",
    "elementwise_relu.json",
    "reduction_sum_axis1.json",
    "softmax_axis1.json",
)


@pytest.mark.parametrize("fixture_name", _GOLDEN_FILES)
def test_mvp_reference_kernel_matches_golden(fixture_name: str) -> None:
    fixture = json.loads((_GOLDEN_DIR / fixture_name).read_text(encoding="utf-8"))

    result = _evaluate_fixture(fixture)
    expected = np.array(fixture["expected"], dtype=np.float64)

    assert_allclose(result, expected, rtol=1e-12, atol=1e-12)


def test_reference_matmul_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="dimensions must agree"):
        reference_matmul(
            np.array([[1.0, 2.0]], dtype=np.float64),
            np.array([[1.0, 2.0]], dtype=np.float64),
        )


def test_reference_kernel_rejects_object_dtype() -> None:
    with pytest.raises(TypeError, match="dtype must be numeric"):
        reference_elementwise(np.array([object()], dtype=object), "identity")


def test_reference_kernel_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        reference_softmax(np.array([[1.0, float("inf")]], dtype=np.float64))


def test_reference_reduction_rejects_out_of_bounds_axis() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        reference_reduction_sum(np.array([[1.0]], dtype=np.float64), axis=2)


def _evaluate_fixture(fixture: object) -> np.ndarray:
    if type(fixture) is not dict:
        raise TypeError("golden kernel fixture must be a JSON object")
    operation = fixture.get("operation")
    inputs = fixture.get("inputs")
    if type(operation) is not str or type(inputs) is not dict:
        raise TypeError("golden kernel fixture is malformed")

    if operation == "matmul":
        return reference_matmul(
            np.array(inputs["left"], dtype=np.float64),
            np.array(inputs["right"], dtype=np.float64),
        )
    if operation == "elementwise":
        kernel = fixture.get("kernel")
        if type(kernel) is not str:
            raise TypeError("elementwise golden fixture requires a kernel")
        return reference_elementwise(
            np.array(inputs["value"], dtype=np.float64),
            kernel,
        )
    if operation == "reduction_sum":
        axis = fixture.get("axis")
        if not isinstance(axis, int) or isinstance(axis, bool):
            raise TypeError("reduction golden fixture requires an integer axis")
        return reference_reduction_sum(
            np.array(inputs["value"], dtype=np.float64),
            axis=axis,
        )
    if operation == "softmax":
        axis = fixture.get("axis")
        if not isinstance(axis, int) or isinstance(axis, bool):
            raise TypeError("softmax golden fixture requires an integer axis")
        return reference_softmax(
            np.array(inputs["value"], dtype=np.float64),
            axis=axis,
        )
    raise ValueError(f"unsupported golden kernel operation: {operation!r}")
