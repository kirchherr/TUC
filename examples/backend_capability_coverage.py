"""Emit the current backend capability coverage matrix."""

from __future__ import annotations

from tuc import (
    BackendCapabilityCoverageReport,
    LinearAlgebraSimulatorBackend,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
    build_backend_capability_coverage_report,
    dump_backend_capability_coverage_report,
)


def build_current_backend_capability_coverage_report() -> BackendCapabilityCoverageReport:
    """Return the current pure-data backend capability coverage report."""

    capabilities = tuple(
        backend.capability
        for backend in (
            LinearAlgebraSimulatorBackend(),
            SystolicArraySimulatorBackend(),
            VectorSimulatorBackend(),
        )
    )
    return build_backend_capability_coverage_report(capabilities)


def main() -> None:
    report = build_current_backend_capability_coverage_report()
    print(dump_backend_capability_coverage_report(report), end="")


if __name__ == "__main__":
    main()
