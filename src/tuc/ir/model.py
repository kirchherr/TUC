"""Small hardware-agnostic compute IR model for the early TUC prototype."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

MAX_GRAPH_OPERATIONS = 4096
MAX_TENSOR_RANK = 8
MAX_TENSOR_DIMENSION = 2**31 - 1
MAX_ATTRIBUTE_KEYS = 128
MAX_ATTRIBUTE_KEY_BYTES = 128
MAX_ATTRIBUTE_DEPTH = 5
MAX_ATTRIBUTE_SEQUENCE_LENGTH = 64
MAX_ATTRIBUTE_STRING_BYTES = 4096
MAX_ATTRIBUTE_TOTAL_BYTES = 64 * 1024

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DTYPE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class OperationKind(StrEnum):
    """Operation classes TUC can reason about in the first prototype."""

    MATMUL = "matmul"
    ELEMENTWISE = "elementwise"
    REDUCTION = "reduction"
    SOFTMAX = "softmax"


@dataclass(frozen=True)
class TensorRef:
    """Symbolic tensor reference used in compute graph operations."""

    name: str
    shape: tuple[int, ...]
    dtype: str = "float32"

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "tensor name")
        if not isinstance(self.dtype, str) or not _DTYPE_RE.fullmatch(self.dtype):
            raise ValueError("tensor dtype must be a simple identifier")

        shape = tuple(self.shape)
        if not shape:
            raise ValueError("tensor shape must not be empty")
        if len(shape) > MAX_TENSOR_RANK:
            raise ValueError("tensor rank exceeds TUC IR limit")
        if any(
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_TENSOR_DIMENSION
            for dimension in shape
        ):
            raise ValueError("tensor dimensions must be positive bounded integers")
        object.__setattr__(self, "shape", shape)


@dataclass(frozen=True)
class ComputeOperation:
    """Hardware-agnostic operation node."""

    name: str
    kind: OperationKind
    inputs: tuple[TensorRef, ...]
    outputs: tuple[TensorRef, ...]
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "operation name")
        _validate_enum(self.kind, OperationKind, "operation kind")
        if not self.inputs:
            raise ValueError("operation must have inputs")
        if not self.outputs:
            raise ValueError("operation must have outputs")
        object.__setattr__(
            self,
            "attributes",
            _freeze_attribute_mapping(self.attributes, "operation attributes"),
        )


@dataclass(frozen=True)
class ComputeGraph:
    """Ordered hardware-agnostic compute graph."""

    name: str
    operations: tuple[ComputeOperation, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "graph name")
        if not self.operations:
            raise ValueError("graph must contain at least one operation")
        if len(self.operations) > MAX_GRAPH_OPERATIONS:
            raise ValueError("graph operation count exceeds TUC IR limit")
        _validate_unique_operation_names(self.operations)
        _validate_consistent_tensor_bindings(self.operations)
        object.__setattr__(
            self,
            "metadata",
            _freeze_attribute_mapping(self.metadata, "graph metadata"),
        )

    def operation_names(self) -> tuple[str, ...]:
        return tuple(operation.name for operation in self.operations)

    def with_metadata(self, **metadata: object) -> ComputeGraph:
        merged = dict(self.metadata)
        merged.update(metadata)
        return ComputeGraph(name=self.name, operations=self.operations, metadata=merged)


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a simple identifier")


def _validate_enum(value: object, enum_type: type[StrEnum], label: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{label} must be {enum_type.__name__}")


def _validate_unique_operation_names(operations: tuple[ComputeOperation, ...]) -> None:
    names = [operation.name for operation in operations]
    if len(names) != len(set(names)):
        raise ValueError("operation names must be unique within a graph")


def _validate_consistent_tensor_bindings(
    operations: tuple[ComputeOperation, ...],
) -> None:
    bindings: dict[str, tuple[tuple[int, ...], str]] = {}
    for operation in operations:
        for tensor in (*operation.inputs, *operation.outputs):
            signature = (tensor.shape, tensor.dtype)
            existing = bindings.get(tensor.name)
            if existing is not None and existing != signature:
                raise ValueError(
                    f"tensor {tensor.name!r} has inconsistent shape or dtype"
                )
            bindings[tensor.name] = signature


def _freeze_attribute_mapping(
    mapping: Mapping[str, object],
    label: str,
) -> Mapping[str, object]:
    if not isinstance(mapping, Mapping):
        raise TypeError(f"{label} must be a mapping")
    budget = _AttributeBudget()
    frozen = _freeze_mapping(mapping, label=label, depth=0, budget=budget)
    if budget.bytes_used > MAX_ATTRIBUTE_TOTAL_BYTES:
        raise ValueError(f"{label} exceeds TUC IR metadata budget")
    return frozen


def _freeze_mapping(
    mapping: Mapping[str, object],
    label: str,
    depth: int,
    budget: _AttributeBudget,
) -> Mapping[str, object]:
    if depth > MAX_ATTRIBUTE_DEPTH:
        raise ValueError(f"{label} nesting exceeds TUC IR limit")
    if len(mapping) > MAX_ATTRIBUTE_KEYS:
        raise ValueError(f"{label} key count exceeds TUC IR limit")

    keys = tuple(mapping.keys())
    if any(not isinstance(key, str) for key in keys):
        raise TypeError(f"{label} keys must be strings")

    frozen: dict[str, object] = {}
    for key in sorted(keys):
        _charge_string(key, f"{label} key", budget, max_bytes=MAX_ATTRIBUTE_KEY_BYTES)
        frozen[key] = _freeze_attribute_value(
            mapping[key],
            label=f"{label}.{key}",
            depth=depth + 1,
            budget=budget,
        )
    return MappingProxyType(frozen)


def _freeze_attribute_value(
    value: object,
    label: str,
    depth: int,
    budget: _AttributeBudget,
) -> object:
    if isinstance(value, bool):
        budget.bytes_used += 1
        return value
    if isinstance(value, int):
        budget.bytes_used += 8
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{label} must be finite")
        budget.bytes_used += 8
        return value
    if isinstance(value, str):
        _charge_string(value, label, budget, max_bytes=MAX_ATTRIBUTE_STRING_BYTES)
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value, label=label, depth=depth, budget=budget)
    if isinstance(value, Sequence) and not isinstance(value, str):
        if depth > MAX_ATTRIBUTE_DEPTH:
            raise ValueError(f"{label} nesting exceeds TUC IR limit")
        if len(value) > MAX_ATTRIBUTE_SEQUENCE_LENGTH:
            raise ValueError(f"{label} sequence length exceeds TUC IR limit")
        return tuple(
            _freeze_attribute_value(
                item,
                label=f"{label}[]",
                depth=depth + 1,
                budget=budget,
            )
            for item in value
        )
    raise TypeError(f"{label} has unsupported IR attribute type")


def _charge_string(
    value: str,
    label: str,
    budget: _AttributeBudget,
    max_bytes: int,
) -> None:
    encoded_size = len(value.encode("utf-8"))
    if encoded_size > max_bytes:
        raise ValueError(f"{label} exceeds TUC IR string limit")
    budget.bytes_used += encoded_size


@dataclass
class _AttributeBudget:
    bytes_used: int = 0
