"""Small deterministic NumPy reference kernels for the TUC MVP families."""

from __future__ import annotations

from enum import StrEnum
from typing import cast

import numpy as np
from numpy.typing import NDArray

MAX_REFERENCE_ARRAY_ELEMENTS = 1_000_000
MAX_REFERENCE_ARRAY_RANK = 8

FloatArray = NDArray[np.float64]


class ElementwiseKernel(StrEnum):
    """Elementwise reference kernels covered by the golden suite."""

    GELU = "gelu"
    IDENTITY = "identity"
    RELU = "relu"


def reference_matmul(left: object, right: object) -> FloatArray:
    """Return a deterministic 2-D matrix multiplication reference result."""

    left_array = _require_float_array(left, "left")
    right_array = _require_float_array(right, "right")
    if left_array.ndim != 2 or right_array.ndim != 2:
        raise ValueError("reference matmul requires rank-2 arrays")
    if left_array.shape[1] != right_array.shape[0]:
        raise ValueError("reference matmul input dimensions must agree")
    return left_array @ right_array


def reference_elementwise(
    value: object,
    kernel: ElementwiseKernel | str = ElementwiseKernel.IDENTITY,
) -> FloatArray:
    """Return a deterministic elementwise reference result."""

    array = _require_float_array(value, "value")
    kernel_kind = _coerce_elementwise_kernel(kernel)
    if kernel_kind is ElementwiseKernel.IDENTITY:
        return array.copy()
    if kernel_kind is ElementwiseKernel.RELU:
        return cast(FloatArray, np.maximum(array, 0.0))
    if kernel_kind is ElementwiseKernel.GELU:
        scaled = np.sqrt(2.0 / np.pi) * (array + (0.044715 * np.power(array, 3)))
        return cast(FloatArray, 0.5 * array * (1.0 + np.tanh(scaled)))
    raise AssertionError(f"unhandled elementwise kernel: {kernel_kind!r}")


def reference_reduction_sum(value: object, axis: int | None = None) -> FloatArray:
    """Return a deterministic sum-reduction reference result."""

    array = _require_float_array(value, "value")
    if axis is not None:
        _require_axis(axis, array.ndim)
    return cast(FloatArray, np.sum(array, axis=axis, dtype=np.float64))


def reference_softmax(value: object, axis: int = -1) -> FloatArray:
    """Return a numerically stable softmax reference result."""

    array = _require_float_array(value, "value")
    normalized_axis = _require_axis(axis, array.ndim)
    shifted = array - np.max(array, axis=normalized_axis, keepdims=True)
    exp = np.exp(shifted)
    denominator = np.sum(exp, axis=normalized_axis, keepdims=True, dtype=np.float64)
    return cast(FloatArray, exp / denominator)


def _require_float_array(value: object, label: str) -> FloatArray:
    if not isinstance(value, np.ndarray):
        raise TypeError(f"{label} must be a NumPy array")
    if value.ndim == 0:
        raise ValueError(f"{label} must not be scalar")
    if value.ndim > MAX_REFERENCE_ARRAY_RANK:
        raise ValueError(f"{label} rank exceeds reference kernel limit")
    if value.size > MAX_REFERENCE_ARRAY_ELEMENTS:
        raise ValueError(f"{label} element count exceeds reference kernel limit")
    if not (
        np.issubdtype(value.dtype, np.floating)
        or np.issubdtype(value.dtype, np.integer)
    ):
        raise TypeError(f"{label} dtype must be numeric")

    array = value.astype(np.float64, copy=False)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain only finite values")
    return cast(FloatArray, array)


def _coerce_elementwise_kernel(kernel: ElementwiseKernel | str) -> ElementwiseKernel:
    if isinstance(kernel, ElementwiseKernel):
        return kernel
    if isinstance(kernel, str):
        try:
            return ElementwiseKernel(kernel)
        except ValueError as exc:
            raise ValueError(f"unsupported elementwise reference kernel: {kernel!r}") from exc
    raise TypeError("elementwise kernel must be a string or ElementwiseKernel")


def _require_axis(axis: int, rank: int) -> int:
    if not isinstance(axis, int) or isinstance(axis, bool):
        raise TypeError("axis must be an integer")
    if rank == 0:
        raise ValueError("axis requires a non-scalar array")
    normalized = axis + rank if axis < 0 else axis
    if normalized < 0 or normalized >= rank:
        raise ValueError("axis is out of bounds for reference array")
    return normalized


__all__ = [
    "ElementwiseKernel",
    "MAX_REFERENCE_ARRAY_ELEMENTS",
    "MAX_REFERENCE_ARRAY_RANK",
    "reference_elementwise",
    "reference_matmul",
    "reference_reduction_sum",
    "reference_softmax",
]
