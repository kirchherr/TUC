"""Emit Runtime Allocation Plan Report v0."""

from tuc import (
    RuntimeAllocationPlanReport,
    build_runtime_allocation_plan_report,
    dump_runtime_allocation_plan_report,
)

try:
    from examples.runtime_buffer_lifetime import (
        build_current_runtime_buffer_lifetime_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_buffer_lifetime import build_current_runtime_buffer_lifetime_report


def build_current_runtime_allocation_plan_report() -> RuntimeAllocationPlanReport:
    """Build the current runtime allocation plan report."""

    return build_runtime_allocation_plan_report(
        build_current_runtime_buffer_lifetime_report()
    )


def main() -> None:
    print(
        dump_runtime_allocation_plan_report(
            build_current_runtime_allocation_plan_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
