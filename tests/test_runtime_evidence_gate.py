from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.runtime_evidence_gate import (
    SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID,
    RuntimeEvidenceGateError,
    build_gate_report,
)
from examples.runtime_execution_receipt import build_execution_receipt_report
from examples.runtime_input_manifest import build_input_manifest_report
from examples.runtime_output_contract import build_output_contract_report
from examples.runtime_output_manifest import build_output_manifest_report
from examples.runtime_public_output_bundle import build_public_output_bundle
from examples.runtime_reference_correctness import build_reference_correctness_report
from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from examples.source_intent_runtime_returns import (
    run_evidence as run_source_intent_runtime_returns,
)
from tuc import (
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGraph,
    RuntimeExecutionReceiptIssue,
    RuntimeExecutionReceiptReport,
    RuntimeExecutorConformanceCase,
    RuntimeExecutorConformanceIssue,
    RuntimeExecutorConformanceReport,
    RuntimeInputManifestIssue,
    RuntimeInputManifestReport,
    RuntimeOutputContractIssue,
    RuntimeOutputContractReport,
    RuntimeOutputManifestIssue,
    RuntimeOutputManifestReport,
    RuntimeReferenceCorrectnessIssue,
    RuntimeReferenceCorrectnessReport,
    RuntimeTensorStoreEvidenceIssue,
    RuntimeTensorStoreEvidenceReport,
    build_current_runtime_evidence_matrix_report,
    build_runtime_evidence_matrix_report,
)
from tuc.ir import OperationKind

_GOLDEN = Path("tests/golden/proofs/runtime_evidence_gate.txt")


def test_runtime_evidence_gate_matches_golden() -> None:
    assert build_gate_report() == _GOLDEN.read_text(encoding="utf-8")


def test_runtime_evidence_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_evidence_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert 'status = "PASS"' in completed.stdout
    assert 'runtime_evidence_matrix = "complete"' in completed.stdout
    assert 'runtime_executor_conformance = "passed"' in completed.stdout
    assert 'runtime_tensor_store_evidence = "passed"' in completed.stdout
    assert 'runtime_input_manifest = "passed"' in completed.stdout
    assert 'runtime_output_manifest = "passed"' in completed.stdout
    assert 'runtime_output_contract = "passed"' in completed.stdout
    assert 'runtime_public_output_bundle = "passed"' in completed.stdout
    assert 'runtime_reference_correctness = "passed"' in completed.stdout
    assert 'runtime_execution_receipt = "passed"' in completed.stdout
    assert 'source_intent_runtime_returns = "passed"' in completed.stdout


def test_runtime_evidence_gate_rejects_incomplete_matrix() -> None:
    incomplete = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_incomplete",
        (
            RuntimeEvidenceGraph(
                graph_id="incomplete_gate_graph",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    RuntimeEvidenceArtifact(
                        artifact_kind="hac_ir_golden",
                        artifact_id="incomplete_gate_hac_ir",
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="matrix incomplete"):
        build_gate_report(matrix_report=incomplete)


def test_runtime_evidence_gate_rejects_failed_conformance() -> None:
    case = RuntimeExecutorConformanceCase(
        executor_name="reference-cpu",
        operation_kind=OperationKind.MATMUL,
        case_name="reference-cpu_matmul_failed",
        expected_status="supported",
        observed_status="rejected",
        output_shape=(),
        output_dtype="not_executed",
    )
    failed_conformance = RuntimeExecutorConformanceReport(
        checked_cases=(case,),
        issues=(
            RuntimeExecutorConformanceIssue(
                executor_name="reference-cpu",
                case_name="reference-cpu_matmul_failed",
                message="supported_case_did_not_execute",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="conformance failed"):
        build_gate_report(conformance_report=failed_conformance)


def test_runtime_evidence_gate_rejects_failed_tensor_store_evidence() -> None:
    report = build_tensor_store_evidence_report()
    mutable_records = (replace(report.records[0], readonly=False), *report.records[1:])
    failed_tensor_store = RuntimeTensorStoreEvidenceReport(
        graph_name=report.graph_name,
        expected_records=report.expected_records,
        records=mutable_records,
        issues=(
            RuntimeTensorStoreEvidenceIssue(
                tensor_name=report.records[0].tensor_name,
                issue_code="record_value_mutable",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="tensor store evidence failed"):
        build_gate_report(tensor_store_report=failed_tensor_store)


def test_runtime_evidence_gate_rejects_failed_input_manifest() -> None:
    report = build_input_manifest_report()
    mutable_inputs = (replace(report.inputs[0], readonly=False), *report.inputs[1:])
    failed_input_manifest = RuntimeInputManifestReport(
        graph_name=report.graph_name,
        expected_inputs=report.expected_inputs,
        inputs=mutable_inputs,
        issues=(
            RuntimeInputManifestIssue(
                tensor_name=report.inputs[0].tensor_name,
                issue_code="record_value_mutable",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="input manifest failed"):
        build_gate_report(input_manifest_report=failed_input_manifest)


def test_runtime_evidence_gate_rejects_failed_output_manifest() -> None:
    report = build_output_manifest_report()
    mutable_outputs = (replace(report.outputs[0], readonly=False),)
    failed_output_manifest = RuntimeOutputManifestReport(
        graph_name=report.graph_name,
        expected_outputs=report.expected_outputs,
        outputs=mutable_outputs,
        issues=(
            RuntimeOutputManifestIssue(
                tensor_name=report.outputs[0].tensor_name,
                issue_code="record_value_mutable",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="output manifest failed"):
        build_gate_report(output_manifest_report=failed_output_manifest)


def test_runtime_evidence_gate_rejects_failed_output_contract() -> None:
    report = build_output_contract_report()
    failed_output_contract = RuntimeOutputContractReport(
        graph_name=report.graph_name,
        aliases=report.aliases[:-1],
        terminal_tensor_names=report.terminal_tensor_names,
        available_tensor_names=report.available_tensor_names,
        public_outputs=report.public_outputs[:-1],
        output_manifest_passed=report.output_manifest_passed,
        issues=(
            RuntimeOutputContractIssue(
                public_name="unbound",
                tensor_name="row_sum",
                issue_code="terminal_output_unbound",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="output contract failed"):
        build_gate_report(output_contract_report=failed_output_contract)


def test_runtime_evidence_gate_rejects_mismatched_public_output_bundle() -> None:
    bundle = build_public_output_bundle()
    mismatched_bundle = replace(bundle, graph_name="other_graph")

    with pytest.raises(RuntimeEvidenceGateError, match="public output bundle failed"):
        build_gate_report(public_output_bundle=mismatched_bundle)


def test_runtime_evidence_gate_rejects_failed_reference_correctness() -> None:
    report = build_reference_correctness_report()
    bad_comparison = replace(report.comparisons[0], comparison_status="mismatched")
    failed_reference_correctness = RuntimeReferenceCorrectnessReport(
        graph_name=report.graph_name,
        comparisons=(bad_comparison,),
        reference_tensor_names=report.reference_tensor_names,
        issues=(
            RuntimeReferenceCorrectnessIssue(
                tensor_name=bad_comparison.tensor_name,
                issue_code="reference_value_mismatch",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="reference correctness failed"):
        build_gate_report(reference_correctness_report=failed_reference_correctness)


def test_runtime_evidence_gate_rejects_failed_execution_receipt() -> None:
    report = build_execution_receipt_report()
    failed_link = replace(report.evidence_links[0], passed=False)
    failed_receipt = RuntimeExecutionReceiptReport(
        graph_name=report.graph_name,
        evidence_links=(failed_link, *report.evidence_links[1:]),
        operations=report.operations,
        issues=(
            RuntimeExecutionReceiptIssue(
                evidence_kind=failed_link.evidence_kind,
                issue_code="evidence_not_passed",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="execution receipt failed"):
        build_gate_report(execution_receipt_report=failed_receipt)


def test_runtime_evidence_gate_rejects_invalid_source_intent_runtime_returns() -> None:
    with pytest.raises(RuntimeEvidenceGateError, match="source intent runtime returns"):
        build_gate_report(source_intent_runtime_returns_report="not_a_report")  # type: ignore[arg-type]


def test_runtime_evidence_gate_rejects_missing_source_intent_matrix_graph() -> None:
    report = build_current_runtime_evidence_matrix_report()
    without_source_intent_graph = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_missing_source_intent_graph",
        tuple(
            graph
            for graph in report.graphs
            if graph.graph_id != SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID
        ),
    )

    assert without_source_intent_graph.runtime_evidence_matrix_complete
    with pytest.raises(RuntimeEvidenceGateError, match="matrix coverage"):
        build_gate_report(matrix_report=without_source_intent_graph)


def test_runtime_evidence_gate_rejects_missing_source_intent_matrix_artifact() -> None:
    report = build_current_runtime_evidence_matrix_report()
    without_runtime_returns_artifact = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_missing_source_intent_runtime_returns_artifact",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    artifact
                    for artifact in graph.artifacts
                    if artifact.artifact_kind != "source_intent_runtime_returns"
                ),
            )
            if graph.graph_id == SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert without_runtime_returns_artifact.runtime_evidence_matrix_complete
    with pytest.raises(RuntimeEvidenceGateError, match="matrix coverage"):
        build_gate_report(matrix_report=without_runtime_returns_artifact)


def test_runtime_evidence_gate_rejects_unbound_source_intent_return_report() -> None:
    report = run_source_intent_runtime_returns().runtime_returns
    mismatched_report = replace(
        report,
        module_name="other_graph",
        graph_name="other_graph",
    )

    with pytest.raises(RuntimeEvidenceGateError, match="report graph mismatch"):
        build_gate_report(source_intent_runtime_returns_report=mismatched_report)
