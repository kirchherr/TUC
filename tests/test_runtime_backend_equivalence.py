from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_backend_equivalence import build_backend_equivalence_report
from tuc import (
    MAX_RUNTIME_BACKEND_EQUIVALENCE_COMPARISONS,
    MAX_RUNTIME_BACKEND_EQUIVALENCE_RUNS,
    RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS,
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_ATOL,
    RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_RTOL,
    RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeBackendEquivalenceIssue,
    RuntimeBackendEquivalenceReport,
    RuntimeBackendEquivalenceRun,
    assert_runtime_backend_equivalence,
    dump_runtime_backend_equivalence_report,
    runtime_backend_equivalence_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/runtime_backend_equivalence/current_report.json")
SCHEMA_PATH = Path("schemas/runtime_backend_equivalence_report.v0.schema.json")


def test_runtime_backend_equivalence_passes_for_reference_and_systolic() -> None:
    report = build_backend_equivalence_report()

    assert report.equivalence_contract == RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.trusted_executor_registry == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert report.passed
    assert report.issues == ()
    assert report.baseline_run_id == "reference_cpu"
    assert report.candidate_run_id == "systolic_sim"
    assert len(report.runs) == 2
    baseline, candidate = report.runs
    assert baseline.planned_backend_sequence == ("reference-cpu", "reference-cpu")
    assert candidate.planned_backend_sequence == ("systolic-sim", "reference-cpu")
    assert baseline.output_tensor_names == ("activated",)
    assert candidate.output_tensor_names == ("activated",)
    assert baseline.output_metadata_digest == candidate.output_metadata_digest
    assert len(report.comparisons) == 1
    comparison = report.comparisons[0]
    assert comparison.tensor_name == "activated"
    assert comparison.comparison_status == "matched"
    assert comparison.expected_shape == (2, 2)
    assert comparison.baseline_shape == (2, 2)
    assert comparison.candidate_shape == (2, 2)
    assert comparison.baseline_dtype == "float64"
    assert comparison.candidate_dtype == "float64"
    assert comparison.rtol == RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_RTOL
    assert comparison.atol == RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_ATOL
    assert comparison.baseline_output_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert comparison.candidate_output_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert tuple(runtime_backend_equivalence_report_to_dict(report)) == (
        "artifact_status",
        "baseline_run_id",
        "blocked_execution_surfaces",
        "candidate_run_id",
        "comparison_count",
        "comparison_metadata_digest",
        "comparisons",
        "equivalence_contract",
        "executor_contract",
        "graph_name",
        "issues",
        "passed",
        "raw_value_policy",
        "run_count",
        "runs",
        "schema_version",
        "trusted_executor_registry",
    )


def test_runtime_backend_equivalence_dump_matches_golden() -> None:
    assert dump_runtime_backend_equivalence_report(
        build_backend_equivalence_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_backend_equivalence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_backend_equivalence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_backend_equivalence.data_only.v0" in completed.stdout
    assert '"planned_backend_sequence": [' in completed.stdout
    assert '"reference-cpu"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"comparison_status": "matched"' in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_runtime_backend_equivalence_assertion_returns_report() -> None:
    assert assert_runtime_backend_equivalence(build_backend_equivalence_report()).passed


def test_runtime_backend_equivalence_rejects_same_backend_sequence_as_issue() -> None:
    report = build_backend_equivalence_report()
    candidate = replace(
        report.runs[1],
        planned_backend_sequence=report.runs[0].planned_backend_sequence,
    )
    failing = RuntimeBackendEquivalenceReport(
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

    assert not failing.passed
    assert failing.issues[0].issue_code == "backend_sequences_not_distinct"


def test_runtime_backend_equivalence_issues_must_be_derived() -> None:
    report = build_backend_equivalence_report()
    bad_comparison = replace(report.comparisons[0], comparison_status="mismatched")

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeBackendEquivalenceReport(
            graph_name=report.graph_name,
            baseline_run_id=report.baseline_run_id,
            candidate_run_id=report.candidate_run_id,
            runs=report.runs,
            comparisons=(bad_comparison,),
            issues=(),
        )


def test_runtime_backend_equivalence_rejects_raw_value_status() -> None:
    report = build_backend_equivalence_report()

    with pytest.raises(ValueError, match="omit output values"):
        replace(report.runs[0], output_value_status="included")

    with pytest.raises(ValueError, match="omit baseline values"):
        replace(report.comparisons[0], baseline_output_value_status="included")


def test_runtime_backend_equivalence_rejects_forbidden_surface_names() -> None:
    report = build_backend_equivalence_report()

    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeBackendEquivalenceRun(
            run_id="python_source",
            graph_name=report.graph_name,
            planned_backend_sequence=("reference-cpu",),
            output_tensor_names=("activated",),
            output_metadata_digest=report.runs[0].output_metadata_digest,
            trace_step_count=1,
            tensor_record_count=1,
        )


def test_runtime_backend_equivalence_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_backend_equivalence_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS
    )
    assert schema["properties"]["equivalence_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["trusted_executor_registry"]["const"] == (
        TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["runs"]["maxItems"] == (
        MAX_RUNTIME_BACKEND_EQUIVALENCE_RUNS
    )
    assert schema["properties"]["comparisons"]["maxItems"] == (
        MAX_RUNTIME_BACKEND_EQUIVALENCE_COMPARISONS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_backend_equivalence_schema_fails_closed() -> None:
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
        "tensor_values",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["run"]["properties"]
        assert forbidden not in schema["$defs"]["comparison"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_backend_equivalence_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS
    assert golden["equivalence_contract"] == RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["run_count"] == len(golden["runs"]) == 2
    assert golden["comparison_count"] == len(golden["comparisons"]) == 1
    assert golden["runs"][0]["planned_backend_sequence"] == [
        "reference-cpu",
        "reference-cpu",
    ]
    assert golden["runs"][1]["planned_backend_sequence"] == [
        "systolic-sim",
        "reference-cpu",
    ]
    assert golden["runs"][0]["output_metadata_digest"] == (
        golden["runs"][1]["output_metadata_digest"]
    )
    assert golden["comparisons"][0]["comparison_status"] == "matched"
    assert golden["comparisons"][0]["baseline_output_value_status"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert golden["comparisons"][0]["candidate_output_value_status"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )


def test_runtime_backend_equivalence_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_backend_equivalence_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0136-runtime-backend-equivalence-evidence.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
