"""Run the CI-facing Runtime Evidence Gate."""

from examples.runtime_execution_receipt import build_execution_receipt_report
from examples.runtime_input_manifest import build_input_manifest_report
from examples.runtime_output_contract import build_output_contract_report
from examples.runtime_output_manifest import build_output_manifest_report
from examples.runtime_public_output_bundle import build_public_output_bundle
from examples.runtime_reference_correctness import build_reference_correctness_report
from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from examples.source_intent_runtime_returns import run_evidence as run_runtime_returns
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT,
    RuntimeEvidenceGraph,
    RuntimeEvidenceMatrixReport,
    RuntimeExecutionReceiptReport,
    RuntimeExecutorConformanceReport,
    RuntimeInputManifestReport,
    RuntimeOutputContractReport,
    RuntimeOutputManifestReport,
    RuntimePublicOutputBundle,
    RuntimeReferenceCorrectnessReport,
    RuntimeTensorStoreEvidenceReport,
    SourceIntentRuntimeReturnsReport,
    build_current_runtime_evidence_matrix_report,
    run_runtime_executor_conformance,
)

SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID = "source_intent_return_mlp"
SOURCE_INTENT_RUNTIME_RETURNS_SOURCE_BOUNDARY = "source_intent_metadata"
SOURCE_INTENT_RUNTIME_RETURNS_REQUIRED_MATRIX_ARTIFACTS = (
    "source_intent_return_semantics",
    "source_intent_runtime_returns",
)


class RuntimeEvidenceGateError(AssertionError):
    """Raised when required runtime evidence is incomplete."""


def build_gate_report(
    *,
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
    conformance_report: RuntimeExecutorConformanceReport | None = None,
    execution_receipt_report: RuntimeExecutionReceiptReport | None = None,
    input_manifest_report: RuntimeInputManifestReport | None = None,
    output_contract_report: RuntimeOutputContractReport | None = None,
    output_manifest_report: RuntimeOutputManifestReport | None = None,
    public_output_bundle: RuntimePublicOutputBundle | None = None,
    reference_correctness_report: RuntimeReferenceCorrectnessReport | None = None,
    source_intent_runtime_returns_report: (
        SourceIntentRuntimeReturnsReport | None
    ) = None,
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
    input_manifest = (
        build_input_manifest_report()
        if input_manifest_report is None
        else input_manifest_report
    )
    output_manifest = (
        build_output_manifest_report()
        if output_manifest_report is None
        else output_manifest_report
    )
    output_contract = (
        build_output_contract_report()
        if output_contract_report is None
        else output_contract_report
    )
    public_bundle = (
        build_public_output_bundle()
        if public_output_bundle is None
        else public_output_bundle
    )
    reference_correctness = (
        build_reference_correctness_report()
        if reference_correctness_report is None
        else reference_correctness_report
    )
    execution_receipt = (
        build_execution_receipt_report()
        if execution_receipt_report is None
        else execution_receipt_report
    )
    source_intent_runtime_returns = (
        run_runtime_returns().runtime_returns
        if source_intent_runtime_returns_report is None
        else source_intent_runtime_returns_report
    )
    _assert_matrix_complete(matrix)
    _assert_conformance_passed(conformance)
    _assert_tensor_store_evidence_passed(tensor_store)
    _assert_input_manifest_passed(input_manifest)
    _assert_output_manifest_passed(output_manifest)
    _assert_output_contract_passed(output_contract)
    _assert_public_output_bundle_passed(public_bundle, output_contract)
    _assert_reference_correctness_passed(reference_correctness)
    _assert_execution_receipt_passed(execution_receipt)
    _assert_source_intent_runtime_returns_passed(source_intent_runtime_returns)
    _assert_source_intent_runtime_returns_matrix_covered(
        matrix,
        source_intent_runtime_returns,
    )
    return _render_gate_report(
        matrix,
        conformance,
        tensor_store,
        input_manifest,
        output_manifest,
        output_contract,
        public_bundle,
        reference_correctness,
        execution_receipt,
        source_intent_runtime_returns,
    )


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


def _assert_input_manifest_passed(report: RuntimeInputManifestReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime input manifest failed: {issues}")


def _assert_output_manifest_passed(report: RuntimeOutputManifestReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime output manifest failed: {issues}")


def _assert_output_contract_passed(report: RuntimeOutputContractReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.public_name}:{issue.tensor_name}:{issue.issue_code}"
            for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime output contract failed: {issues}")


def _assert_public_output_bundle_passed(
    bundle: RuntimePublicOutputBundle,
    output_contract: RuntimeOutputContractReport,
) -> None:
    if not isinstance(bundle, RuntimePublicOutputBundle):
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: not a bundle object"
        )
    expected_public_names = tuple(
        output.public_name for output in output_contract.public_outputs
    )
    expected_tensor_names = tuple(
        output.tensor_name for output in output_contract.public_outputs
    )
    if bundle.graph_name != output_contract.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: graph name mismatch"
        )
    if bundle.output_contract != output_contract.output_contract:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: output contract mismatch"
        )
    if bundle.raw_value_policy != output_contract.raw_value_policy:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: raw value policy mismatch"
        )
    if bundle.public_output_names != expected_public_names:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: public output name mismatch"
        )
    if bundle.tensor_names != expected_tensor_names:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: tensor name mismatch"
        )
    if any(not output.readonly for output in bundle.outputs):
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: output value is mutable"
        )


def _assert_reference_correctness_passed(
    report: RuntimeReferenceCorrectnessReport,
) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(
            f"runtime reference correctness failed: {issues}"
        )


def _assert_execution_receipt_passed(report: RuntimeExecutionReceiptReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.evidence_kind}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime execution receipt failed: {issues}")


def _assert_source_intent_runtime_returns_passed(
    report: SourceIntentRuntimeReturnsReport,
) -> None:
    if not isinstance(report, SourceIntentRuntimeReturnsReport):
        raise RuntimeEvidenceGateError(
            "source intent runtime returns failed: not a report object"
        )
    if not report.passed:
        raise RuntimeEvidenceGateError("source intent runtime returns failed")
    if report.runtime_returns_contract != SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns failed: contract mismatch"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "source intent runtime returns failed: raw value policy mismatch"
        )


def _assert_source_intent_runtime_returns_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: SourceIntentRuntimeReturnsReport,
) -> None:
    graph = _find_runtime_evidence_graph(
        matrix,
        SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID,
    )
    if graph is None:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: graph missing"
        )
    if graph.source_boundary != SOURCE_INTENT_RUNTIME_RETURNS_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: "
            "source boundary mismatch"
        )
    if report.module_name != graph.graph_id or report.graph_name != graph.graph_id:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: "
            "report graph mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: "
            "runtime evidence incomplete"
        )
    missing_artifacts = tuple(
        artifact_kind
        for artifact_kind in SOURCE_INTENT_RUNTIME_RETURNS_REQUIRED_MATRIX_ARTIFACTS
        if artifact_kind not in graph.present_artifact_kinds
    )
    if missing_artifacts:
        missing = ",".join(missing_artifacts)
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: "
            f"missing {missing}"
        )


def _find_runtime_evidence_graph(
    matrix: RuntimeEvidenceMatrixReport,
    graph_id: str,
) -> RuntimeEvidenceGraph | None:
    for graph in matrix.graphs:
        if graph.graph_id == graph_id:
            return graph
    return None


def _render_gate_report(
    matrix: RuntimeEvidenceMatrixReport,
    conformance: RuntimeExecutorConformanceReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    reference_correctness: RuntimeReferenceCorrectnessReport,
    execution_receipt: RuntimeExecutionReceiptReport,
    source_intent_runtime_returns: SourceIntentRuntimeReturnsReport,
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
    lines.append('  runtime_input_manifest = "passed"')
    lines.append(f'  runtime_input_count = "{len(input_manifest.inputs)}"')
    lines.append(
        f'  runtime_input_raw_value_policy = "{input_manifest.raw_value_policy}"'
    )
    lines.append('  runtime_output_manifest = "passed"')
    lines.append(f'  runtime_output_count = "{len(output_manifest.outputs)}"')
    lines.append(
        f'  runtime_output_raw_value_policy = "{output_manifest.raw_value_policy}"'
    )
    lines.append('  runtime_output_contract = "passed"')
    lines.append(f'  runtime_public_output_count = "{len(output_contract.public_outputs)}"')
    lines.append(f'  runtime_output_alias_count = "{len(output_contract.aliases)}"')
    lines.append(
        f'  runtime_output_contract_raw_value_policy = "{output_contract.raw_value_policy}"'
    )
    lines.append('  runtime_public_output_bundle = "passed"')
    lines.append(
        f'  runtime_public_output_bundle_outputs = "{len(public_output_bundle.outputs)}"'
    )
    lines.append(
        "  runtime_public_output_bundle_raw_value_policy = "
        f'"{public_output_bundle.raw_value_policy}"'
    )
    lines.append('  runtime_reference_correctness = "passed"')
    lines.append(
        f'  runtime_reference_comparisons = "{len(reference_correctness.comparisons)}"'
    )
    lines.append(
        f'  runtime_reference_raw_value_policy = "{reference_correctness.raw_value_policy}"'
    )
    lines.append('  runtime_execution_receipt = "passed"')
    lines.append(
        f'  runtime_execution_receipt_links = "{len(execution_receipt.evidence_links)}"'
    )
    lines.append(
        f'  runtime_execution_receipt_operations = "{len(execution_receipt.operations)}"'
    )
    lines.append(
        "  runtime_execution_receipt_raw_value_policy = "
        f'"{execution_receipt.raw_value_policy}"'
    )
    lines.append('  source_intent_runtime_returns_matrix = "covered"')
    lines.append('  source_intent_runtime_returns = "passed"')
    lines.append(
        "  source_intent_runtime_return_count = "
        f'"{source_intent_runtime_returns.return_count}"'
    )
    lines.append(
        "  source_intent_runtime_public_output_count = "
        f'"{len(source_intent_runtime_returns.public_output_names)}"'
    )
    lines.append(
        "  source_intent_runtime_returns_raw_value_policy = "
        f'"{source_intent_runtime_returns.raw_value_policy}"'
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
