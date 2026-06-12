"""Emit Runtime Allocation Request Manifest v0."""

from tuc import (
    RuntimeAllocationRequestManifestReport,
    build_runtime_allocation_request_manifest_report,
    dump_runtime_allocation_request_manifest_report,
)

try:
    from examples.runtime_allocation_plan import (
        build_current_runtime_allocation_plan_report,
    )
    from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_plan import build_current_runtime_allocation_plan_report
    from runtime_memory_budget import build_current_runtime_memory_budget_report


def build_current_runtime_allocation_request_manifest_report() -> (
    RuntimeAllocationRequestManifestReport
):
    """Build the current runtime allocation request manifest report."""

    return build_runtime_allocation_request_manifest_report(
        build_current_runtime_allocation_plan_report(),
        build_current_runtime_memory_budget_report(),
    )


def main() -> None:
    print(
        dump_runtime_allocation_request_manifest_report(
            build_current_runtime_allocation_request_manifest_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
