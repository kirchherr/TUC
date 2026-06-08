"""Rule-based graph partitioning for the Phase 0 runtime."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import prod
from typing import NamedTuple

from tuc.backends.base import BackendCapability
from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, ComputeOperation, TensorRef
from tuc.runtime.overrides import RuntimeOverrideEffect, RuntimeOverrideSet
from tuc.runtime.plan import LayoutConversionCost, RuntimeTransferEdge, TransferCostProfile


@dataclass(frozen=True)
class Assignment:
    """Assigns one operation to one backend."""

    operation_name: str
    backend_name: str
    reason: str
    memory_domain: MemoryDomainKind
    produced_layout: LayoutKind
    transfer_bytes: int = 0
    layout_conversion_bytes: int = 0


@dataclass(frozen=True)
class PartitionPlan:
    """Ordered operation-to-backend assignment plan."""

    graph_name: str
    assignments: tuple[Assignment, ...]
    transfer_edges: tuple[RuntimeTransferEdge, ...] = ()
    layout_conversions: tuple[LayoutConversionCost, ...] = ()
    override_effects: tuple[RuntimeOverrideEffect, ...] = ()

    def backend_for(self, operation_name: str) -> str:
        for assignment in self.assignments:
            if assignment.operation_name == operation_name:
                return assignment.backend_name
        raise KeyError(operation_name)

    def total_transfer_bytes(self) -> int:
        """Return estimated cross-domain transfer bytes in the plan."""

        return sum(edge.bytes_moved for edge in self.transfer_edges)

    def total_layout_conversion_bytes(self) -> int:
        """Return estimated layout-conversion bytes in the plan."""

        return sum(conversion.bytes_converted for conversion in self.layout_conversions)

    def total_data_movement_bytes(self) -> int:
        """Return total explicit data movement bytes represented in the plan."""

        return self.total_transfer_bytes() + self.total_layout_conversion_bytes()

    def total_estimated_transfer_latency_ns(self) -> float:
        """Return estimated transfer latency across all explicit transfer edges."""

        return sum(
            edge.cost_estimate.estimated_latency_ns
            for edge in self.transfer_edges
            if edge.cost_estimate is not None
        )

    def total_estimated_transfer_energy_pj(self) -> float:
        """Return estimated transfer energy across all explicit transfer edges."""

        return sum(
            edge.cost_estimate.estimated_energy_pj
            for edge in self.transfer_edges
            if edge.cost_estimate is not None
        )


def partition_graph(
    graph: ComputeGraph,
    backends: Iterable[BackendCapability],
    fallback_backend: str = "gpu",
    transfer_cost_profile: TransferCostProfile | None = None,
    runtime_overrides: RuntimeOverrideSet | None = None,
) -> PartitionPlan:
    """Assign operations using backend preference and capability metadata."""

    capabilities = tuple(backends)
    if runtime_overrides is not None:
        runtime_overrides.validate_for_graph(graph, capabilities)

    assignments: list[Assignment] = []
    transfer_edges: list[RuntimeTransferEdge] = []
    layout_conversions: list[LayoutConversionCost] = []
    tensor_locations: dict[str, TensorLocation] = {}
    for operation in graph.operations:
        assignment = _assign_operation(
            operation,
            capabilities,
            fallback_backend,
            tensor_locations,
            transfer_cost_profile,
            runtime_overrides,
        )
        transfers, conversions = _movement_requirements(
            operation=operation,
            assignment=assignment,
            tensor_locations=tensor_locations,
            transfer_cost_profile=transfer_cost_profile,
        )
        if transfers or conversions:
            assignment = _with_movement_costs(assignment, transfers, conversions)
        assignments.append(assignment)
        transfer_edges.extend(transfers)
        layout_conversions.extend(conversions)
        for tensor in operation.outputs:
            tensor_locations[tensor.name] = TensorLocation(
                producer_operation=operation.name,
                backend_name=assignment.backend_name,
                memory_domain=assignment.memory_domain,
                layout=assignment.produced_layout,
            )
    return PartitionPlan(
        graph_name=graph.name,
        assignments=tuple(assignments),
        transfer_edges=tuple(transfer_edges),
        layout_conversions=tuple(layout_conversions),
        override_effects=(
            runtime_overrides.active_effects_for_graph(graph)
            if runtime_overrides is not None
            else ()
        ),
    )


def _assign_operation(
    operation: ComputeOperation,
    capabilities: tuple[BackendCapability, ...],
    fallback_backend: str,
    tensor_locations: dict[str, TensorLocation],
    transfer_cost_profile: TransferCostProfile | None,
    runtime_overrides: RuntimeOverrideSet | None,
) -> Assignment:
    accepted = tuple(capability for capability in capabilities if capability.supports(operation))
    override_effect = (
        runtime_overrides.effect_for_operation(operation.name)
        if runtime_overrides is not None
        else None
    )
    if runtime_overrides is not None:
        accepted = runtime_overrides.apply_to_candidates(
            operation_name=operation.name,
            candidates=accepted,
        )

    if override_effect is not None and override_effect.required_backend is not None:
        return _select_lowest_transfer_candidate(
            operation=operation,
            candidates=accepted,
            tensor_locations=tensor_locations,
            reason_prefix=f"manual_override:require_backend={override_effect.required_backend}",
            transfer_cost_profile=transfer_cost_profile,
        )

    if override_effect is not None and override_effect.preferred_backend is not None:
        return _select_lowest_transfer_candidate(
            operation=operation,
            candidates=accepted,
            tensor_locations=tensor_locations,
            reason_prefix=f"manual_override:prefer_backend={override_effect.preferred_backend}",
            transfer_cost_profile=transfer_cost_profile,
        )

    preferred = tuple(
        capability
        for capability in accepted
        if operation.kind in capability.preferred_for
    )
    if preferred:
        return _select_lowest_transfer_candidate(
            operation=operation,
            candidates=preferred,
            tensor_locations=tensor_locations,
            reason_prefix=f"preferred_for:{operation.kind.value}",
            transfer_cost_profile=transfer_cost_profile,
        )

    if accepted:
        return _select_lowest_transfer_candidate(
            operation=operation,
            candidates=accepted,
            tensor_locations=tensor_locations,
            reason_prefix=f"supported:{operation.kind.value}",
            transfer_cost_profile=transfer_cost_profile,
        )

    transfer_bytes = _transfer_bytes_for_domain(
        operation,
        MemoryDomainKind.GPU_HBM,
        tensor_locations,
    )
    layout_conversion_bytes = _layout_conversion_bytes_for_layout(
        operation,
        _operation_layout(operation),
        tensor_locations,
    )

    return Assignment(
        operation_name=operation.name,
        backend_name=fallback_backend,
        reason=(
            "fallback:"
            f"transfer_bytes={transfer_bytes};"
            f"layout_conversion_bytes={layout_conversion_bytes}"
        ),
        memory_domain=MemoryDomainKind.GPU_HBM,
        produced_layout=_operation_layout(operation),
        transfer_bytes=transfer_bytes,
        layout_conversion_bytes=layout_conversion_bytes,
    )


def _select_lowest_transfer_candidate(
    operation: ComputeOperation,
    candidates: tuple[BackendCapability, ...],
    tensor_locations: dict[str, TensorLocation],
    reason_prefix: str,
    transfer_cost_profile: TransferCostProfile | None,
) -> Assignment:
    scored = tuple(
        (
            _transfer_score_for_domain(
                operation,
                capability.memory_domain,
                tensor_locations,
                transfer_cost_profile,
            ),
            _layout_conversion_bytes_for_layout(
                operation,
                _operation_layout(operation),
                tensor_locations,
            ),
            _transfer_bytes_for_domain(operation, capability.memory_domain, tensor_locations),
            not _domain_match(operation, capability.memory_domain),
            capability.name,
            capability,
        )
        for capability in candidates
    )
    _, layout_conversion_bytes, transfer_bytes, _, _, capability = min(
        scored,
        key=lambda item: item[:5],
    )
    domain_match = _domain_match(operation, capability.memory_domain)
    reason_parts = [
        reason_prefix,
        f"domain={capability.memory_domain.value}",
        f"transfer_bytes={transfer_bytes}",
        f"layout_conversion_bytes={layout_conversion_bytes}",
        f"produced_layout={capability.produced_layout_for(operation).value}",
    ]
    if domain_match:
        reason_parts.append("preferred_memory_domain_match")
    return Assignment(
        operation_name=operation.name,
        backend_name=capability.name,
        reason=";".join(reason_parts),
        memory_domain=capability.memory_domain,
        produced_layout=capability.produced_layout_for(operation),
        transfer_bytes=transfer_bytes,
        layout_conversion_bytes=layout_conversion_bytes,
    )


def _transfer_bytes_for_domain(
    operation: ComputeOperation,
    target_domain: MemoryDomainKind,
    tensor_locations: dict[str, TensorLocation],
) -> int:
    transfer_bytes = 0
    for tensor in operation.inputs:
        location = tensor_locations.get(tensor.name)
        if location is not None and location.memory_domain != target_domain:
            transfer_bytes += _tensor_nbytes(tensor)
    return transfer_bytes


def _transfer_score_for_domain(
    operation: ComputeOperation,
    target_domain: MemoryDomainKind,
    tensor_locations: dict[str, TensorLocation],
    transfer_cost_profile: TransferCostProfile | None,
) -> float:
    score = 0.0
    for tensor in operation.inputs:
        location = tensor_locations.get(tensor.name)
        if location is not None and location.memory_domain != target_domain:
            tensor_bytes = _tensor_nbytes(tensor)
            if transfer_cost_profile is None:
                score += tensor_bytes
            else:
                score += transfer_cost_profile.estimate(
                    bytes_moved=tensor_bytes,
                    source_domain=location.memory_domain,
                    target_domain=target_domain,
                ).estimated_latency_ns
    return score


def _layout_conversion_bytes_for_layout(
    operation: ComputeOperation,
    target_layout: LayoutKind,
    tensor_locations: dict[str, TensorLocation],
) -> int:
    conversion_bytes = 0
    for tensor in operation.inputs:
        source_layout = _source_layout(tensor, tensor_locations)
        if source_layout != target_layout:
            conversion_bytes += _tensor_nbytes(tensor)
    return conversion_bytes


def _movement_requirements(
    operation: ComputeOperation,
    assignment: Assignment,
    tensor_locations: dict[str, TensorLocation],
    transfer_cost_profile: TransferCostProfile | None,
) -> tuple[tuple[RuntimeTransferEdge, ...], tuple[LayoutConversionCost, ...]]:
    transfers: list[RuntimeTransferEdge] = []
    conversions: list[LayoutConversionCost] = []
    target_layout = _operation_layout(operation)

    for tensor in operation.inputs:
        location = tensor_locations.get(tensor.name)
        source_layout = _source_layout(tensor, tensor_locations)
        tensor_bytes = _tensor_nbytes(tensor)

        if location is not None and location.memory_domain != assignment.memory_domain:
            transfers.append(
                RuntimeTransferEdge(
                    tensor_name=tensor.name,
                    source_operation=location.producer_operation,
                    target_operation=operation.name,
                    source_backend=location.backend_name,
                    target_backend=assignment.backend_name,
                    source_domain=location.memory_domain,
                    target_domain=assignment.memory_domain,
                    source_layout=source_layout,
                    target_layout=target_layout,
                    bytes_moved=tensor_bytes,
                    cost_estimate=(
                        transfer_cost_profile.estimate(
                            bytes_moved=tensor_bytes,
                            source_domain=location.memory_domain,
                            target_domain=assignment.memory_domain,
                        )
                        if transfer_cost_profile is not None
                        else None
                    ),
                )
            )

        if source_layout != target_layout:
            conversions.append(
                LayoutConversionCost(
                    tensor_name=tensor.name,
                    source_operation=location.producer_operation if location else None,
                    target_operation=operation.name,
                    source_layout=source_layout,
                    target_layout=target_layout,
                    bytes_converted=tensor_bytes,
                    reason="layout_mismatch",
                )
            )

    return tuple(transfers), tuple(conversions)


def _with_movement_costs(
    assignment: Assignment,
    transfers: tuple[RuntimeTransferEdge, ...],
    conversions: tuple[LayoutConversionCost, ...],
) -> Assignment:
    transfer_bytes = sum(edge.bytes_moved for edge in transfers)
    layout_conversion_bytes = sum(conversion.bytes_converted for conversion in conversions)
    reason = (
        f"{assignment.reason};"
        f"actual_transfer_bytes={transfer_bytes};"
        f"actual_layout_conversion_bytes={layout_conversion_bytes}"
    )
    return Assignment(
        operation_name=assignment.operation_name,
        backend_name=assignment.backend_name,
        reason=reason,
        memory_domain=assignment.memory_domain,
        produced_layout=assignment.produced_layout,
        transfer_bytes=transfer_bytes,
        layout_conversion_bytes=layout_conversion_bytes,
    )


def _tensor_nbytes(tensor: TensorRef) -> int:
    return prod(tensor.shape) * dtype_size_bytes(tensor.dtype)


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


def _source_layout(
    tensor: TensorRef,
    tensor_locations: dict[str, TensorLocation],
) -> LayoutKind:
    location = tensor_locations.get(tensor.name)
    if location is None:
        return LayoutKind.ROW_MAJOR
    return location.layout


def _domain_match(
    operation: ComputeOperation,
    memory_domain: MemoryDomainKind,
) -> bool:
    preferred = operation.attributes.get("tuc.preferred_memory_domain")
    return isinstance(preferred, str) and preferred == memory_domain.value


class TensorLocation(NamedTuple):
    """Tracks where an intermediate tensor currently lives."""

    producer_operation: str
    backend_name: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
