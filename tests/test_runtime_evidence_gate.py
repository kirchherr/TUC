from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.runtime_evidence_gate import RuntimeEvidenceGateError, build_gate_report
from tuc import (
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGraph,
    RuntimeExecutorConformanceCase,
    RuntimeExecutorConformanceIssue,
    RuntimeExecutorConformanceReport,
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
