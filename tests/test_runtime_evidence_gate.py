from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.runtime_backend_equivalence import build_backend_equivalence_report
from examples.runtime_evidence_gate import (
    RUNTIME_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_ARTIFACT_IDS,
    RUNTIME_HS_IR_PLAN_ALIGNMENT_MATRIX_ARTIFACT_ID,
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID,
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS,
    RUNTIME_VECTOR_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
    SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID,
    RuntimeEvidenceGateError,
    build_gate_report,
)
from examples.runtime_execution_receipt import build_execution_receipt_report
from examples.runtime_hs_ir_plan_alignment import build_alignment_report
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
from examples.source_intent_runtime_returns import (
    run_evidence as run_source_intent_runtime_returns,
)
from tuc import (
    RuntimeBackendEquivalenceIssue,
    RuntimeBackendEquivalencePortfolioPolicyReport,
    RuntimeBackendEquivalencePortfolioReport,
    RuntimeBackendEquivalencePortfolioRequirement,
    RuntimeBackendEquivalenceReport,
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGraph,
    RuntimeExecutionEvidenceBundleIssue,
    RuntimeExecutionEvidenceBundleReport,
    RuntimeExecutionReceiptIssue,
    RuntimeExecutionReceiptReport,
    RuntimeExecutorConformanceCase,
    RuntimeExecutorConformanceIssue,
    RuntimeExecutorConformanceReport,
    RuntimeHsIrPlanAlignmentIssue,
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
    build_default_runtime_backend_equivalence_portfolio_policy_report,
    build_runtime_backend_equivalence_portfolio_report,
    build_runtime_evidence_matrix_report,
    build_runtime_execution_evidence_bundle_report,
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
    assert 'runtime_evidence_gate_matrix_coverage = "passed"' in completed.stdout
    assert 'runtime_evidence_gate_matrix_bindings = "4"' in completed.stdout
    assert 'runtime_backend_equivalence = "passed"' in completed.stdout
    assert 'runtime_backend_equivalence_binding = "verified"' in completed.stdout
    assert 'runtime_backend_equivalence_matrix = "covered"' in completed.stdout
    assert (
        "runtime_backend_equivalence_matrix_artifact = "
        f'"{RUNTIME_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID}"'
    ) in completed.stdout
    assert 'runtime_vector_backend_equivalence = "passed"' in completed.stdout
    assert (
        'runtime_vector_backend_equivalence_binding = "verified"'
        in completed.stdout
    )
    assert (
        'runtime_vector_backend_equivalence_matrix = "covered"'
        in completed.stdout
    )
    assert (
        "runtime_vector_backend_equivalence_matrix_artifact = "
        f'"{RUNTIME_VECTOR_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID}"'
    ) in completed.stdout
    assert 'runtime_mixed_backend_equivalence = "passed"' in completed.stdout
    assert 'runtime_mixed_backend_equivalence_binding = "verified"' in completed.stdout
    assert (
        'runtime_mixed_backend_equivalence_matrix = "covered"'
        in completed.stdout
    )
    assert (
        "runtime_mixed_backend_equivalence_matrix_artifact = "
        f'"{RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID}"'
    ) in completed.stdout
    assert 'runtime_hs_ir_plan_alignment = "passed"' in completed.stdout
    assert 'runtime_hs_ir_plan_alignment_binding = "verified"' in completed.stdout
    assert 'runtime_hs_ir_plan_alignment_matrix = "covered"' in completed.stdout
    assert (
        "runtime_hs_ir_plan_alignment_matrix_artifact = "
        f'"{RUNTIME_HS_IR_PLAN_ALIGNMENT_MATRIX_ARTIFACT_ID}"'
    ) in completed.stdout
    assert 'runtime_hs_ir_plan_alignment_steps = "4"' in completed.stdout
    assert (
        'runtime_hs_ir_plan_alignment_backend_sequence = '
        '"systolic-sim,vector-sim,vector-sim,vector-sim"'
    ) in completed.stdout
    assert 'runtime_backend_equivalence_portfolio = "passed"' in completed.stdout
    assert (
        'runtime_backend_equivalence_portfolio_binding = "verified"'
        in completed.stdout
    )
    assert (
        'runtime_backend_equivalence_portfolio_backend_families = '
        '"systolic-sim,vector-sim"'
    ) in completed.stdout
    assert (
        'runtime_backend_equivalence_portfolio_matrix = "covered"'
        in completed.stdout
    )
    assert (
        "runtime_backend_equivalence_portfolio_matrix_artifacts = "
        f'"{",".join(RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_ARTIFACT_IDS)}"'
    ) in completed.stdout
    assert (
        'runtime_backend_equivalence_portfolio_policy = "accepted"'
        in completed.stdout
    )
    assert (
        'runtime_backend_equivalence_portfolio_policy_binding = "verified"'
        in completed.stdout
    )
    assert 'runtime_tensor_store_evidence = "passed"' in completed.stdout
    assert 'runtime_input_manifest = "passed"' in completed.stdout
    assert 'runtime_output_manifest = "passed"' in completed.stdout
    assert 'runtime_output_contract = "passed"' in completed.stdout
    assert 'runtime_public_output_bundle = "passed"' in completed.stdout
    assert 'runtime_reference_correctness = "passed"' in completed.stdout
    assert 'runtime_execution_receipt = "passed"' in completed.stdout
    assert 'runtime_execution_receipt_binding = "verified"' in completed.stdout
    assert 'runtime_execution_evidence_bundle = "passed"' in completed.stdout
    assert 'runtime_execution_evidence_bundle_binding = "verified"' in completed.stdout
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


def test_runtime_evidence_gate_rejects_failed_backend_equivalence() -> None:
    report = build_backend_equivalence_report()
    candidate = replace(
        report.runs[1],
        planned_backend_sequence=report.runs[0].planned_backend_sequence,
    )
    failed_equivalence = RuntimeBackendEquivalenceReport(
        graph_name=report.graph_name,
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(report.runs[0], candidate),
        comparisons=report.comparisons,
        issues=(
            RuntimeBackendEquivalenceIssue(
                subject="backend_sequence",
                issue_code="backend_sequences_not_distinct",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="backend equivalence failed"):
        build_gate_report(backend_equivalence_report=failed_equivalence)


def test_runtime_evidence_gate_rejects_unbound_backend_equivalence() -> None:
    report = build_backend_equivalence_report()
    mismatched_report = RuntimeBackendEquivalenceReport(
        graph_name="other_backend_equivalence",
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(
            replace(report.runs[0], graph_name="other_backend_equivalence"),
            replace(report.runs[1], graph_name="other_backend_equivalence"),
        ),
        comparisons=report.comparisons,
        issues=(),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="backend equivalence binding"):
        build_gate_report(backend_equivalence_report=mismatched_report)


def test_runtime_evidence_gate_rejects_failed_vector_backend_equivalence() -> None:
    report = build_vector_backend_equivalence_report()
    candidate = replace(
        report.runs[1],
        planned_backend_sequence=report.runs[0].planned_backend_sequence,
    )
    failed_equivalence = RuntimeBackendEquivalenceReport(
        graph_name=report.graph_name,
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(report.runs[0], candidate),
        comparisons=report.comparisons,
        issues=(
            RuntimeBackendEquivalenceIssue(
                subject="backend_sequence",
                issue_code="backend_sequences_not_distinct",
            ),
        ),
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="vector backend equivalence failed",
    ):
        build_gate_report(vector_backend_equivalence_report=failed_equivalence)


def test_runtime_evidence_gate_rejects_unbound_vector_backend_equivalence() -> None:
    report = build_vector_backend_equivalence_report()
    mismatched_report = RuntimeBackendEquivalenceReport(
        graph_name="other_vector_backend_equivalence",
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(
            replace(report.runs[0], graph_name="other_vector_backend_equivalence"),
            replace(report.runs[1], graph_name="other_vector_backend_equivalence"),
        ),
        comparisons=report.comparisons,
        issues=(),
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="vector backend equivalence binding",
    ):
        build_gate_report(vector_backend_equivalence_report=mismatched_report)


def test_runtime_evidence_gate_rejects_failed_mixed_backend_equivalence() -> None:
    report = build_mixed_backend_equivalence_report()
    candidate = replace(
        report.runs[1],
        planned_backend_sequence=report.runs[0].planned_backend_sequence,
    )
    failed_equivalence = RuntimeBackendEquivalenceReport(
        graph_name=report.graph_name,
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(report.runs[0], candidate),
        comparisons=report.comparisons,
        issues=(
            RuntimeBackendEquivalenceIssue(
                subject="backend_sequence",
                issue_code="backend_sequences_not_distinct",
            ),
        ),
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="mixed backend equivalence failed",
    ):
        build_gate_report(mixed_backend_equivalence_report=failed_equivalence)


def test_runtime_evidence_gate_rejects_unbound_mixed_backend_equivalence() -> None:
    report = build_mixed_backend_equivalence_report()
    mismatched_report = RuntimeBackendEquivalenceReport(
        graph_name="other_mixed_backend_equivalence",
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(
            replace(report.runs[0], graph_name="other_mixed_backend_equivalence"),
            replace(report.runs[1], graph_name="other_mixed_backend_equivalence"),
        ),
        comparisons=report.comparisons,
        issues=(),
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="mixed backend equivalence binding",
    ):
        build_gate_report(mixed_backend_equivalence_report=mismatched_report)


def test_runtime_evidence_gate_rejects_failed_hs_ir_plan_alignment() -> None:
    report = build_alignment_report()
    failed_alignment = replace(
        report,
        partition_backend_sequence=("reference-cpu", *report.partition_backend_sequence[1:]),
        issues=(
            RuntimeHsIrPlanAlignmentIssue(
                subject="backend_sequence",
                issue_code="hs_ir_partition_backend_mismatch",
            ),
            RuntimeHsIrPlanAlignmentIssue(
                subject="backend_sequence",
                issue_code="partition_trace_backend_mismatch",
            ),
        ),
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="HS-IR plan alignment failed",
    ):
        build_gate_report(runtime_hs_ir_plan_alignment_report=failed_alignment)


def test_runtime_evidence_gate_rejects_unbound_hs_ir_plan_alignment() -> None:
    report = build_alignment_report()
    unbound_alignment = replace(
        report,
        graph_name="runtime_other_backend_equivalence",
        partition_plan_graph_name="runtime_other_backend_equivalence",
        execution_trace_graph_name="runtime_other_backend_equivalence",
    )

    assert unbound_alignment.passed
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="HS-IR plan alignment binding",
    ):
        build_gate_report(runtime_hs_ir_plan_alignment_report=unbound_alignment)


def test_runtime_evidence_gate_rejects_missing_backend_equivalence_matrix_graph() -> None:
    report = build_current_runtime_evidence_matrix_report()
    without_mixed_equivalence = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_missing_mixed_backend_equivalence_graph",
        tuple(
            graph
            for graph in report.graphs
            if graph.graph_id != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
        ),
    )

    assert without_mixed_equivalence.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="mixed backend equivalence matrix coverage",
    ):
        build_gate_report(matrix_report=without_mixed_equivalence)


def test_runtime_evidence_gate_rejects_malformed_backend_equivalence_matrix_graph() -> None:
    report = build_current_runtime_evidence_matrix_report()
    malformed_mixed_equivalence = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_malformed_mixed_backend_equivalence_graph",
        tuple(
            replace(graph, source_boundary="typed_compute_graph")
            if graph.graph_id == RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert malformed_mixed_equivalence.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="mixed backend equivalence matrix coverage",
    ):
        build_gate_report(matrix_report=malformed_mixed_equivalence)


def test_runtime_evidence_gate_rejects_broadened_backend_equivalence_matrix_scope() -> None:
    report = build_current_runtime_evidence_matrix_report()
    broadened_mixed_equivalence = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_broadened_mixed_backend_equivalence_graph",
        tuple(
            replace(
                graph,
                artifacts=(
                    *graph.artifacts,
                    RuntimeEvidenceArtifact(
                        artifact_kind="input_manifest",
                        artifact_id="runtime_mixed_backend_equivalence_input_manifest",
                    ),
                ),
                required_artifact_kinds=(
                    *RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS,
                    "input_manifest",
                ),
            )
            if graph.graph_id == RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert broadened_mixed_equivalence.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="mixed backend equivalence matrix coverage",
    ):
        build_gate_report(matrix_report=broadened_mixed_equivalence)


def test_runtime_evidence_gate_rejects_wrong_backend_equivalence_matrix_artifact_id() -> None:
    report = build_current_runtime_evidence_matrix_report()
    mismatched_mixed_equivalence = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_wrong_mixed_backend_equivalence_artifact_id",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    replace(
                        artifact,
                        artifact_id="runtime_backend_equivalence_other",
                    )
                    if artifact.artifact_kind == "backend_equivalence"
                    else artifact
                    for artifact in graph.artifacts
                ),
            )
            if graph.graph_id == RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert mismatched_mixed_equivalence.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="mixed backend equivalence matrix coverage",
    ):
        build_gate_report(matrix_report=mismatched_mixed_equivalence)


def test_runtime_evidence_gate_rejects_wrong_hs_ir_alignment_matrix_artifact_id() -> None:
    report = build_current_runtime_evidence_matrix_report()
    mismatched_alignment = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_wrong_hs_ir_alignment_artifact_id",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    replace(
                        artifact,
                        artifact_id="runtime_hs_ir_plan_alignment_other",
                    )
                    if artifact.artifact_kind == "runtime_hs_ir_plan_alignment"
                    else artifact
                    for artifact in graph.artifacts
                ),
            )
            if graph.graph_id == RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert mismatched_alignment.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="HS-IR plan alignment matrix coverage",
    ):
        build_gate_report(matrix_report=mismatched_alignment)


def test_runtime_evidence_gate_rejects_failed_backend_equivalence_portfolio() -> None:
    vector_report = build_vector_backend_equivalence_report()
    candidate = replace(
        vector_report.runs[1],
        planned_backend_sequence=vector_report.runs[0].planned_backend_sequence,
    )
    failed_vector = RuntimeBackendEquivalenceReport(
        graph_name=vector_report.graph_name,
        baseline_run_id=vector_report.baseline_run_id,
        candidate_run_id=vector_report.candidate_run_id,
        runs=(vector_report.runs[0], candidate),
        comparisons=vector_report.comparisons,
        issues=(
            RuntimeBackendEquivalenceIssue(
                subject="backend_sequence",
                issue_code="backend_sequences_not_distinct",
            ),
        ),
    )
    failed_portfolio = build_runtime_backend_equivalence_portfolio_report(
        "runtime_backend_equivalence_portfolio",
        (
            build_backend_equivalence_report(),
            failed_vector,
            build_mixed_backend_equivalence_report(),
        ),
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio failed",
    ):
        build_gate_report(backend_equivalence_portfolio_report=failed_portfolio)


def test_runtime_evidence_gate_rejects_unbound_backend_equivalence_portfolio() -> None:
    subportfolio = build_runtime_backend_equivalence_portfolio_report(
        "runtime_backend_equivalence_portfolio",
        (
            build_backend_equivalence_report(),
            build_mixed_backend_equivalence_report(),
        ),
    )

    assert subportfolio.passed
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio binding",
    ):
        build_gate_report(backend_equivalence_portfolio_report=subportfolio)


def test_runtime_evidence_gate_rejects_forged_backend_equivalence_portfolio_slice() -> None:
    report = build_runtime_backend_equivalence_portfolio_report(
        "runtime_backend_equivalence_portfolio",
        (
            build_backend_equivalence_report(),
            build_vector_backend_equivalence_report(),
            build_mixed_backend_equivalence_report(),
        ),
    )
    forged = RuntimeBackendEquivalencePortfolioReport(
        portfolio_id=report.portfolio_id,
        slices=(
            replace(report.slices[0], graph_name="other_backend_equivalence"),
            *report.slices[1:],
        ),
        issues=(),
    )

    assert forged.passed
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio binding",
    ):
        build_gate_report(backend_equivalence_portfolio_report=forged)


def test_runtime_evidence_gate_rejects_missing_backend_equivalence_portfolio_matrix_graph() -> None:
    report = build_current_runtime_evidence_matrix_report()
    without_portfolio = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_missing_backend_equivalence_portfolio_graph",
        tuple(
            graph
            for graph in report.graphs
            if graph.graph_id != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID
        ),
    )

    assert without_portfolio.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio matrix coverage",
    ):
        build_gate_report(matrix_report=without_portfolio)


def test_runtime_evidence_gate_rejects_malformed_backend_portfolio_matrix() -> None:
    report = build_current_runtime_evidence_matrix_report()
    malformed_portfolio = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_malformed_backend_equivalence_portfolio_graph",
        tuple(
            replace(graph, source_boundary="typed_compute_graph")
            if graph.graph_id == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert malformed_portfolio.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio matrix coverage",
    ):
        build_gate_report(matrix_report=malformed_portfolio)


def test_runtime_evidence_gate_rejects_broadened_backend_portfolio_matrix_scope() -> None:
    report = build_current_runtime_evidence_matrix_report()
    broadened_portfolio = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_broadened_backend_equivalence_portfolio_graph",
        tuple(
            replace(
                graph,
                artifacts=(
                    *graph.artifacts,
                    RuntimeEvidenceArtifact(
                        artifact_kind="input_manifest",
                        artifact_id="runtime_backend_equivalence_portfolio_input_manifest",
                    ),
                ),
                required_artifact_kinds=(
                    "backend_equivalence_portfolio",
                    "input_manifest",
                ),
            )
            if graph.graph_id == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert broadened_portfolio.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio matrix coverage",
    ):
        build_gate_report(matrix_report=broadened_portfolio)


def test_runtime_evidence_gate_rejects_wrong_backend_portfolio_matrix_artifact_id() -> None:
    report = build_current_runtime_evidence_matrix_report()
    mismatched_portfolio = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_wrong_backend_equivalence_portfolio_artifact_id",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    replace(
                        artifact,
                        artifact_id="runtime_backend_equivalence_other_policy",
                    )
                    if artifact.artifact_kind == "backend_equivalence_portfolio_policy"
                    else artifact
                    for artifact in graph.artifacts
                ),
            )
            if graph.graph_id == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID
            else graph
            for graph in report.graphs
        ),
    )

    assert mismatched_portfolio.runtime_evidence_matrix_complete
    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio matrix coverage",
    ):
        build_gate_report(matrix_report=mismatched_portfolio)


def test_runtime_evidence_gate_rejects_unbound_backend_equivalence_portfolio_policy() -> None:
    policy = build_default_runtime_backend_equivalence_portfolio_policy_report()
    forged_requirement = RuntimeBackendEquivalencePortfolioRequirement(
        slice_id="runtime_backend_equivalence",
        graph_name="runtime_backend_equivalence",
        baseline_run_id="reference_cpu",
        candidate_run_id="systolic_sim",
        baseline_backend_sequence=("reference-cpu", "reference-cpu"),
        candidate_backend_sequence=("vector-sim", "reference-cpu"),
    )
    forged_policy = RuntimeBackendEquivalencePortfolioPolicyReport(
        portfolio_id=policy.portfolio_id,
        requirements=(forged_requirement, *policy.requirements[1:]),
        required_candidate_backend_families=policy.required_candidate_backend_families,
    )

    with pytest.raises(
        RuntimeEvidenceGateError,
        match="backend equivalence portfolio policy failed",
    ):
        build_gate_report(backend_equivalence_portfolio_policy_report=forged_policy)


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


def test_runtime_evidence_gate_rejects_unbound_execution_receipt_digest() -> None:
    report = build_execution_receipt_report()
    forged_link = replace(
        report.evidence_links[1],
        metadata_digest="sha256:" + "1" * 64,
    )
    forged_receipt = RuntimeExecutionReceiptReport(
        graph_name=report.graph_name,
        evidence_links=(
            report.evidence_links[0],
            forged_link,
            *report.evidence_links[2:],
        ),
        operations=report.operations,
        issues=(),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="receipt binding failed"):
        build_gate_report(execution_receipt_report=forged_receipt)


def test_runtime_evidence_gate_rejects_failed_execution_evidence_bundle() -> None:
    receipt = build_execution_receipt_report()
    tensor_store = build_tensor_store_evidence_report()
    input_manifest = build_input_manifest_report()
    output_manifest = build_output_manifest_report()
    reference_correctness = build_reference_correctness_report()
    forged_input_link = replace(
        receipt.evidence_links[1],
        metadata_digest="sha256:" + "1" * 64,
    )
    forged_receipt = RuntimeExecutionReceiptReport(
        graph_name=receipt.graph_name,
        evidence_links=(
            receipt.evidence_links[0],
            forged_input_link,
            *receipt.evidence_links[2:],
        ),
        operations=receipt.operations,
        issues=(),
    )
    failed_bundle = RuntimeExecutionEvidenceBundleReport(
        graph_name=receipt.graph_name,
        tensor_store_report=tensor_store,
        input_manifest_report=input_manifest,
        output_manifest_report=output_manifest,
        reference_correctness_report=reference_correctness,
        execution_receipt_report=forged_receipt,
        issues=(
            RuntimeExecutionEvidenceBundleIssue(
                section="input_manifest",
                issue_code="metadata_digest_mismatch",
            ),
        ),
    )

    with pytest.raises(RuntimeEvidenceGateError, match="evidence bundle failed"):
        build_gate_report(execution_evidence_bundle_report=failed_bundle)


def test_runtime_evidence_gate_rejects_unbound_execution_evidence_bundle() -> None:
    receipt = build_execution_receipt_report()
    tensor_store = build_tensor_store_evidence_report()
    input_manifest = build_input_manifest_report()
    output_manifest = build_output_manifest_report()
    reference_correctness = build_reference_correctness_report()
    truncated_receipt = RuntimeExecutionReceiptReport(
        graph_name=receipt.graph_name,
        evidence_links=receipt.evidence_links,
        operations=receipt.operations[:-1],
        issues=(),
    )
    stale_bundle = build_runtime_execution_evidence_bundle_report(
        tensor_store,
        input_manifest,
        output_manifest,
        reference_correctness,
        truncated_receipt,
    )

    with pytest.raises(RuntimeEvidenceGateError, match="evidence bundle binding failed"):
        build_gate_report(execution_evidence_bundle_report=stale_bundle)


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
