from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.runtime_evidence_matrix import build_matrix_report
from tuc import (
    RUNTIME_EVIDENCE_MATRIX_CONTRACT,
    RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS,
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGraph,
    RuntimeEvidenceMatrixReport,
    build_runtime_evidence_matrix_report,
    dump_runtime_evidence_matrix_report,
    runtime_evidence_matrix_report_to_dict,
)

_GOLDEN = Path("tests/golden/proofs/runtime_evidence_matrix_report.json")


def test_runtime_evidence_matrix_tracks_current_gaps() -> None:
    report = build_matrix_report()
    graphs = {graph.graph_id: graph for graph in report.graphs}

    assert report.evidence_contract == RUNTIME_EVIDENCE_MATRIX_CONTRACT
    assert len(report.graphs) == 7
    assert report.runtime_evidence_matrix_complete
    assert graphs["proof_of_abstraction"].runtime_evidence_complete
    assert graphs["proof_of_reduction"].runtime_evidence_complete
    assert graphs["proof_of_softmax"].runtime_evidence_complete
    assert graphs["proof_of_execution"].runtime_evidence_complete
    assert graphs["proof_of_systolic_execution"].runtime_evidence_complete
    assert graphs["triton_metadata_mvp_families"].runtime_evidence_complete
    assert graphs["source_intent_return_mlp"].runtime_evidence_complete
    assert graphs["source_intent_return_mlp"].source_boundary == (
        "source_intent_metadata"
    )
    assert graphs["source_intent_return_mlp"].present_artifact_kinds >= {
        "source_intent_return_semantics",
        "source_intent_runtime_returns",
    }
    assert all(
        "input_manifest" in graph.present_artifact_kinds for graph in report.graphs
    )
    assert all(
        "output_contract" in graph.present_artifact_kinds for graph in report.graphs
    )
    assert all(
        "public_output_bundle" in graph.present_artifact_kinds
        for graph in report.graphs
    )
    assert all(
        "execution_receipt" in graph.present_artifact_kinds
        for graph in report.graphs
    )
    assert report.issues == ()
    assert tuple(runtime_evidence_matrix_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "evidence_contract",
        "graph_count",
        "graphs",
        "issues",
        "matrix_id",
        "required_artifact_kinds",
        "runtime_evidence_matrix_complete",
        "schema_version",
    )


def test_runtime_evidence_matrix_dump_matches_golden() -> None:
    assert dump_runtime_evidence_matrix_report(build_matrix_report()) == (
        _GOLDEN.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_evidence_matrix_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_evidence_matrix.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_evidence_matrix.data_only.v0" in completed.stdout
    assert '"runtime_evidence_matrix_complete": true' in completed.stdout
    assert '"input_manifest"' in completed.stdout
    assert '"output_contract"' in completed.stdout
    assert '"public_output_bundle"' in completed.stdout
    assert '"execution_receipt"' in completed.stdout
    assert "triton_metadata_mvp_families" in completed.stdout
    assert "source_intent_return_mlp" in completed.stdout
    assert '"source_intent_runtime_returns"' in completed.stdout


def test_runtime_evidence_matrix_rejects_unknown_artifact_kind() -> None:
    with pytest.raises(ValueError, match="unsupported runtime evidence artifact kind"):
        build_runtime_evidence_matrix_report(
            "bad_runtime_matrix",
            (
                RuntimeEvidenceGraph(
                    graph_id="bad_graph",
                    graph_family="objective_alpha",
                    source_boundary="typed_compute_graph",
                    artifacts=(
                        RuntimeEvidenceArtifact(
                            artifact_kind="raw_native_trace",
                            artifact_id="bad_native_trace",
                        ),
                    ),
                ),
            ),
        )


def test_runtime_evidence_matrix_rejects_duplicate_graphs() -> None:
    graph = RuntimeEvidenceGraph(
        graph_id="duplicate_graph",
        graph_family="objective_alpha",
        source_boundary="typed_compute_graph",
        artifacts=(),
    )

    with pytest.raises(ValueError, match="duplicate runtime evidence graph id"):
        build_runtime_evidence_matrix_report(
            "duplicate_runtime_matrix",
            (graph, graph),
        )


def test_runtime_evidence_matrix_rejects_duplicate_artifact_kinds() -> None:
    with pytest.raises(ValueError, match="duplicate runtime evidence artifact kind"):
        build_runtime_evidence_matrix_report(
            "duplicate_artifact_matrix",
            (
                RuntimeEvidenceGraph(
                    graph_id="duplicate_artifacts",
                    graph_family="objective_alpha",
                    source_boundary="typed_compute_graph",
                    artifacts=(
                        RuntimeEvidenceArtifact(
                            artifact_kind="hac_ir_golden",
                            artifact_id="first_hac_ir",
                        ),
                        RuntimeEvidenceArtifact(
                            artifact_kind="hac_ir_golden",
                            artifact_id="second_hac_ir",
                        ),
                    ),
                ),
            ),
        )


def test_runtime_evidence_matrix_rejects_execution_surface_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        build_runtime_evidence_matrix_report(
            "runtime_matrix_with_surface",
            (
                RuntimeEvidenceGraph(
                    graph_id="surface_graph",
                    graph_family="objective_alpha",
                    source_boundary="typed_compute_graph",
                    artifacts=(
                        RuntimeEvidenceArtifact(
                            artifact_kind="hac_ir_golden",
                            artifact_id="python_source",
                        ),
                    ),
                ),
            ),
        )


def test_runtime_evidence_matrix_rejects_path_like_artifact_ids() -> None:
    with pytest.raises(ValueError, match="safe runtime evidence identifier"):
        build_runtime_evidence_matrix_report(
            "runtime_matrix_with_path",
            (
                RuntimeEvidenceGraph(
                    graph_id="path_graph",
                    graph_family="objective_alpha",
                    source_boundary="typed_compute_graph",
                    artifacts=(
                        RuntimeEvidenceArtifact(
                            artifact_kind="hac_ir_golden",
                            artifact_id="tests/golden/hac_ir/proof",
                        ),
                    ),
                ),
            ),
        )


def test_runtime_evidence_matrix_report_issues_must_be_derived() -> None:
    graph = RuntimeEvidenceGraph(
        graph_id="partial_graph",
        graph_family="objective_alpha",
        source_boundary="typed_compute_graph",
        artifacts=(
            RuntimeEvidenceArtifact(
                artifact_kind="reference_correctness",
                artifact_id="partial_graph_reference_semantics",
            ),
        ),
    )
    report = RuntimeEvidenceMatrixReport(
        matrix_id="forged_runtime_matrix",
        graphs=(graph,),
        issues=(),
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        dump_runtime_evidence_matrix_report(report)


def test_runtime_evidence_required_artifact_order_is_stable() -> None:
    assert RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS == (
        "hac_ir_golden",
        "runtime_plan_golden",
        "compiler_decision_golden",
        "execution_readiness_golden",
        "execution_trace_golden",
        "input_manifest",
        "output_contract",
        "public_output_bundle",
        "reference_correctness",
        "execution_receipt",
    )
