"""Emit Runtime Allocation Reconciliation Report v0."""

try:
    from examples.runtime_allocation_admission import (
        build_current_runtime_allocation_admission_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_admission import (  # type: ignore[no-redef]
        build_current_runtime_allocation_admission_report,
    )

from tuc import (
    RuntimeAllocationReconciliationReport,
    build_runtime_allocation_receipt_report,
    build_runtime_allocation_reconciliation_report,
    dump_runtime_allocation_reconciliation_report,
)


def build_current_runtime_allocation_reconciliation_report() -> (
    RuntimeAllocationReconciliationReport
):
    """Return the current data-only allocation reconciliation report."""

    admission = build_current_runtime_allocation_admission_report()
    receipt = build_runtime_allocation_receipt_report(admission)
    return build_runtime_allocation_reconciliation_report(admission, receipt)


def main() -> None:
    print(
        dump_runtime_allocation_reconciliation_report(
            build_current_runtime_allocation_reconciliation_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
