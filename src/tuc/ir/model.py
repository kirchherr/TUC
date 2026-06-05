"""Small hardware-agnostic compute IR model for the Phase 0 prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


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
        if not self.name:
            raise ValueError("tensor name must not be empty")
        if not self.shape:
            raise ValueError("tensor shape must not be empty")
        if any(dimension <= 0 for dimension in self.shape):
            raise ValueError("tensor dimensions must be positive")


@dataclass(frozen=True)
class ComputeOperation:
    """Hardware-agnostic operation node."""

    name: str
    kind: OperationKind
    inputs: tuple[TensorRef, ...]
    outputs: tuple[TensorRef, ...]
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("operation name must not be empty")
        if not self.inputs:
            raise ValueError("operation must have inputs")
        if not self.outputs:
            raise ValueError("operation must have outputs")


@dataclass(frozen=True)
class ComputeGraph:
    """Ordered hardware-agnostic compute graph."""

    name: str
    operations: tuple[ComputeOperation, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("graph name must not be empty")
        if not self.operations:
            raise ValueError("graph must contain at least one operation")

    def operation_names(self) -> tuple[str, ...]:
        return tuple(operation.name for operation in self.operations)

    def with_metadata(self, **metadata: Any) -> ComputeGraph:
        merged = dict(self.metadata)
        merged.update(metadata)
        return ComputeGraph(name=self.name, operations=self.operations, metadata=merged)
