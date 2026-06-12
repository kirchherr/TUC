"""Run the CI-facing Runtime Memory Planning Gate."""

try:
    from examples.runtime_allocation_plan import (
        build_current_runtime_allocation_plan_report,
    )
    from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_plan import (  # type: ignore[no-redef]
        build_current_runtime_allocation_plan_report,
    )
    from runtime_memory_budget import (  # type: ignore[no-redef]
        build_current_runtime_memory_budget_report,
    )

from tuc import (
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeAllocationPlanReport,
    RuntimeMemoryBudgetReport,
    assert_runtime_allocation_plan,
    assert_runtime_memory_budget,
)


class RuntimeMemoryPlanningGateError(AssertionError):
    """Raised when runtime memory planning evidence is incomplete."""


def build_gate_report(
    *,
    allocation_report: RuntimeAllocationPlanReport | None = None,
    memory_budget_report: RuntimeMemoryBudgetReport | None = None,
) -> str:
    """Return the stable CI-facing runtime memory planning gate report."""

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
    _assert_allocation_plan_passed(allocation)
    _assert_memory_budget_passed(memory_budget)
    _assert_memory_budget_matches_allocation(allocation, memory_budget)
    return _render_gate_report(allocation, memory_budget)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_allocation_plan_passed(report: RuntimeAllocationPlanReport) -> None:
    try:
        assert_runtime_allocation_plan(report)
    except AssertionError as exc:
        raise RuntimeMemoryPlanningGateError(
            f"runtime allocation plan failed: {exc}"
        ) from exc


def _assert_memory_budget_passed(report: RuntimeMemoryBudgetReport) -> None:
    try:
        assert_runtime_memory_budget(report)
    except AssertionError as exc:
        raise RuntimeMemoryPlanningGateError(
            f"runtime memory budget failed: {exc}"
        ) from exc


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


def _render_gate_report(
    allocation: RuntimeAllocationPlanReport,
    memory_budget: RuntimeMemoryBudgetReport,
) -> str:
    lines = ["runtime.memory_planning_gate @runtime_memory_planning_gate_v0 {"]
    lines.append('  allocation_plan = "passed"')
    lines.append(f'  allocation_bindings = "{allocation.tensor_binding_count}"')
    lines.append(f'  allocation_slots = "{allocation.slot_count}"')
    lines.append(f'  allocation_reuse_slots = "{allocation.reuse_slot_count}"')
    lines.append('  memory_budget = "passed"')
    lines.append('  memory_budget_allocation_binding = "verified"')
    lines.append(f'  memory_budget_count = "{memory_budget.budget_count}"')
    lines.append(f'  memory_usage_count = "{memory_budget.usage_count}"')
    lines.append(f'  total_reserved_bytes = "{memory_budget.total_reserved_bytes}"')
    lines.append(f'  total_peak_live_bytes = "{memory_budget.total_peak_live_bytes}"')
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
