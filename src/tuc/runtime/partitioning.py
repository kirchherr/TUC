"""Rule-based graph partitioning for the Phase 0 runtime."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import prod

from tuc.backends.base import BackendCapability
from tuc.ir.memory import MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, ComputeOperation, TensorRef


@dataclass(frozen=True)
class Assignment:
    """Assigns one operation to one backend."""

    operation_name: str
    backend_name: str
    reason: str
    memory_domain: MemoryDomainKind
    transfer_bytes: int = 0


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

    def total_transfer_bytes(self) -> int:
        """Return estimated cross-domain transfer bytes in the plan."""

        return sum(assignment.transfer_bytes for assignment in self.assignments)


def partition_graph(
    graph: ComputeGraph,
    backends: Iterable[BackendCapability],
    fallback_backend: str = "gpu",
) -> PartitionPlan:
    """Assign operations using backend preference and capability metadata."""

    capabilities = tuple(backends)
    assignments: list[Assignment] = []
    tensor_domains: dict[str, MemoryDomainKind] = {}
    for operation in graph.operations:
        assignment = _assign_operation(
            operation,
            capabilities,
            fallback_backend,
            tensor_domains,
        )
        assignments.append(assignment)
        for tensor in operation.outputs:
            tensor_domains[tensor.name] = assignment.memory_domain
    return PartitionPlan(graph_name=graph.name, assignments=tuple(assignments))


def _assign_operation(
    operation: ComputeOperation,
    capabilities: tuple[BackendCapability, ...],
    fallback_backend: str,
    tensor_domains: dict[str, MemoryDomainKind],
) -> Assignment:
    preferred = tuple(
        capability
        for capability in capabilities
        if operation.kind in capability.preferred_for and capability.supports(operation)
    )
    if preferred:
        return _select_lowest_transfer_candidate(
            operation=operation,
            candidates=preferred,
            tensor_domains=tensor_domains,
            reason_prefix=f"preferred_for:{operation.kind.value}",
        )

    supported = tuple(capability for capability in capabilities if capability.supports(operation))
    if supported:
        return _select_lowest_transfer_candidate(
            operation=operation,
            candidates=supported,
            tensor_domains=tensor_domains,
            reason_prefix=f"supported:{operation.kind.value}",
        )

    transfer_bytes = _transfer_bytes_for_domain(
        operation,
        MemoryDomainKind.GPU_HBM,
        tensor_domains,
    )

    return Assignment(
        operation_name=operation.name,
        backend_name=fallback_backend,
        reason=f"fallback:transfer_bytes={transfer_bytes}",
        memory_domain=MemoryDomainKind.GPU_HBM,
        transfer_bytes=transfer_bytes,
    )


def _select_lowest_transfer_candidate(
    operation: ComputeOperation,
    candidates: tuple[BackendCapability, ...],
    tensor_domains: dict[str, MemoryDomainKind],
    reason_prefix: str,
) -> Assignment:
    scored = tuple(
        (
            _transfer_bytes_for_domain(
                operation,
                capability.memory_domain,
                tensor_domains,
            ),
            capability,
        )
        for capability in candidates
    )
    transfer_bytes, capability = min(scored, key=lambda item: item[0])
    domain_match = _domain_match(operation, capability.memory_domain)
    reason_parts = [
        reason_prefix,
        f"domain={capability.memory_domain.value}",
        f"transfer_bytes={transfer_bytes}",
    ]
    if domain_match:
        reason_parts.append("preferred_memory_domain_match")
    return Assignment(
        operation_name=operation.name,
        backend_name=capability.name,
        reason=";".join(reason_parts),
        memory_domain=capability.memory_domain,
        transfer_bytes=transfer_bytes,
    )


def _transfer_bytes_for_domain(
    operation: ComputeOperation,
    target_domain: MemoryDomainKind,
    tensor_domains: dict[str, MemoryDomainKind],
) -> int:
    transfer_bytes = 0
    for tensor in operation.inputs:
        source_domain = tensor_domains.get(tensor.name)
        if source_domain is not None and source_domain != target_domain:
            transfer_bytes += _tensor_nbytes(tensor)
    return transfer_bytes


def _tensor_nbytes(tensor: TensorRef) -> int:
    return prod(tensor.shape) * dtype_size_bytes(tensor.dtype)


def _domain_match(
    operation: ComputeOperation,
    memory_domain: MemoryDomainKind,
) -> bool:
    preferred = operation.attributes.get("tuc.preferred_memory_domain")
    return isinstance(preferred, str) and preferred == memory_domain.value
