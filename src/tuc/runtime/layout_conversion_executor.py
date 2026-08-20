"""Trusted in-process materialization for one bounded simulator layout conversion."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc.ir.memory import LayoutKind, dtype_size_bytes
from tuc.ir.model import TensorRef
from tuc.runtime.plan import LayoutConversionCost

RUNTIME_LAYOUT_CONVERTER_CONTRACT = "runtime_layout_converter.trusted_simulator.v0"
RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE = "in_process_fixed_tiled_copy"
RUNTIME_LAYOUT_CONVERTER_NAME = "trusted-blocked-2x2-to-row-major"
RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE = (2, 2)
RUNTIME_LAYOUT_CONVERTER_STATUS = "trusted"
MAX_RUNTIME_LAYOUT_CONVERTER_PHYSICAL_ELEMENTS = 2_000_000
MAX_RUNTIME_LAYOUT_CONVERTER_NAME_BYTES = 256
RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES = (
    "backend_plugin_discovery",
    "device_access",
    "dynamic_import",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "subprocess_execution",
)

FloatArray = NDArray[np.float64]
_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class RuntimeLayoutConverterContract:
    """Pure-data contract for the fixed trusted simulator converter."""

    converter_name: str = RUNTIME_LAYOUT_CONVERTER_NAME
    source_layout: LayoutKind = LayoutKind.BLOCKED
    target_layout: LayoutKind = LayoutKind.ROW_MAJOR
    tile_shape: tuple[int, int] = RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE
    converter_contract: str = RUNTIME_LAYOUT_CONVERTER_CONTRACT
    execution_mode: str = RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES
    )
    external_artifacts: str = "forbidden"
    status: str = RUNTIME_LAYOUT_CONVERTER_STATUS

    def __post_init__(self) -> None:
        _require_name(self.converter_name, "layout converter name")
        if self.source_layout is not LayoutKind.BLOCKED:
            raise ValueError("trusted layout converter source layout must be blocked")
        if self.target_layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("trusted layout converter target layout must be row_major")
        if self.tile_shape != RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE:
            raise ValueError("trusted layout converter tile shape must be 2x2")
        if self.converter_contract != RUNTIME_LAYOUT_CONVERTER_CONTRACT:
            raise ValueError("trusted layout converter contract mismatch")
        if self.execution_mode != RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE:
            raise ValueError("trusted layout converter execution mode mismatch")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("trusted layout converter security boundary changed")
        if self.external_artifacts != "forbidden":
            raise ValueError("trusted layout converter external artifacts must be forbidden")
        if self.status != RUNTIME_LAYOUT_CONVERTER_STATUS:
            raise ValueError("trusted layout converter status must be trusted")


@dataclass(frozen=True)
class RuntimeLayoutConversionExecutionStep:
    """Observable facts for one materialized simulator layout conversion."""

    tensor_name: str
    source_operation: str
    target_operation: str
    source_layout: LayoutKind
    target_layout: LayoutKind
    logical_shape: tuple[int, ...]
    physical_shape: tuple[int, ...]
    tile_shape: tuple[int, int]
    planned_bytes: int
    runtime_logical_bytes: int
    runtime_physical_bytes: int
    logical_element_count: int
    physical_element_count: int
    padding_element_count: int
    temporary_storage_bytes: int
    converter_name: str = RUNTIME_LAYOUT_CONVERTER_NAME
    converter_contract: str = RUNTIME_LAYOUT_CONVERTER_CONTRACT
    semantic_verification: str = "exact_logical_values"
    status: str = "executed_and_verified"

    def __post_init__(self) -> None:
        for name_value, label in (
            (self.tensor_name, "conversion tensor name"),
            (self.source_operation, "conversion source operation"),
            (self.target_operation, "conversion target operation"),
            (self.converter_name, "conversion converter name"),
        ):
            _require_name(name_value, label)
        if self.source_layout is not LayoutKind.BLOCKED:
            raise ValueError("materialized conversion source layout must be blocked")
        if self.target_layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("materialized conversion target layout must be row_major")
        _require_positive_shape(self.logical_shape, 2, "conversion logical shape")
        _require_positive_shape(self.physical_shape, 4, "conversion physical shape")
        if self.tile_shape != RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE:
            raise ValueError("materialized conversion tile shape must be 2x2")
        for integer_value, label in (
            (self.planned_bytes, "conversion planned bytes"),
            (self.runtime_logical_bytes, "conversion runtime logical bytes"),
            (self.runtime_physical_bytes, "conversion runtime physical bytes"),
            (self.logical_element_count, "conversion logical element count"),
            (self.physical_element_count, "conversion physical element count"),
            (self.temporary_storage_bytes, "conversion temporary storage bytes"),
        ):
            if (
                not isinstance(integer_value, int)
                or isinstance(integer_value, bool)
                or integer_value <= 0
            ):
                raise ValueError(f"{label} must be a positive integer")
        if (
            not isinstance(self.padding_element_count, int)
            or isinstance(self.padding_element_count, bool)
            or self.padding_element_count < 0
        ):
            raise ValueError("conversion padding element count must be non-negative")
        if self.physical_element_count > MAX_RUNTIME_LAYOUT_CONVERTER_PHYSICAL_ELEMENTS:
            raise ValueError("materialized conversion physical element limit exceeded")
        if self.physical_element_count != (
            self.logical_element_count + self.padding_element_count
        ):
            raise ValueError("materialized conversion padding accounting mismatch")
        rows, columns = self.logical_shape
        expected_physical_shape = ((rows + 1) // 2, (columns + 1) // 2, 2, 2)
        if self.physical_shape != expected_physical_shape:
            raise ValueError("materialized conversion physical shape mismatch")
        if self.logical_element_count != rows * columns:
            raise ValueError("materialized conversion logical element count mismatch")
        expected_physical_elements = 1
        for dimension in self.physical_shape:
            expected_physical_elements *= dimension
        if self.physical_element_count != expected_physical_elements:
            raise ValueError("materialized conversion physical element count mismatch")
        if self.runtime_logical_bytes != self.logical_element_count * 8:
            raise ValueError("materialized conversion runtime logical bytes mismatch")
        if self.runtime_physical_bytes != self.physical_element_count * 8:
            raise ValueError("materialized conversion runtime physical bytes mismatch")
        if self.temporary_storage_bytes != (
            self.runtime_logical_bytes + self.runtime_physical_bytes
        ):
            raise ValueError("materialized conversion temporary storage mismatch")
        if self.converter_contract != RUNTIME_LAYOUT_CONVERTER_CONTRACT:
            raise ValueError("materialized conversion converter contract mismatch")
        if self.semantic_verification != "exact_logical_values":
            raise ValueError("materialized conversion semantic verification mismatch")
        if self.status != "executed_and_verified":
            raise ValueError("materialized conversion status mismatch")

    def dump_line(self) -> str:
        """Render one deterministic materialized-conversion trace line."""

        return (
            f"{self.tensor_name}"
            f" source_operation={self.source_operation}"
            f" target_operation={self.target_operation}"
            f" source_layout={self.source_layout.value}"
            f" target_layout={self.target_layout.value}"
            f" logical_shape={_format_shape(self.logical_shape)}"
            f" physical_shape={_format_shape(self.physical_shape)}"
            f" tile_shape={_format_shape(self.tile_shape)}"
            f" planned_bytes={self.planned_bytes}"
            f" runtime_logical_bytes={self.runtime_logical_bytes}"
            f" runtime_physical_bytes={self.runtime_physical_bytes}"
            f" logical_elements={self.logical_element_count}"
            f" physical_elements={self.physical_element_count}"
            f" padding_elements={self.padding_element_count}"
            f" temporary_storage_bytes={self.temporary_storage_bytes}"
            f" converter={self.converter_name}"
            f" semantic_verification={self.semantic_verification}"
            f" status={self.status}"
        )


def trusted_runtime_layout_converter_contract() -> RuntimeLayoutConverterContract:
    """Return the fixed execution-free trusted converter contract."""

    return RuntimeLayoutConverterContract()


def assert_materializable_layout_conversion(
    conversion: LayoutConversionCost,
    tensor: TensorRef,
) -> RuntimeLayoutConverterContract:
    """Validate one planned conversion before any runtime value is touched."""

    if not isinstance(conversion, LayoutConversionCost):
        raise TypeError("materialized layout conversion must use LayoutConversionCost")
    if not isinstance(tensor, TensorRef):
        raise TypeError("materialized layout conversion tensor must be TensorRef")
    if conversion.tensor_name != tensor.name:
        raise ValueError("materialized layout conversion tensor mismatch")
    if conversion.source_operation is None:
        raise ValueError("materialized layout conversion requires a source operation")
    contract = trusted_runtime_layout_converter_contract()
    if conversion.source_layout is not contract.source_layout:
        raise ValueError("materialized layout conversion source layout unsupported")
    if conversion.target_layout is not contract.target_layout:
        raise ValueError("materialized layout conversion target layout unsupported")
    if len(tensor.shape) != 2:
        raise ValueError("materialized layout conversion supports rank-2 tensors only")
    logical_elements = 1
    for dimension in tensor.shape:
        logical_elements *= dimension
    expected_planned_bytes = logical_elements * dtype_size_bytes(tensor.dtype)
    if conversion.bytes_converted != expected_planned_bytes:
        raise ValueError("materialized layout conversion planned byte count mismatch")
    return contract


def materialize_layout_conversion(
    conversion: LayoutConversionCost,
    tensor: TensorRef,
    value: FloatArray,
) -> tuple[FloatArray, RuntimeLayoutConversionExecutionStep]:
    """Materialize one blocked-to-row-major conversion through 2x2 tiled storage."""

    contract = assert_materializable_layout_conversion(conversion, tensor)
    source_operation = conversion.source_operation
    if source_operation is None:  # Defensive narrowing after contract validation.
        raise ValueError("materialized layout conversion requires a source operation")
    if not isinstance(value, np.ndarray):
        raise TypeError("materialized layout conversion value must be NumPy array")
    if tuple(value.shape) != tensor.shape:
        raise ValueError("materialized layout conversion value shape mismatch")
    if value.dtype != np.dtype(np.float64):
        raise TypeError("materialized layout conversion value dtype must be float64")
    if not bool(np.all(np.isfinite(value))):
        raise ValueError("materialized layout conversion value must be finite")

    logical_elements = int(value.size)
    rows, columns = tensor.shape
    tile_rows = (rows + 1) // 2
    tile_columns = (columns + 1) // 2
    padded_rows = tile_rows * 2
    padded_columns = tile_columns * 2
    physical_elements = padded_rows * padded_columns
    if physical_elements > MAX_RUNTIME_LAYOUT_CONVERTER_PHYSICAL_ELEMENTS:
        raise ValueError("materialized layout conversion physical element limit exceeded")

    padded = np.zeros((padded_rows, padded_columns), dtype=np.float64)
    padded[:rows, :columns] = value
    blocked = (
        padded.reshape(tile_rows, 2, tile_columns, 2)
        .transpose(0, 2, 1, 3)
        .copy(order="C")
    )
    converted = (
        blocked.transpose(0, 2, 1, 3)
        .reshape(padded_rows, padded_columns)[:rows, :columns]
        .copy(order="C")
    )
    if not bool(np.array_equal(converted, value)):
        raise ValueError("materialized layout conversion changed logical values")
    converted.setflags(write=False)

    step = RuntimeLayoutConversionExecutionStep(
        tensor_name=tensor.name,
        source_operation=source_operation,
        target_operation=conversion.target_operation,
        source_layout=conversion.source_layout,
        target_layout=conversion.target_layout,
        logical_shape=tensor.shape,
        physical_shape=tuple(int(item) for item in blocked.shape),
        tile_shape=contract.tile_shape,
        planned_bytes=conversion.bytes_converted,
        runtime_logical_bytes=int(converted.nbytes),
        runtime_physical_bytes=int(blocked.nbytes),
        logical_element_count=logical_elements,
        physical_element_count=physical_elements,
        padding_element_count=physical_elements - logical_elements,
        temporary_storage_bytes=int(blocked.nbytes + converted.nbytes),
    )
    return converted, step


def _require_name(value: str, label: str) -> None:
    if not isinstance(value, str) or _NAME_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a safe runtime name")
    if len(value.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERTER_NAME_BYTES:
        raise ValueError(f"{label} exceeds runtime name byte limit")


def _require_positive_shape(
    value: tuple[int, ...],
    rank: int,
    label: str,
) -> None:
    if type(value) is not tuple or len(value) != rank:
        raise ValueError(f"{label} must be positive rank-{rank}")
    for dimension in value:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
        ):
            raise ValueError(f"{label} must be positive rank-{rank}")


def _format_shape(shape: tuple[int, ...]) -> str:
    return "x".join(str(item) for item in shape)


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERTER_NAME_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERTER_PHYSICAL_ELEMENTS",
    "RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES",
    "RUNTIME_LAYOUT_CONVERTER_CONTRACT",
    "RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE",
    "RUNTIME_LAYOUT_CONVERTER_NAME",
    "RUNTIME_LAYOUT_CONVERTER_STATUS",
    "RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE",
    "RuntimeLayoutConversionExecutionStep",
    "RuntimeLayoutConverterContract",
    "assert_materializable_layout_conversion",
    "materialize_layout_conversion",
    "trusted_runtime_layout_converter_contract",
]
