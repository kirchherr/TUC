"""Emit Runtime Allocation Receipt Report v0."""

try:
    from examples.runtime_allocation_admission import (
        build_current_runtime_allocation_admission_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_allocation_admission import (  # type: ignore[no-redef]
        build_current_runtime_allocation_admission_report,
    )

from tuc import (
    RuntimeAllocationReceiptReport,
    build_runtime_allocation_receipt_report,
    dump_runtime_allocation_receipt_report,
)


def build_current_runtime_allocation_receipt_report() -> (
    RuntimeAllocationReceiptReport
):
    """Return the current data-only allocation receipt report."""

    return build_runtime_allocation_receipt_report(
        build_current_runtime_allocation_admission_report()
    )


def main() -> None:
    print(
        dump_runtime_allocation_receipt_report(
            build_current_runtime_allocation_receipt_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
