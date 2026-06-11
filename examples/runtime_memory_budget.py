"""Emit Runtime Memory Budget Report v0."""

from tuc import (
    MemoryDomainKind,
    RuntimeMemoryBudgetReport,
    RuntimeMemoryDomainBudget,
    build_runtime_memory_budget_report,
    dump_runtime_memory_budget_report,
)

try:
    from examples.runtime_allocation_plan import (
        build_current_runtime_allocation_plan_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_plan import build_current_runtime_allocation_plan_report


def build_current_runtime_memory_budget_report() -> RuntimeMemoryBudgetReport:
    """Build the current runtime memory budget report."""

    allocation_report = build_current_runtime_allocation_plan_report()
    budgets = (
        RuntimeMemoryDomainBudget(
            budget_id="host_ram_alpha_budget",
            memory_domain=MemoryDomainKind.HOST_RAM,
            max_reserved_bytes=192,
            max_peak_live_bytes=192,
        ),
    )
    return build_runtime_memory_budget_report(allocation_report, budgets)


def main() -> None:
    print(
        dump_runtime_memory_budget_report(
            build_current_runtime_memory_budget_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
