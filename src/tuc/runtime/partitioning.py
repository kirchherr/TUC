"""Rule-based graph partitioning for the Phase 0 runtime."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tuc.backends.base import BackendCapability
from tuc.ir.model import ComputeGraph, ComputeOperation


@dataclass(frozen=True)
class Assignment:
    """Assigns one operation to one backend."""

    operation_name: str
    backend_name: str
    reason: str


@dataclass(frozen=True)
class PartitionPlan:
    """Ordered operation-to-backend assignment plan."""

    graph_name: str
    assignments: tuple[Assignment, ...]

    def backend_for(self, operation_name: str) -> str:
        for assignment in self.assignments:
            if assignment.operation_name == operation_name:
                return assignment.backend_name
        raise KeyError(operation_name)


def partition_graph(
    graph: ComputeGraph,
    backends: Iterable[BackendCapability],
    fallback_backend: str = "gpu",
) -> PartitionPlan:
    """Assign operations using backend preference and capability metadata."""

    capabilities = tuple(backends)
    assignments = tuple(
        _assign_operation(operation, capabilities, fallback_backend)
        for operation in graph.operations
    )
    return PartitionPlan(graph_name=graph.name, assignments=assignments)


def _assign_operation(
    operation: ComputeOperation,
    capabilities: tuple[BackendCapability, ...],
    fallback_backend: str,
) -> Assignment:
    preferred = [
        capability
        for capability in capabilities
        if operation.kind in capability.preferred_for and capability.supports(operation)
    ]
    if preferred:
        return Assignment(
            operation_name=operation.name,
            backend_name=preferred[0].name,
            reason=f"preferred_for:{operation.kind.value}",
        )

    supported = [capability for capability in capabilities if capability.supports(operation)]
    if supported:
        return Assignment(
            operation_name=operation.name,
            backend_name=supported[0].name,
            reason=f"supported:{operation.kind.value}",
        )

    return Assignment(
        operation_name=operation.name,
        backend_name=fallback_backend,
        reason="fallback",
    )
