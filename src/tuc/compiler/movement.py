"""Data-movement estimates for early TUC compiler passes."""

from __future__ import annotations

from dataclasses import replace
from math import prod
from typing import Any

from tuc.ir.memory import (
    LayoutConstraint,
    LayoutKind,
    MemoryDomainKind,
    MovementEstimate,
    dtype_size_bytes,
)
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef

MOVEMENT_MODEL_VERSION = "movement.v0"
MAX_OPERATION_TENSORS = 16
MAX_TENSOR_RANK = 8
MAX_TENSOR_ELEMENTS = 2**48
MAX_TENSOR_BYTES = 2**63 - 1


def annotate_graph_movement(
    graph: ComputeGraph,
    default_domain: MemoryDomainKind = MemoryDomainKind.HOST_RAM,
) -> ComputeGraph:
    """Attach bounded data-movement estimates to every operation in a graph."""

    annotated_operations = tuple(
        _annotate_operation(operation, default_domain)
        for operation in graph.operations
    )
    annotated = ComputeGraph(
        name=graph.name,
        operations=annotated_operations,
        metadata={
            **graph.metadata,
            "movement_model": MOVEMENT_MODEL_VERSION,
        },
    )
    return annotated.with_metadata(movement_summary=summarize_graph_movement(annotated))


def estimate_operation_movement(
    operation: ComputeOperation,
    preferred_domain: MemoryDomainKind | None = None,
) -> MovementEstimate:
    """Estimate per-operation bytes and arithmetic intensity for MVP kernels."""

    _validate_operation_surface(operation)
    domain = preferred_domain or _preferred_domain(operation)
    if operation.kind is OperationKind.MATMUL:
        return _estimate_matmul(operation, domain)
    if operation.kind is OperationKind.ELEMENTWISE:
        return _estimate_elementwise(operation, domain)
    if operation.kind is OperationKind.REDUCTION:
        return _estimate_reduction(operation, domain)
    if operation.kind is OperationKind.SOFTMAX:
        return _estimate_softmax(operation, domain)
    raise ValueError(f"unsupported operation for movement estimate: {operation.kind.value}")


def summarize_graph_movement(graph: ComputeGraph) -> dict[str, int | float | str]:
    """Summarize movement attributes, failing closed if annotations are missing."""

    total_read = 0
    total_written = 0
    total_ops = 0
    for operation in graph.operations:
        total_read += _require_attribute_int(operation, "tuc.bytes_read")
        total_written += _require_attribute_int(operation, "tuc.bytes_written")
        total_ops += _require_attribute_int(operation, "tuc.arithmetic_ops")

    return {
        "arithmetic_intensity": _arithmetic_intensity(
            arithmetic_ops=total_ops,
            bytes_read=total_read,
            bytes_written=total_written,
        ),
        "movement_model": MOVEMENT_MODEL_VERSION,
        "operation_count": len(graph.operations),
        "total_arithmetic_ops": total_ops,
        "total_bytes_read": total_read,
        "total_bytes_written": total_written,
    }


def _annotate_operation(
    operation: ComputeOperation,
    default_domain: MemoryDomainKind,
) -> ComputeOperation:
    estimate = estimate_operation_movement(
        operation,
        preferred_domain=_preferred_domain(operation, default_domain),
    )
    attributes: dict[str, Any] = {
        **operation.attributes,
        **estimate.as_attributes(),
    }
    return replace(operation, attributes=attributes)


def _estimate_matmul(
    operation: ComputeOperation,
    domain: MemoryDomainKind,
) -> MovementEstimate:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise ValueError("matmul movement estimate expects two inputs and one output")

    left, right = operation.inputs
    output = operation.outputs[0]
    _require_rank(left, 2, operation.name)
    _require_rank(right, 2, operation.name)
    _require_rank(output, 2, operation.name)

    m, k = left.shape
    rhs_k, n = right.shape
    if k != rhs_k:
        raise ValueError("matmul input dimensions must agree")
    if output.shape != (m, n):
        raise ValueError("matmul output shape must match input dimensions")

    bytes_read = _tensor_nbytes(left) + _tensor_nbytes(right)
    bytes_written = _tensor_nbytes(output)
    arithmetic_ops = _checked_product((2, m, n, k), "matmul arithmetic_ops")
    return _movement_estimate(
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        arithmetic_ops=arithmetic_ops,
        preferred_domain=domain,
        notes=("rank2_matmul",),
    )


def _estimate_elementwise(
    operation: ComputeOperation,
    domain: MemoryDomainKind,
) -> MovementEstimate:
    reference_shape = operation.outputs[0].shape
    tensors = (*operation.inputs, *operation.outputs)
    if any(tensor.shape != reference_shape for tensor in tensors):
        raise ValueError("elementwise movement estimate requires exact-shape tensors")

    bytes_read = sum(_tensor_nbytes(tensor) for tensor in operation.inputs)
    bytes_written = sum(_tensor_nbytes(tensor) for tensor in operation.outputs)
    arithmetic_ops = sum(_tensor_elements(tensor) for tensor in operation.outputs)
    return _movement_estimate(
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        arithmetic_ops=arithmetic_ops,
        preferred_domain=domain,
        notes=("exact_shape_elementwise",),
    )


def _estimate_reduction(
    operation: ComputeOperation,
    domain: MemoryDomainKind,
) -> MovementEstimate:
    if len(operation.outputs) != 1:
        raise ValueError("reduction movement estimate expects one output")

    input_elements = sum(_tensor_elements(tensor) for tensor in operation.inputs)
    output_elements = _tensor_elements(operation.outputs[0])
    if output_elements > input_elements:
        raise ValueError("reduction output must not contain more elements than its inputs")

    bytes_read = sum(_tensor_nbytes(tensor) for tensor in operation.inputs)
    bytes_written = _tensor_nbytes(operation.outputs[0])
    arithmetic_ops = max(input_elements - output_elements, 0)
    return _movement_estimate(
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        arithmetic_ops=arithmetic_ops,
        preferred_domain=domain,
        notes=("bounded_reduction",),
    )


def _estimate_softmax(
    operation: ComputeOperation,
    domain: MemoryDomainKind,
) -> MovementEstimate:
    if len(operation.inputs) != 1 or len(operation.outputs) != 1:
        raise ValueError("softmax movement estimate expects one input and one output")
    if operation.inputs[0].shape != operation.outputs[0].shape:
        raise ValueError("softmax input and output shapes must match")
    _require_axis_attribute(
        operation.attributes.get("axis"),
        rank=len(operation.inputs[0].shape),
        operation_name=operation.name,
    )

    elements = _tensor_elements(operation.outputs[0])
    bytes_read = _tensor_nbytes(operation.inputs[0])
    bytes_written = _tensor_nbytes(operation.outputs[0])
    arithmetic_ops = _checked_product((5, elements), "softmax arithmetic_ops")
    return _movement_estimate(
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        arithmetic_ops=arithmetic_ops,
        preferred_domain=domain,
        notes=("softmax_approximate_ops",),
    )


def _movement_estimate(
    bytes_read: int,
    bytes_written: int,
    arithmetic_ops: int,
    preferred_domain: MemoryDomainKind,
    notes: tuple[str, ...],
) -> MovementEstimate:
    return MovementEstimate(
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        arithmetic_ops=arithmetic_ops,
        arithmetic_intensity=_arithmetic_intensity(
            arithmetic_ops=arithmetic_ops,
            bytes_read=bytes_read,
            bytes_written=bytes_written,
        ),
        preferred_domain=preferred_domain,
        layout=LayoutConstraint(LayoutKind.ROW_MAJOR),
        notes=notes,
    )


def _preferred_domain(
    operation: ComputeOperation,
    default_domain: MemoryDomainKind = MemoryDomainKind.HOST_RAM,
) -> MemoryDomainKind:
    prefers_linear_accelerator = (
        operation.attributes.get("prefer_linear_accelerator") is True
    )
    if operation.kind is OperationKind.MATMUL and prefers_linear_accelerator:
        return MemoryDomainKind.ANALOG_WEIGHT_BANK
    return default_domain


def _validate_operation_surface(operation: ComputeOperation) -> None:
    tensor_count = len(operation.inputs) + len(operation.outputs)
    if tensor_count > MAX_OPERATION_TENSORS:
        raise ValueError("operation exceeds movement estimator tensor limit")
    for tensor in (*operation.inputs, *operation.outputs):
        _validate_tensor(tensor)


def _validate_tensor(tensor: TensorRef) -> None:
    if len(tensor.shape) > MAX_TENSOR_RANK:
        raise ValueError("tensor rank exceeds movement estimator limit")
    if any(
        not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0
        for dimension in tensor.shape
    ):
        raise ValueError("tensor dimensions must be positive integers")
    _tensor_elements(tensor)
    dtype_size_bytes(tensor.dtype)


def _require_rank(tensor: TensorRef, rank: int, operation_name: str) -> None:
    if len(tensor.shape) != rank:
        raise ValueError(f"operation {operation_name!r} expects rank-{rank} tensors")


def _tensor_nbytes(tensor: TensorRef) -> int:
    size = _checked_product(
        (_tensor_elements(tensor), dtype_size_bytes(tensor.dtype)),
        f"tensor {tensor.name!r} bytes",
    )
    if size > MAX_TENSOR_BYTES:
        raise ValueError("tensor byte size exceeds movement estimator limit")
    return size


def _tensor_elements(tensor: TensorRef) -> int:
    elements = _checked_product(tensor.shape, f"tensor {tensor.name!r} elements")
    if elements > MAX_TENSOR_ELEMENTS:
        raise ValueError("tensor element count exceeds movement estimator limit")
    return elements


def _checked_product(values: tuple[int, ...], label: str) -> int:
    result = prod(values)
    if result < 0:
        raise ValueError(f"{label} must be non-negative")
    if result > MAX_TENSOR_BYTES:
        raise ValueError(f"{label} exceeds movement estimator limit")
    return result


def _arithmetic_intensity(
    arithmetic_ops: int,
    bytes_read: int,
    bytes_written: int,
) -> float:
    total_bytes = bytes_read + bytes_written
    if total_bytes == 0:
        return 0.0
    return arithmetic_ops / total_bytes


def _require_attribute_int(operation: ComputeOperation, key: str) -> int:
    value = operation.attributes.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"operation {operation.name!r} is missing valid {key}")
    return value


def _require_axis_attribute(value: object, *, rank: int, operation_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"operation {operation_name!r} softmax axis must be an integer")
    normalized = value + rank if value < 0 else value
    if normalized < 0 or normalized >= rank:
        raise ValueError(f"operation {operation_name!r} softmax axis is out of bounds")
    return normalized


__all__ = [
    "MOVEMENT_MODEL_VERSION",
    "annotate_graph_movement",
    "estimate_operation_movement",
    "summarize_graph_movement",
]
