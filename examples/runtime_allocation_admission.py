"""Emit Runtime Allocation Admission Report v0."""

from tuc import (
    RuntimeAllocationAdmissionReport,
    build_runtime_allocation_admission_report,
    dump_runtime_allocation_admission_report,
)

try:
    from examples.runtime_allocation_request_manifest import (
        build_current_runtime_allocation_request_manifest_report,
    )
    from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_request_manifest import (  # type: ignore[no-redef]
        build_current_runtime_allocation_request_manifest_report,
    )
    from runtime_memory_budget import (  # type: ignore[no-redef]
        build_current_runtime_memory_budget_report,
    )


def build_current_runtime_allocation_admission_report() -> (
    RuntimeAllocationAdmissionReport
):
    """Build the current runtime allocation admission report."""

    return build_runtime_allocation_admission_report(
        build_current_runtime_allocation_request_manifest_report(),
        build_current_runtime_memory_budget_report(),
    )


def main() -> None:
    print(
        dump_runtime_allocation_admission_report(
            build_current_runtime_allocation_admission_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
