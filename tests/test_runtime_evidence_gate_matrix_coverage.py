from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_evidence_gate import (
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID,
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID,
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS,
    build_gate_matrix_bindings,
    build_gate_matrix_coverage_report,
)
from tuc import (
    RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_ARTIFACT_STATUS,
    RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_CONTRACT,
    RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_REPORT_SCHEMA_VERSION,
    RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_STATUSES,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGateMatrixBinding,
    build_current_runtime_evidence_matrix_report,
    build_runtime_evidence_gate_matrix_coverage_report,
    build_runtime_evidence_matrix_report,
    dump_runtime_evidence_gate_matrix_coverage_report,
    runtime_evidence_gate_matrix_coverage_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/proofs/runtime_evidence_gate_matrix_coverage_report.json"
)
SCHEMA_PATH = Path(
    "schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json"
)


def test_runtime_evidence_gate_matrix_coverage_matches_current_gate() -> None:
    report = build_gate_matrix_coverage_report()

    assert report.coverage_contract == RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_CONTRACT
    assert report.artifact_status == (
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_ARTIFACT_STATUS
    )
    assert report.matrix_complete
    assert report.coverage_passed
    assert report.binding_count == 4
    assert report.issues == ()
    assert {binding.coverage_status for binding in report.bindings} == {"covered"}
    assert tuple(binding.binding_id for binding in report.bindings) == (
        "runtime_backend_equivalence_matrix",
        "runtime_vector_backend_equivalence_matrix",
        "runtime_mixed_backend_equivalence_matrix",
        "runtime_backend_equivalence_portfolio_matrix",
    )
    mixed = {
        binding.binding_id: binding for binding in report.bindings
    }["runtime_mixed_backend_equivalence_matrix"]
    assert mixed.expected_artifact_ids == (
        RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS
    )
    assert mixed.observed_artifact_ids == (
        RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS
    )
    assert tuple(runtime_evidence_gate_matrix_coverage_report_to_dict(report)) == (
        "artifact_status",
        "binding_count",
        "bindings",
        "blocked_execution_surfaces",
        "coverage_contract",
        "coverage_id",
        "coverage_passed",
        "issues",
        "matrix_complete",
        "matrix_id",
        "schema_version",
    )


def test_runtime_evidence_gate_matrix_coverage_dump_matches_golden() -> None:
    assert dump_runtime_evidence_gate_matrix_coverage_report(
        build_gate_matrix_coverage_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_evidence_gate_matrix_coverage_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_evidence_gate_matrix_coverage.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_evidence_gate_matrix_coverage.data_only.v0" in completed.stdout
    assert '"coverage_passed": true' in completed.stdout
    assert '"binding_count": 4' in completed.stdout
    assert "runtime_backend_equivalence_systolic" in completed.stdout
    assert "runtime_hs_ir_plan_alignment_mixed" in completed.stdout
    assert "runtime_backend_equivalence_portfolio_policy" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "command_line" not in completed.stdout


def test_runtime_evidence_gate_matrix_coverage_rejects_wrong_artifact_id() -> None:
    matrix = build_current_runtime_evidence_matrix_report()
    forged = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_matrix_coverage_wrong_artifact",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    RuntimeEvidenceArtifact(
                        artifact_kind=artifact.artifact_kind,
                        artifact_id="runtime_backend_equivalence_other",
                    )
                    if artifact.artifact_kind == "backend_equivalence"
                    else artifact
                    for artifact in graph.artifacts
                ),
            )
            if graph.graph_id == RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
            else graph
            for graph in matrix.graphs
        ),
    )

    report = build_runtime_evidence_gate_matrix_coverage_report(
        "runtime_evidence_gate_matrix_coverage",
        forged,
        build_gate_matrix_bindings(),
    )

    assert not report.coverage_passed
    assert report.issues == (
        "runtime_mixed_backend_equivalence_matrix.artifact_id_mismatch",
    )
    mixed = {
        binding.binding_id: binding for binding in report.bindings
    }["runtime_mixed_backend_equivalence_matrix"]
    assert mixed.coverage_status == "failed"
    assert mixed.observed_artifact_ids == (
        "runtime_backend_equivalence_other",
        "runtime_hs_ir_plan_alignment_mixed",
    )


def test_runtime_evidence_gate_matrix_coverage_rejects_missing_portfolio_graph() -> None:
    matrix = build_current_runtime_evidence_matrix_report()
    forged = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_matrix_coverage_missing_portfolio",
        tuple(
            graph
            for graph in matrix.graphs
            if graph.graph_id != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID
        ),
    )

    report = build_runtime_evidence_gate_matrix_coverage_report(
        "runtime_evidence_gate_matrix_coverage",
        forged,
        build_gate_matrix_bindings(),
    )

    assert not report.coverage_passed
    assert report.issues == (
        "runtime_backend_equivalence_portfolio_matrix.graph_missing",
    )


def test_runtime_evidence_gate_matrix_coverage_rejects_duplicate_binding_id() -> None:
    binding = build_gate_matrix_bindings()[0]

    with pytest.raises(ValueError, match="duplicate runtime evidence gate"):
        build_runtime_evidence_gate_matrix_coverage_report(
            "runtime_evidence_gate_matrix_coverage",
            build_current_runtime_evidence_matrix_report(),
            (binding, binding),
        )


def test_runtime_evidence_gate_matrix_coverage_rejects_forged_issues() -> None:
    matrix = build_current_runtime_evidence_matrix_report()
    forged = build_runtime_evidence_matrix_report(
        "runtime_evidence_gate_matrix_coverage_wrong_artifact",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    RuntimeEvidenceArtifact(
                        artifact_kind=artifact.artifact_kind,
                        artifact_id="runtime_backend_equivalence_other",
                    )
                    if artifact.artifact_kind == "backend_equivalence"
                    else artifact
                    for artifact in graph.artifacts
                ),
            )
            if graph.graph_id == RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID
            else graph
            for graph in matrix.graphs
        ),
    )
    report = build_runtime_evidence_gate_matrix_coverage_report(
        "runtime_evidence_gate_matrix_coverage",
        forged,
        build_gate_matrix_bindings(),
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        runtime_evidence_gate_matrix_coverage_report_to_dict(
            replace(report, issues=()),
        )


def test_runtime_evidence_gate_matrix_coverage_rejects_forbidden_binding_text() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeEvidenceGateMatrixBinding(
            binding_id="python_source",
            graph_id="runtime_backend_equivalence",
            graph_family="backend_equivalence",
            source_boundary="runtime_backend_equivalence",
            required_artifact_kinds=("backend_equivalence",),
            artifact_ids=("runtime_backend_equivalence_systolic",),
        )


def test_runtime_evidence_gate_matrix_coverage_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_ARTIFACT_STATUS
    )
    assert schema["properties"]["coverage_contract"]["const"] == (
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_CONTRACT
    )
    assert schema["$defs"]["binding"]["properties"]["coverage_status"]["enum"] == (
        list(RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_STATUSES)
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_evidence_gate_matrix_coverage_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "raw_benchmark_output",
        "raw_tensor_value",
        "tensor_value",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["binding"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_evidence_gate_matrix_coverage_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_REPORT_SCHEMA_VERSION
    )
    assert golden["artifact_status"] == (
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_ARTIFACT_STATUS
    )
    assert golden["coverage_contract"] == RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_CONTRACT
    assert golden["coverage_passed"] is True
    assert golden["matrix_complete"] is True
    assert golden["binding_count"] == len(golden["bindings"]) == 4
    assert golden["issues"] == []
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )


def test_runtime_evidence_gate_matrix_coverage_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0147-runtime-evidence-gate-matrix-coverage.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema_node: dict[str, Any]) -> None:
    if schema_node.get("type") == "object":
        assert schema_node.get("additionalProperties") is False
    for value in schema_node.values():
        if isinstance(value, dict):
            _assert_objects_fail_closed(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _assert_objects_fail_closed(item)
