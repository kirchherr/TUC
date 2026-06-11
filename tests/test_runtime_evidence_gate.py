from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.runtime_evidence_gate import RuntimeEvidenceGateError, build_gate_report
from examples.runtime_output_manifest import build_output_manifest_report
from examples.runtime_reference_correctness import build_reference_correctness_report
from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from tuc import (
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGraph,
    RuntimeExecutorConformanceCase,
    RuntimeExecutorConformanceIssue,
    RuntimeExecutorConformanceReport,
    RuntimeOutputManifestIssue,
    RuntimeOutputManifestReport,
    RuntimeReferenceCorrectnessIssue,
    RuntimeReferenceCorrectnessReport,
    RuntimeTensorStoreEvidenceIssue,
    RuntimeTensorStoreEvidenceReport,
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
    assert 'runtime_output_manifest = "passed"' in completed.stdout
    assert 'runtime_reference_correctness = "passed"' in completed.stdout


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
