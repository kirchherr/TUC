"""Run the CI-facing Runtime Evidence Gate."""

from examples.runtime_backend_equivalence import build_backend_equivalence_report
from examples.runtime_execution_receipt import build_execution_receipt_report
from examples.runtime_input_manifest import build_input_manifest_report
from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from examples.runtime_output_contract import build_output_contract_report
from examples.runtime_output_manifest import build_output_manifest_report
from examples.runtime_public_output_bundle import build_public_output_bundle
from examples.runtime_reference_correctness import build_reference_correctness_report
from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from examples.runtime_vector_backend_equivalence import (
    build_vector_backend_equivalence_report,
)
from examples.source_intent_runtime_returns import run_evidence as run_runtime_returns
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT,
    RuntimeBackendEquivalencePortfolioReport,
    RuntimeBackendEquivalencePortfolioSlice,
    RuntimeBackendEquivalenceReport,
    RuntimeEvidenceGraph,
    RuntimeEvidenceMatrixReport,
    RuntimeExecutionEvidenceBundleReport,
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
    build_runtime_backend_equivalence_portfolio_report,
    build_runtime_execution_evidence_bundle_report,
    run_runtime_executor_conformance,
)

SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID = "source_intent_return_mlp"
SOURCE_INTENT_RUNTIME_RETURNS_SOURCE_BOUNDARY = "source_intent_metadata"
SOURCE_INTENT_RUNTIME_RETURNS_REQUIRED_MATRIX_ARTIFACTS = (
    "source_intent_return_semantics",
    "source_intent_runtime_returns",
)
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY = "runtime_backend_equivalence"
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY = "backend_equivalence"
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS = ("backend_equivalence",)
RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID = "runtime_backend_equivalence"
RUNTIME_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = "reference_cpu"
RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = "systolic_sim"
RUNTIME_BACKEND_EQUIVALENCE_BASELINE_BACKENDS = ("reference-cpu", "reference-cpu")
RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS = ("systolic-sim", "reference-cpu")
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_GRAPH_ID = "runtime_vector_backend_equivalence"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = "reference_cpu"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = "vector_sim"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_BACKENDS = (
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
)
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS = (
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID = "runtime_mixed_backend_equivalence"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = "reference_cpu"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = "mixed_accelerators"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_BACKENDS = (
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS = (
    "systolic-sim",
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID = "runtime_backend_equivalence_portfolio"
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_BACKEND_FAMILIES = (
    "systolic-sim",
    "vector-sim",
)


class RuntimeEvidenceGateError(AssertionError):
    """Raised when required runtime evidence is incomplete."""


def build_gate_report(
    *,
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
    conformance_report: RuntimeExecutorConformanceReport | None = None,
    backend_equivalence_report: RuntimeBackendEquivalenceReport | None = None,
    vector_backend_equivalence_report: (
        RuntimeBackendEquivalenceReport | None
    ) = None,
    mixed_backend_equivalence_report: RuntimeBackendEquivalenceReport | None = None,
    backend_equivalence_portfolio_report: (
        RuntimeBackendEquivalencePortfolioReport | None
    ) = None,
    execution_evidence_bundle_report: (
        RuntimeExecutionEvidenceBundleReport | None
    ) = None,
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
    backend_equivalence = (
        build_backend_equivalence_report()
        if backend_equivalence_report is None
        else backend_equivalence_report
    )
    vector_backend_equivalence = (
        build_vector_backend_equivalence_report()
        if vector_backend_equivalence_report is None
        else vector_backend_equivalence_report
    )
    mixed_backend_equivalence = (
        build_mixed_backend_equivalence_report()
        if mixed_backend_equivalence_report is None
        else mixed_backend_equivalence_report
    )
    backend_equivalence_portfolio = (
        build_runtime_backend_equivalence_portfolio_report(
            RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID,
            (
                backend_equivalence,
                vector_backend_equivalence,
                mixed_backend_equivalence,
            ),
        )
        if backend_equivalence_portfolio_report is None
        else backend_equivalence_portfolio_report
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
    execution_evidence_bundle = (
        build_runtime_execution_evidence_bundle_report(
            tensor_store,
            input_manifest,
            output_manifest,
            reference_correctness,
            execution_receipt,
        )
        if execution_evidence_bundle_report is None
        else execution_evidence_bundle_report
    )
    source_intent_runtime_returns = (
        run_runtime_returns().runtime_returns
        if source_intent_runtime_returns_report is None
        else source_intent_runtime_returns_report
    )
    _assert_matrix_complete(matrix)
    _assert_conformance_passed(conformance)
    _assert_backend_equivalence_passed(
        backend_equivalence,
        graph_id=RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID,
        baseline_run_id=RUNTIME_BACKEND_EQUIVALENCE_BASELINE_RUN_ID,
        candidate_run_id=RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
        baseline_backends=RUNTIME_BACKEND_EQUIVALENCE_BASELINE_BACKENDS,
        candidate_backends=RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS,
        label="runtime backend equivalence",
    )
    _assert_backend_equivalence_matrix_covered(
        matrix,
        backend_equivalence,
        label="runtime backend equivalence",
    )
    _assert_backend_equivalence_passed(
        vector_backend_equivalence,
        graph_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_GRAPH_ID,
        baseline_run_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_RUN_ID,
        candidate_run_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
        baseline_backends=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_BACKENDS,
        candidate_backends=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS,
        label="runtime vector backend equivalence",
    )
    _assert_backend_equivalence_matrix_covered(
        matrix,
        vector_backend_equivalence,
        label="runtime vector backend equivalence",
    )
    _assert_backend_equivalence_passed(
        mixed_backend_equivalence,
        graph_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID,
        baseline_run_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_RUN_ID,
        candidate_run_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
        baseline_backends=RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_BACKENDS,
        candidate_backends=RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS,
        label="runtime mixed backend equivalence",
    )
    _assert_backend_equivalence_matrix_covered(
        matrix,
        mixed_backend_equivalence,
        label="runtime mixed backend equivalence",
    )
    _assert_backend_equivalence_portfolio_passed(
        backend_equivalence_portfolio,
        (
            backend_equivalence,
            vector_backend_equivalence,
            mixed_backend_equivalence,
        ),
    )
    _assert_tensor_store_evidence_passed(tensor_store)
    _assert_input_manifest_passed(input_manifest)
    _assert_output_manifest_passed(output_manifest)
    _assert_output_contract_passed(output_contract)
    _assert_public_output_bundle_passed(public_bundle, output_contract)
    _assert_reference_correctness_passed(reference_correctness)
    _assert_execution_receipt_passed(execution_receipt)
    _assert_execution_receipt_matches_gate_reports(
        execution_receipt,
        tensor_store,
        input_manifest,
        output_manifest,
        reference_correctness,
    )
    _assert_execution_evidence_bundle_passed(execution_evidence_bundle)
    _assert_execution_evidence_bundle_matches_gate_reports(
        execution_evidence_bundle,
        tensor_store,
        input_manifest,
        output_manifest,
        reference_correctness,
        execution_receipt,
    )
    _assert_source_intent_runtime_returns_passed(source_intent_runtime_returns)
    _assert_source_intent_runtime_returns_matrix_covered(
        matrix,
        source_intent_runtime_returns,
    )
    return _render_gate_report(
        matrix,
        conformance,
        backend_equivalence,
        vector_backend_equivalence,
        mixed_backend_equivalence,
        backend_equivalence_portfolio,
        tensor_store,
        input_manifest,
        output_manifest,
        output_contract,
        public_bundle,
        reference_correctness,
        execution_receipt,
        execution_evidence_bundle,
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


def _assert_backend_equivalence_passed(
    report: RuntimeBackendEquivalenceReport,
    *,
    graph_id: str,
    baseline_run_id: str,
    candidate_run_id: str,
    baseline_backends: tuple[str, ...],
    candidate_backends: tuple[str, ...],
    label: str,
) -> None:
    if not isinstance(report, RuntimeBackendEquivalenceReport):
        raise RuntimeEvidenceGateError(
            f"{label} failed: not a report object"
        )
    if report.issues:
        issues = ",".join(
            f"{issue.subject}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"{label} failed: {issues}")
    if report.graph_name != graph_id:
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: graph_name_mismatch"
        )
    if report.baseline_run_id != baseline_run_id:
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: baseline_run_id_mismatch"
        )
    if report.candidate_run_id != candidate_run_id:
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: candidate_run_id_mismatch"
        )
    runs = {run.run_id: run for run in report.runs}
    baseline = runs.get(baseline_run_id)
    candidate = runs.get(candidate_run_id)
    if baseline is None or candidate is None:
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: missing_expected_run"
        )
    if baseline.planned_backend_sequence != baseline_backends:
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: baseline_backends_mismatch"
        )
    if candidate.planned_backend_sequence != candidate_backends:
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: candidate_backends_mismatch"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: raw_value_policy_mismatch"
        )
    if any(
        comparison.comparison_status != "matched"
        for comparison in report.comparisons
    ):
        raise RuntimeEvidenceGateError(
            f"{label} binding failed: comparison_not_matched"
        )


def _assert_backend_equivalence_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeBackendEquivalenceReport,
    *,
    label: str,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(f"{label} matrix coverage failed: graph missing")
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: source_boundary_mismatch"
        )
    if (
        graph.required_artifact_kinds
        != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    ):
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: runtime evidence incomplete"
        )
    missing_artifacts = tuple(
        artifact_kind
        for artifact_kind in RUNTIME_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
        if artifact_kind not in graph.present_artifact_kinds
    )
    if missing_artifacts:
        missing = ",".join(missing_artifacts)
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: missing {missing}"
        )


def _assert_backend_equivalence_portfolio_passed(
    report: RuntimeBackendEquivalencePortfolioReport,
    expected_reports: tuple[RuntimeBackendEquivalenceReport, ...],
) -> None:
    if not isinstance(report, RuntimeBackendEquivalencePortfolioReport):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio failed: not a report object"
        )
    if report.issues:
        issues = ",".join(
            f"{issue.slice_id}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(
            f"runtime backend equivalence portfolio failed: {issues}"
        )
    if report.portfolio_id != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: "
            "portfolio_id_mismatch"
        )
    if report.slice_count != len(expected_reports):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: "
            "slice_count_mismatch"
        )
    if report.candidate_backend_families != (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_BACKEND_FAMILIES
    ):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: "
            "backend_family_mismatch"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: "
            "raw_value_policy_mismatch"
        )
    expected_slice_ids = tuple(
        expected_report.graph_name for expected_report in expected_reports
    )
    actual_slice_ids = tuple(slice_.slice_id for slice_ in report.slices)
    if actual_slice_ids != expected_slice_ids:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: "
            "slice_id_mismatch"
        )
    for slice_, expected_report in zip(
        report.slices,
        expected_reports,
        strict=True,
    ):
        _assert_backend_equivalence_portfolio_slice_bound(slice_, expected_report)


def _assert_backend_equivalence_portfolio_slice_bound(
    slice_: RuntimeBackendEquivalencePortfolioSlice,
    expected_report: RuntimeBackendEquivalenceReport,
) -> None:
    runs = {run.run_id: run for run in expected_report.runs}
    baseline = runs.get(expected_report.baseline_run_id)
    candidate = runs.get(expected_report.candidate_run_id)
    if baseline is None or candidate is None:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: "
            "missing_expected_run"
        )
    expected = {
        "slice_id": expected_report.graph_name,
        "graph_name": expected_report.graph_name,
        "baseline_run_id": expected_report.baseline_run_id,
        "candidate_run_id": expected_report.candidate_run_id,
        "baseline_backend_sequence": baseline.planned_backend_sequence,
        "candidate_backend_sequence": candidate.planned_backend_sequence,
        "comparison_count": len(expected_report.comparisons),
        "comparison_metadata_digest": expected_report.comparison_metadata_digest,
        "passed": expected_report.passed,
        "raw_value_policy": expected_report.raw_value_policy,
    }
    actual = {
        "slice_id": slice_.slice_id,
        "graph_name": slice_.graph_name,
        "baseline_run_id": slice_.baseline_run_id,
        "candidate_run_id": slice_.candidate_run_id,
        "baseline_backend_sequence": slice_.baseline_backend_sequence,
        "candidate_backend_sequence": slice_.candidate_backend_sequence,
        "comparison_count": slice_.comparison_count,
        "comparison_metadata_digest": slice_.comparison_metadata_digest,
        "passed": slice_.passed,
        "raw_value_policy": slice_.raw_value_policy,
    }
    for field_name, expected_value in expected.items():
        if actual[field_name] != expected_value:
            raise RuntimeEvidenceGateError(
                "runtime backend equivalence portfolio binding failed: "
                f"{expected_report.graph_name}:{field_name}_mismatch"
            )


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


def _assert_execution_receipt_matches_gate_reports(
    receipt: RuntimeExecutionReceiptReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    reference_correctness: RuntimeReferenceCorrectnessReport,
) -> None:
    links = {link.evidence_kind: link for link in receipt.evidence_links}
    expected_links = {
        "tensor_store_evidence": {
            "evidence_contract": tensor_store.evidence_contract,
            "graph_name": tensor_store.graph_name,
            "item_count": len(tensor_store.records),
            "metadata_digest": tensor_store.record_metadata_digest,
            "passed": tensor_store.passed,
            "raw_value_policy": tensor_store.raw_value_policy,
        },
        "input_manifest": {
            "evidence_contract": input_manifest.manifest_contract,
            "graph_name": input_manifest.graph_name,
            "item_count": len(input_manifest.inputs),
            "metadata_digest": input_manifest.input_metadata_digest,
            "passed": input_manifest.passed,
            "raw_value_policy": input_manifest.raw_value_policy,
        },
        "output_manifest": {
            "evidence_contract": output_manifest.manifest_contract,
            "graph_name": output_manifest.graph_name,
            "item_count": len(output_manifest.outputs),
            "metadata_digest": output_manifest.output_metadata_digest,
            "passed": output_manifest.passed,
            "raw_value_policy": output_manifest.raw_value_policy,
        },
        "reference_correctness": {
            "evidence_contract": reference_correctness.correctness_contract,
            "graph_name": reference_correctness.graph_name,
            "item_count": len(reference_correctness.comparisons),
            "metadata_digest": reference_correctness.comparison_metadata_digest,
            "passed": reference_correctness.passed,
            "raw_value_policy": reference_correctness.raw_value_policy,
        },
    }

    for evidence_kind, expected in expected_links.items():
        link = links.get(evidence_kind)
        if link is None:
            raise RuntimeEvidenceGateError(
                "runtime execution receipt binding failed: "
                f"{evidence_kind}:missing_link"
            )
        actual = {
            "evidence_contract": link.evidence_contract,
            "graph_name": link.graph_name,
            "item_count": link.item_count,
            "metadata_digest": link.metadata_digest,
            "passed": link.passed,
            "raw_value_policy": link.raw_value_policy,
        }
        for field_name, expected_value in expected.items():
            if actual[field_name] != expected_value:
                raise RuntimeEvidenceGateError(
                    "runtime execution receipt binding failed: "
                    f"{evidence_kind}:{field_name}_mismatch"
                )


def _assert_execution_evidence_bundle_passed(
    report: RuntimeExecutionEvidenceBundleReport,
) -> None:
    if not isinstance(report, RuntimeExecutionEvidenceBundleReport):
        raise RuntimeEvidenceGateError(
            "runtime execution evidence bundle failed: not a report object"
        )
    if report.issues:
        issues = ",".join(
            f"{issue.section}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(
            f"runtime execution evidence bundle failed: {issues}"
        )


def _assert_execution_evidence_bundle_matches_gate_reports(
    bundle: RuntimeExecutionEvidenceBundleReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    reference_correctness: RuntimeReferenceCorrectnessReport,
    execution_receipt: RuntimeExecutionReceiptReport,
) -> None:
    expected = {
        "tensor_store_evidence": {
            "contract": tensor_store.evidence_contract,
            "graph_name": tensor_store.graph_name,
            "item_count": len(tensor_store.records),
            "metadata_digest": tensor_store.record_metadata_digest,
            "passed": tensor_store.passed,
            "raw_value_policy": tensor_store.raw_value_policy,
        },
        "input_manifest": {
            "contract": input_manifest.manifest_contract,
            "graph_name": input_manifest.graph_name,
            "item_count": len(input_manifest.inputs),
            "metadata_digest": input_manifest.input_metadata_digest,
            "passed": input_manifest.passed,
            "raw_value_policy": input_manifest.raw_value_policy,
        },
        "output_manifest": {
            "contract": output_manifest.manifest_contract,
            "graph_name": output_manifest.graph_name,
            "item_count": len(output_manifest.outputs),
            "metadata_digest": output_manifest.output_metadata_digest,
            "passed": output_manifest.passed,
            "raw_value_policy": output_manifest.raw_value_policy,
        },
        "reference_correctness": {
            "contract": reference_correctness.correctness_contract,
            "graph_name": reference_correctness.graph_name,
            "item_count": len(reference_correctness.comparisons),
            "metadata_digest": reference_correctness.comparison_metadata_digest,
            "passed": reference_correctness.passed,
            "raw_value_policy": reference_correctness.raw_value_policy,
        },
        "execution_receipt": {
            "contract": execution_receipt.receipt_contract,
            "graph_name": execution_receipt.graph_name,
            "item_count": len(execution_receipt.evidence_links),
            "metadata_digest": execution_receipt.receipt_metadata_digest,
            "passed": execution_receipt.passed,
            "raw_value_policy": execution_receipt.raw_value_policy,
        },
    }
    actual = {
        "tensor_store_evidence": {
            "contract": bundle.tensor_store_report.evidence_contract,
            "graph_name": bundle.tensor_store_report.graph_name,
            "item_count": len(bundle.tensor_store_report.records),
            "metadata_digest": bundle.tensor_store_report.record_metadata_digest,
            "passed": bundle.tensor_store_report.passed,
            "raw_value_policy": bundle.tensor_store_report.raw_value_policy,
        },
        "input_manifest": {
            "contract": bundle.input_manifest_report.manifest_contract,
            "graph_name": bundle.input_manifest_report.graph_name,
            "item_count": len(bundle.input_manifest_report.inputs),
            "metadata_digest": bundle.input_manifest_report.input_metadata_digest,
            "passed": bundle.input_manifest_report.passed,
            "raw_value_policy": bundle.input_manifest_report.raw_value_policy,
        },
        "output_manifest": {
            "contract": bundle.output_manifest_report.manifest_contract,
            "graph_name": bundle.output_manifest_report.graph_name,
            "item_count": len(bundle.output_manifest_report.outputs),
            "metadata_digest": bundle.output_manifest_report.output_metadata_digest,
            "passed": bundle.output_manifest_report.passed,
            "raw_value_policy": bundle.output_manifest_report.raw_value_policy,
        },
        "reference_correctness": {
            "contract": bundle.reference_correctness_report.correctness_contract,
            "graph_name": bundle.reference_correctness_report.graph_name,
            "item_count": len(bundle.reference_correctness_report.comparisons),
            "metadata_digest": (
                bundle.reference_correctness_report.comparison_metadata_digest
            ),
            "passed": bundle.reference_correctness_report.passed,
            "raw_value_policy": bundle.reference_correctness_report.raw_value_policy,
        },
        "execution_receipt": {
            "contract": bundle.execution_receipt_report.receipt_contract,
            "graph_name": bundle.execution_receipt_report.graph_name,
            "item_count": len(bundle.execution_receipt_report.evidence_links),
            "metadata_digest": (
                bundle.execution_receipt_report.receipt_metadata_digest
            ),
            "passed": bundle.execution_receipt_report.passed,
            "raw_value_policy": bundle.execution_receipt_report.raw_value_policy,
        },
    }

    for section, expected_fields in expected.items():
        actual_fields = actual[section]
        for field_name, expected_value in expected_fields.items():
            if actual_fields[field_name] != expected_value:
                raise RuntimeEvidenceGateError(
                    "runtime execution evidence bundle binding failed: "
                    f"{section}:{field_name}_mismatch"
                )


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
    backend_equivalence: RuntimeBackendEquivalenceReport,
    vector_backend_equivalence: RuntimeBackendEquivalenceReport,
    mixed_backend_equivalence: RuntimeBackendEquivalenceReport,
    backend_equivalence_portfolio: RuntimeBackendEquivalencePortfolioReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    reference_correctness: RuntimeReferenceCorrectnessReport,
    execution_receipt: RuntimeExecutionReceiptReport,
    execution_evidence_bundle: RuntimeExecutionEvidenceBundleReport,
    source_intent_runtime_returns: SourceIntentRuntimeReturnsReport,
) -> str:
    lines = ["runtime.evidence_gate @runtime_evidence_gate_v0 {"]
    lines.append('  runtime_evidence_matrix = "complete"')
    lines.append(f'  runtime_evidence_graphs = "{len(matrix.graphs)}"')
    lines.append('  runtime_executor_conformance = "passed"')
    lines.append(f'  runtime_executor_conformance_cases = "{len(conformance.checked_cases)}"')
    lines.append('  runtime_backend_equivalence = "passed"')
    lines.append('  runtime_backend_equivalence_binding = "verified"')
    lines.append('  runtime_backend_equivalence_matrix = "covered"')
    lines.append(f'  runtime_backend_equivalence_runs = "{len(backend_equivalence.runs)}"')
    lines.append(
        "  runtime_backend_equivalence_comparisons = "
        f'"{len(backend_equivalence.comparisons)}"'
    )
    lines.append(
        "  runtime_backend_equivalence_raw_value_policy = "
        f'"{backend_equivalence.raw_value_policy}"'
    )
    lines.append('  runtime_vector_backend_equivalence = "passed"')
    lines.append('  runtime_vector_backend_equivalence_binding = "verified"')
    lines.append('  runtime_vector_backend_equivalence_matrix = "covered"')
    lines.append(
        "  runtime_vector_backend_equivalence_runs = "
        f'"{len(vector_backend_equivalence.runs)}"'
    )
    lines.append(
        "  runtime_vector_backend_equivalence_comparisons = "
        f'"{len(vector_backend_equivalence.comparisons)}"'
    )
    lines.append(
        "  runtime_vector_backend_equivalence_raw_value_policy = "
        f'"{vector_backend_equivalence.raw_value_policy}"'
    )
    lines.append('  runtime_mixed_backend_equivalence = "passed"')
    lines.append('  runtime_mixed_backend_equivalence_binding = "verified"')
    lines.append('  runtime_mixed_backend_equivalence_matrix = "covered"')
    lines.append(
        "  runtime_mixed_backend_equivalence_runs = "
        f'"{len(mixed_backend_equivalence.runs)}"'
    )
    lines.append(
        "  runtime_mixed_backend_equivalence_comparisons = "
        f'"{len(mixed_backend_equivalence.comparisons)}"'
    )
    lines.append(
        "  runtime_mixed_backend_equivalence_raw_value_policy = "
        f'"{mixed_backend_equivalence.raw_value_policy}"'
    )
    lines.append('  runtime_backend_equivalence_portfolio = "passed"')
    lines.append('  runtime_backend_equivalence_portfolio_binding = "verified"')
    lines.append(
        "  runtime_backend_equivalence_portfolio_slices = "
        f'"{backend_equivalence_portfolio.slice_count}"'
    )
    lines.append(
        "  runtime_backend_equivalence_portfolio_backend_families = "
        f'"{",".join(backend_equivalence_portfolio.candidate_backend_families)}"'
    )
    lines.append(
        "  runtime_backend_equivalence_portfolio_raw_value_policy = "
        f'"{backend_equivalence_portfolio.raw_value_policy}"'
    )
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
    lines.append('  runtime_execution_receipt_binding = "verified"')
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
    lines.append('  runtime_execution_evidence_bundle = "passed"')
    lines.append('  runtime_execution_evidence_bundle_binding = "verified"')
    lines.append(
        "  runtime_execution_evidence_bundle_sections = "
        f'"{len(execution_evidence_bundle.report_sections)}"'
    )
    lines.append(
        "  runtime_execution_evidence_bundle_raw_value_policy = "
        f'"{execution_evidence_bundle.raw_value_policy}"'
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
