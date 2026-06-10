"""Emit a deterministic trusted runtime executor conformance report."""

from tuc import (
    RuntimeExecutorConformanceReport,
    dump_runtime_executor_conformance_report,
    run_runtime_executor_conformance,
)


def build_conformance_report() -> RuntimeExecutorConformanceReport:
    """Return the current trusted runtime executor conformance report."""

    return run_runtime_executor_conformance()


def build_report() -> str:
    """Return the stable serialized conformance report."""

    return dump_runtime_executor_conformance_report(build_conformance_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
