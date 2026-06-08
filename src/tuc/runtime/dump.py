"""Stable text dumps for TUC runtime plans."""

from __future__ import annotations

from tuc.runtime.overrides import RuntimeOverrideEffect
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.plan import LayoutConversionCost, RuntimeTransferEdge


def dump_partition_plan(plan: PartitionPlan) -> str:
    """Render a compact, deterministic runtime plan dump."""

    lines = [f"runtime.plan @{plan.graph_name} {{"]
    lines.append("  assignments {")
    for assignment in plan.assignments:
        lines.append(f"    {_format_assignment(assignment)}")
    lines.append("  }")

    if plan.transfer_edges:
        lines.append("  transfers {")
        for edge in plan.transfer_edges:
            lines.append(f"    {_format_transfer(edge)}")
        lines.append("  }")

    if plan.layout_conversions:
        lines.append("  layout_conversions {")
        for conversion in plan.layout_conversions:
            lines.append(f"    {_format_layout_conversion(conversion)}")
        lines.append("  }")

    if plan.override_effects:
        lines.append("  manual_overrides {")
        for effect in plan.override_effects:
            lines.append(f"    {_format_override_effect(effect)}")
        lines.append("  }")

    lines.append("  summary {")
    lines.append(f"    total_transfer_bytes = {plan.total_transfer_bytes()}")
    lines.append(
        f"    total_layout_conversion_bytes = {plan.total_layout_conversion_bytes()}"
    )
    lines.append(f"    total_data_movement_bytes = {plan.total_data_movement_bytes()}")
    lines.append(
        "    estimated_transfer_latency_ns = "
        f"{_format_float(plan.total_estimated_transfer_latency_ns())}"
    )
    lines.append(
        "    estimated_transfer_energy_pj = "
        f"{_format_float(plan.total_estimated_transfer_energy_pj())}"
    )
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def _format_assignment(assignment: Assignment) -> str:
    return (
        f"{assignment.operation_name} -> {assignment.backend_name}"
        f" domain={assignment.memory_domain.value}"
        f" produced_layout={assignment.produced_layout.value}"
        f" transfer_bytes={assignment.transfer_bytes}"
        f" layout_conversion_bytes={assignment.layout_conversion_bytes}"
        f' reason="{assignment.reason}"'
    )


def _format_transfer(edge: RuntimeTransferEdge) -> str:
    cost = edge.cost_estimate
    if cost is None:
        raise ValueError("runtime transfer edge is missing cost estimate")
    return (
        f"%{edge.tensor_name}: {edge.source_operation}/{edge.source_backend}"
        f"/{edge.source_domain.value}/{edge.source_layout.value}"
        f" -> {edge.target_operation}/{edge.target_backend}"
        f"/{edge.target_domain.value}/{edge.target_layout.value}"
        f" bytes={edge.bytes_moved}"
        f" bandwidth_gb_s={_format_float(cost.bandwidth_gb_s)}"
        f" latency_ns={_format_float(cost.estimated_latency_ns)}"
        f" energy_pj={_format_float(cost.estimated_energy_pj)}"
    )


def _format_layout_conversion(conversion: LayoutConversionCost) -> str:
    source = (
        conversion.source_operation
        if conversion.source_operation is not None
        else "graph_input"
    )
    return (
        f"%{conversion.tensor_name}: {source} -> {conversion.target_operation}"
        f" {conversion.source_layout.value}->{conversion.target_layout.value}"
        f" bytes={conversion.bytes_converted}"
        f' reason="{conversion.reason}"'
    )


def _format_override_effect(effect: RuntimeOverrideEffect) -> str:
    return (
        f'{effect.operation_name} '
        f'require_backend="{_format_optional_name(effect.required_backend)}"'
        f' prefer_backend="{_format_optional_name(effect.preferred_backend)}"'
        f' deny_backends="{_format_names(effect.denied_backends)}"'
    )


def _format_optional_name(value: str | None) -> str:
    if value is None:
        return "-"
    return value


def _format_names(names: tuple[str, ...]) -> str:
    if not names:
        return "-"
    return ",".join(names)


def _format_float(value: float) -> str:
    return f"{value:.12g}"


__all__ = ["dump_partition_plan"]
