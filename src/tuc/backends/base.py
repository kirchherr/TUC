"""Backend contracts for TUC prototype backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Protocol

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind


@dataclass(frozen=True)
class BackendCapability:
    """Describes what a backend can accept during early partitioning."""

    name: str
    supported_ops: frozenset[OperationKind]
    supports_noise_model: bool = False
    supports_calibration: bool = False
    preferred_for: frozenset[OperationKind] = field(default_factory=frozenset)
    max_error_budget: float | None = None
    memory_domain: MemoryDomainKind = MemoryDomainKind.GPU_HBM
    supported_layouts: frozenset[LayoutKind] = field(
        default_factory=lambda: frozenset({LayoutKind.ROW_MAJOR})
    )

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("backend capability name must not be empty")
        if not self.supported_ops:
            raise ValueError("backend capability must support at least one operation")
        _validate_operation_set(self.supported_ops, "supported_ops")
        _validate_operation_set(self.preferred_for, "preferred_for")
        if not self.preferred_for.issubset(self.supported_ops):
            raise ValueError("preferred_for must be a subset of supported_ops")
        if self.max_error_budget is not None:
            _validate_non_negative_finite_float(
                self.max_error_budget,
                "max_error_budget",
            )
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("memory_domain must be MemoryDomainKind")
        _validate_layout_set(self.supported_layouts, "supported_layouts")

    def supports(self, operation: ComputeOperation) -> bool:
        if operation.kind not in self.supported_ops:
            return False
        if _operation_layout(operation) not in self.supported_layouts:
            return False
        if self.max_error_budget is None:
            return True
        requested_budget = operation.attributes.get("max_error_budget")
        if requested_budget is None:
            return True
        if not isinstance(requested_budget, int | float) or isinstance(requested_budget, bool):
            raise ValueError("max_error_budget attribute must be a finite non-negative number")
        _validate_non_negative_finite_float(requested_budget, "max_error_budget")
        return requested_budget <= self.max_error_budget


@dataclass(frozen=True)
class LoweringResult:
    """Result produced by a backend lowering pass."""

    backend_name: str
    graph_name: str
    artifact: str
    diagnostics: tuple[str, ...] = ()


class Backend(Protocol):
    """Minimal backend protocol for early TUC experiments."""

    @property
    def capability(self) -> BackendCapability:
        """Return static backend capabilities."""

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        """Lower a compute graph into backend-specific code or configuration."""


def _validate_operation_set(
    operations: frozenset[OperationKind],
    label: str,
) -> None:
    if not isinstance(operations, frozenset):
        raise TypeError(f"{label} must be a frozenset")
    if any(not isinstance(operation, OperationKind) for operation in operations):
        raise TypeError(f"{label} must contain OperationKind values")


def _validate_non_negative_finite_float(value: int | float, label: str) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validate_layout_set(
    layouts: frozenset[LayoutKind],
    label: str,
) -> None:
    if not isinstance(layouts, frozenset):
        raise TypeError(f"{label} must be a frozenset")
    if not layouts:
        raise ValueError(f"{label} must contain at least one layout")
    if any(not isinstance(layout, LayoutKind) for layout in layouts):
        raise TypeError(f"{label} must contain LayoutKind values")


def _operation_layout(operation: ComputeOperation) -> LayoutKind:
    value = operation.attributes.get("tuc.layout")
    if value is None:
        return LayoutKind.ROW_MAJOR
    if isinstance(value, LayoutKind):
        return value
    if isinstance(value, str):
        try:
            return LayoutKind(value)
        except ValueError as exc:
            raise ValueError(f"unsupported operation layout: {value!r}") from exc
    raise TypeError("operation layout must be a LayoutKind or string")
