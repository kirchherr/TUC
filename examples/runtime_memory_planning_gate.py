"""Run the CI-facing Runtime Memory Planning Gate."""

try:
    from examples.runtime_allocation_plan import (
        build_current_runtime_allocation_plan_report,
    )
    from examples.runtime_buffer_lifetime import (
        build_current_runtime_buffer_lifetime_report,
    )
    from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_plan import (  # type: ignore[no-redef]
        build_current_runtime_allocation_plan_report,
    )
    from runtime_buffer_lifetime import (  # type: ignore[no-redef]
        build_current_runtime_buffer_lifetime_report,
    )
    from runtime_memory_budget import (  # type: ignore[no-redef]
        build_current_runtime_memory_budget_report,
    )

from tuc import (
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
    RuntimeAllocationPlanReport,
    RuntimeAllocationRequestManifestReport,
    RuntimeBufferLifetimeReport,
    RuntimeMemoryBudgetReport,
    assert_runtime_allocation_plan,
    assert_runtime_allocation_request_manifest,
    assert_runtime_buffer_lifetime,
    assert_runtime_memory_budget,
    build_runtime_allocation_request_manifest_report,
)


class RuntimeMemoryPlanningGateError(AssertionError):
    """Raised when runtime memory planning evidence is incomplete."""


def build_gate_report(
    *,
    allocation_report: RuntimeAllocationPlanReport | None = None,
    lifetime_report: RuntimeBufferLifetimeReport | None = None,
    memory_budget_report: RuntimeMemoryBudgetReport | None = None,
    request_manifest_report: RuntimeAllocationRequestManifestReport | None = None,
) -> str:
    """Return the stable CI-facing runtime memory planning gate report."""

    lifetime = (
        build_current_runtime_buffer_lifetime_report()
        if lifetime_report is None
        else lifetime_report
    )
    allocation = (
        build_current_runtime_allocation_plan_report()
        if allocation_report is None
        else allocation_report
    )
    memory_budget = (
        build_current_runtime_memory_budget_report()
        if memory_budget_report is None
        else memory_budget_report
    )
    _assert_buffer_lifetime_passed(lifetime)
    _assert_allocation_plan_passed(allocation)
    _assert_memory_budget_passed(memory_budget)
    _assert_allocation_matches_lifetime(lifetime, allocation)
    _assert_memory_budget_matches_allocation(allocation, memory_budget)
    request_manifest = (
        build_runtime_allocation_request_manifest_report(allocation, memory_budget)
        if request_manifest_report is None
        else request_manifest_report
    )
    _assert_allocation_request_manifest_passed(request_manifest)
    _assert_request_manifest_matches_sources(
        allocation,
        memory_budget,
        request_manifest,
    )
    return _render_gate_report(lifetime, allocation, memory_budget, request_manifest)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_allocation_plan_passed(report: RuntimeAllocationPlanReport) -> None:
    try:
        assert_runtime_allocation_plan(report)
    except AssertionError as exc:
        raise RuntimeMemoryPlanningGateError(
            f"runtime allocation plan failed: {exc}"
        ) from exc


def _assert_buffer_lifetime_passed(report: RuntimeBufferLifetimeReport) -> None:
    try:
        assert_runtime_buffer_lifetime(report)
    except AssertionError as exc:
        raise RuntimeMemoryPlanningGateError(
            f"runtime buffer lifetime failed: {exc}"
        ) from exc


def _assert_memory_budget_passed(report: RuntimeMemoryBudgetReport) -> None:
    try:
        assert_runtime_memory_budget(report)
    except AssertionError as exc:
        raise RuntimeMemoryPlanningGateError(
            f"runtime memory budget failed: {exc}"
        ) from exc


def _assert_allocation_request_manifest_passed(
    report: RuntimeAllocationRequestManifestReport,
) -> None:
    try:
        assert_runtime_allocation_request_manifest(report)
    except AssertionError as exc:
        raise RuntimeMemoryPlanningGateError(
            f"runtime allocation request manifest failed: {exc}"
        ) from exc


def _assert_allocation_matches_lifetime(
    lifetime: RuntimeBufferLifetimeReport,
    allocation: RuntimeAllocationPlanReport,
) -> None:
    if lifetime.graph_name != allocation.graph_name:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning lifetime graph mismatch"
        )
    if lifetime.operation_count != allocation.operation_count:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning lifetime operation count mismatch"
        )
    if allocation.source_lifetime_contract != lifetime.lifetime_contract:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning lifetime contract mismatch"
        )
    if (
        allocation.source_lifetime_schema_version
        != RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning lifetime schema mismatch"
        )
    if allocation.source_lifetime_issue_count != len(lifetime.issues):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning lifetime issue count mismatch"
        )
    if allocation.source_lifetime_metadata_digest != lifetime.lifetime_metadata_digest:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning lifetime digest mismatch"
        )


def _assert_memory_budget_matches_allocation(
    allocation: RuntimeAllocationPlanReport,
    memory_budget: RuntimeMemoryBudgetReport,
) -> None:
    if allocation.graph_name != memory_budget.graph_name:
        raise RuntimeMemoryPlanningGateError("runtime memory planning graph mismatch")
    if allocation.operation_count != memory_budget.operation_count:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning operation count mismatch"
        )
    if memory_budget.source_allocation_contract != allocation.allocation_contract:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning allocation contract mismatch"
        )
    if (
        memory_budget.source_allocation_schema_version
        != RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning allocation schema mismatch"
        )
    if memory_budget.source_allocation_issue_count != len(allocation.issues):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning allocation issue count mismatch"
        )
    if (
        memory_budget.source_allocation_metadata_digest
        != allocation.allocation_metadata_digest
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning allocation digest mismatch"
        )


def _assert_request_manifest_matches_sources(
    allocation: RuntimeAllocationPlanReport,
    memory_budget: RuntimeMemoryBudgetReport,
    request_manifest: RuntimeAllocationRequestManifestReport,
) -> None:
    if allocation.graph_name != request_manifest.graph_name:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest graph mismatch"
        )
    if allocation.operation_count != request_manifest.operation_count:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest operation count mismatch"
        )
    if request_manifest.source_allocation_contract != allocation.allocation_contract:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest allocation contract mismatch"
        )
    if (
        request_manifest.source_allocation_schema_version
        != RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest allocation schema mismatch"
        )
    if (
        request_manifest.source_allocation_metadata_digest
        != allocation.allocation_metadata_digest
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest allocation digest mismatch"
        )
    if request_manifest.source_memory_budget_contract != memory_budget.budget_contract:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest budget contract mismatch"
        )
    if (
        request_manifest.source_memory_budget_schema_version
        != RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest budget schema mismatch"
        )
    if (
        request_manifest.source_memory_budget_allocation_digest
        != memory_budget.source_allocation_metadata_digest
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest budget binding mismatch"
        )
    if request_manifest.request_count != allocation.slot_count:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest slot count mismatch"
        )
    if request_manifest.total_reserved_bytes != allocation.total_reserved_bytes:
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest reserved bytes mismatch"
        )
    if tuple(request.slot_id for request in request_manifest.requests) != tuple(
        slot.slot_id for slot in allocation.slots
    ):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest slot binding mismatch"
        )
    if _request_slot_payloads(request_manifest) != _allocation_slot_payloads(allocation):
        raise RuntimeMemoryPlanningGateError(
            "runtime memory planning request manifest slot payload mismatch"
        )


def _request_slot_payloads(
    request_manifest: RuntimeAllocationRequestManifestReport,
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            request.slot_id,
            request.memory_domain,
            request.layout,
            request.dtype,
            request.shape,
            request.bytes_reserved,
            request.tensor_names,
            request.allocation_kind,
        )
        for request in request_manifest.requests
    )


def _allocation_slot_payloads(
    allocation: RuntimeAllocationPlanReport,
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            slot.slot_id,
            slot.memory_domain,
            slot.layout,
            slot.dtype,
            slot.shape,
            slot.bytes_reserved,
            slot.tensor_names,
            slot.allocation_kind,
        )
        for slot in allocation.slots
    )


def _render_gate_report(
    lifetime: RuntimeBufferLifetimeReport,
    allocation: RuntimeAllocationPlanReport,
    memory_budget: RuntimeMemoryBudgetReport,
    request_manifest: RuntimeAllocationRequestManifestReport,
) -> str:
    lines = ["runtime.memory_planning_gate @runtime_memory_planning_gate_v0 {"]
    lines.append('  buffer_lifetime = "passed"')
    lines.append(f'  buffer_lifetimes = "{lifetime.tensor_lifetime_count}"')
    lines.append(f'  buffer_reuse_groups = "{lifetime.reuse_group_count}"')
    lines.append('  allocation_plan = "passed"')
    lines.append('  allocation_lifetime_binding = "verified"')
    lines.append(f'  allocation_bindings = "{allocation.tensor_binding_count}"')
    lines.append(f'  allocation_slots = "{allocation.slot_count}"')
    lines.append(f'  allocation_reuse_slots = "{allocation.reuse_slot_count}"')
    lines.append('  memory_budget = "passed"')
    lines.append('  memory_budget_allocation_binding = "verified"')
    lines.append(f'  memory_budget_count = "{memory_budget.budget_count}"')
    lines.append(f'  memory_usage_count = "{memory_budget.usage_count}"')
    lines.append(f'  total_reserved_bytes = "{memory_budget.total_reserved_bytes}"')
    lines.append(f'  total_peak_live_bytes = "{memory_budget.total_peak_live_bytes}"')
    lines.append('  allocation_request_manifest = "passed"')
    lines.append('  allocation_request_manifest_binding = "verified"')
    lines.append(f'  allocation_requests = "{request_manifest.request_count}"')
    lines.append(
        f'  allocation_request_handle_policy = "{request_manifest.handle_policy}"'
    )
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
