"""Run the CI-facing Runtime Evidence Gate."""

from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeEvidenceMatrixReport,
    RuntimeExecutorConformanceReport,
    build_current_runtime_evidence_matrix_report,
    run_runtime_executor_conformance,
)


class RuntimeEvidenceGateError(AssertionError):
    """Raised when required runtime evidence is incomplete."""


def build_gate_report(
    *,
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
    conformance_report: RuntimeExecutorConformanceReport | None = None,
) -> str:
    """Return the stable CI-facing runtime evidence gate report."""

    matrix = (
        build_current_runtime_evidence_matrix_report()
        if matrix_report is None
        else matrix_report
    )
    conformance = (
        run_runtime_executor_conformance()
        if conformance_report is None
        else conformance_report
    )
    _assert_matrix_complete(matrix)
    _assert_conformance_passed(conformance)
    return _render_gate_report(matrix, conformance)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_matrix_complete(report: RuntimeEvidenceMatrixReport) -> None:
    if not report.runtime_evidence_matrix_complete:
        issues = ",".join(report.issues)
        raise RuntimeEvidenceGateError(f"runtime evidence matrix incomplete: {issues}")


def _assert_conformance_passed(report: RuntimeExecutorConformanceReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.executor_name}:{issue.case_name}:{issue.message}"
            for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime executor conformance failed: {issues}")


def _render_gate_report(
    matrix: RuntimeEvidenceMatrixReport,
    conformance: RuntimeExecutorConformanceReport,
) -> str:
    lines = ["runtime.evidence_gate @runtime_evidence_gate_v0 {"]
    lines.append('  runtime_evidence_matrix = "complete"')
    lines.append(f'  runtime_evidence_graphs = "{len(matrix.graphs)}"')
    lines.append('  runtime_executor_conformance = "passed"')
    lines.append(f'  runtime_executor_conformance_cases = "{len(conformance.checked_cases)}"')
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
