"""Run the CI-facing Runtime Evidence Gate."""

from examples.runtime_output_manifest import build_output_manifest_report
from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeEvidenceMatrixReport,
    RuntimeExecutorConformanceReport,
    RuntimeOutputManifestReport,
    RuntimeTensorStoreEvidenceReport,
    build_current_runtime_evidence_matrix_report,
    run_runtime_executor_conformance,
)


class RuntimeEvidenceGateError(AssertionError):
    """Raised when required runtime evidence is incomplete."""


def build_gate_report(
    *,
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
    conformance_report: RuntimeExecutorConformanceReport | None = None,
    output_manifest_report: RuntimeOutputManifestReport | None = None,
    tensor_store_report: RuntimeTensorStoreEvidenceReport | None = None,
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
    tensor_store = (
        build_tensor_store_evidence_report()
        if tensor_store_report is None
        else tensor_store_report
    )
    output_manifest = (
        build_output_manifest_report()
        if output_manifest_report is None
        else output_manifest_report
    )
    _assert_matrix_complete(matrix)
    _assert_conformance_passed(conformance)
    _assert_tensor_store_evidence_passed(tensor_store)
    _assert_output_manifest_passed(output_manifest)
    return _render_gate_report(matrix, conformance, tensor_store, output_manifest)


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


def _assert_tensor_store_evidence_passed(
    report: RuntimeTensorStoreEvidenceReport,
) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime tensor store evidence failed: {issues}")


def _assert_output_manifest_passed(report: RuntimeOutputManifestReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime output manifest failed: {issues}")


def _render_gate_report(
    matrix: RuntimeEvidenceMatrixReport,
    conformance: RuntimeExecutorConformanceReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    output_manifest: RuntimeOutputManifestReport,
) -> str:
    lines = ["runtime.evidence_gate @runtime_evidence_gate_v0 {"]
    lines.append('  runtime_evidence_matrix = "complete"')
    lines.append(f'  runtime_evidence_graphs = "{len(matrix.graphs)}"')
    lines.append('  runtime_executor_conformance = "passed"')
    lines.append(f'  runtime_executor_conformance_cases = "{len(conformance.checked_cases)}"')
    lines.append('  runtime_tensor_store_evidence = "passed"')
    lines.append(f'  runtime_tensor_store_records = "{len(tensor_store.records)}"')
    lines.append(
        f'  runtime_tensor_store_raw_value_policy = "{tensor_store.raw_value_policy}"'
    )
    lines.append('  runtime_output_manifest = "passed"')
    lines.append(f'  runtime_output_count = "{len(output_manifest.outputs)}"')
    lines.append(
        f'  runtime_output_raw_value_policy = "{output_manifest.raw_value_policy}"'
    )
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
