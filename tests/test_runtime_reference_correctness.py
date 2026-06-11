from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from examples.proof_of_execution import run_proof
from examples.runtime_reference_correctness import build_reference_correctness_report
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS,
    RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL,
    RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL,
    RUNTIME_REFERENCE_CORRECTNESS_REPORT_SCHEMA_VERSION,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeReferenceComparison,
    RuntimeReferenceCorrectnessIssue,
    RuntimeReferenceCorrectnessReport,
    assert_runtime_reference_correctness,
    build_runtime_reference_correctness_report,
    dump_runtime_reference_correctness_report,
    runtime_reference_correctness_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_REFERENCE_CORRECTNESS_COMPARISONS

GOLDEN_PATH = Path("tests/golden/runtime_reference_correctness/proof_of_execution.json")
SCHEMA_PATH = Path("schemas/runtime_reference_correctness_report.v0.schema.json")


def test_runtime_reference_correctness_passes_for_execution_proof() -> None:
    report = build_reference_correctness_report()

    assert report.correctness_contract == RUNTIME_REFERENCE_CORRECTNESS_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.output_manifest_contract == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert report.passed
    assert report.issues == ()
    assert report.reference_tensor_names == ("activated",)
    assert len(report.comparisons) == 1
    comparison = report.comparisons[0]
    assert comparison.tensor_name == "activated"
    assert comparison.comparison_status == "matched"
    assert comparison.expected_shape == (2,)
    assert comparison.output_shape == (2,)
    assert comparison.reference_shape == (2,)
    assert comparison.output_dtype == "float64"
    assert comparison.reference_dtype == "float64"
    assert comparison.rtol == RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL
    assert comparison.atol == RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL
    assert comparison.output_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert comparison.reference_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert tuple(runtime_reference_correctness_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "comparison_count",
        "comparison_metadata_digest",
        "comparisons",
        "correctness_contract",
        "executor_contract",
        "graph_name",
        "issues",
        "output_manifest_contract",
        "passed",
        "raw_value_policy",
        "reference_tensor_names",
        "schema_version",
    )


def test_runtime_reference_correctness_dump_matches_golden() -> None:
    assert dump_runtime_reference_correctness_report(
        build_reference_correctness_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_reference_correctness_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_reference_correctness.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_reference_correctness.data_only.v0" in completed.stdout
    assert '"comparison_status": "matched"' in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout


def test_runtime_reference_correctness_assertion_returns_report() -> None:
    assert assert_runtime_reference_correctness(
        build_reference_correctness_report()
    ).passed


def test_runtime_reference_correctness_records_value_mismatch_as_issue() -> None:
    proof = run_proof()
    bad_reference = proof.reference.copy()
    bad_reference[0] = bad_reference[0] + 1.0
    report = build_runtime_reference_correctness_report(
        proof.compiled.hac_ir.graph,
        proof.execution,
        {"activated": bad_reference},
    )

    assert not report.passed
    assert report.comparisons[0].comparison_status == "mismatched"
    assert report.issues == (
        RuntimeReferenceCorrectnessIssue(
            tensor_name="activated",
            issue_code="reference_value_mismatch",
        ),
    )


def test_runtime_reference_correctness_records_missing_reference_as_issue() -> None:
    proof = run_proof()
    report = build_runtime_reference_correctness_report(
        proof.compiled.hac_ir.graph,
        proof.execution,
        {},
    )

    assert not report.passed
    assert report.comparisons[0].comparison_status == "missing_reference"
    assert report.issues[0].issue_code == "reference_missing"


def test_runtime_reference_correctness_records_unexpected_reference_as_issue() -> None:
    proof = run_proof()
    report = build_runtime_reference_correctness_report(
        proof.compiled.hac_ir.graph,
        proof.execution,
        {
            "activated": proof.reference,
            "extra_reference": np.zeros((2,), dtype=np.float64),
        },
    )

    assert not report.passed
    assert report.issues[-1].issue_code == "unexpected_reference"


def test_runtime_reference_correctness_records_invalid_reference_as_issue() -> None:
    proof = run_proof()
    invalid = proof.reference.copy()
    invalid[0] = np.nan
    report = build_runtime_reference_correctness_report(
        proof.compiled.hac_ir.graph,
        proof.execution,
        {"activated": invalid},
    )

    assert not report.passed
    assert report.comparisons[0].comparison_status == "invalid_reference"
    assert report.issues[0].issue_code == "reference_invalid"


def test_runtime_reference_correctness_rejects_non_plain_reference_mapping() -> None:
    class CustomReferences(dict[str, object]):
        pass

    proof = run_proof()

    with pytest.raises(TypeError, match="plain dict"):
        build_runtime_reference_correctness_report(
            proof.compiled.hac_ir.graph,
            proof.execution,
            CustomReferences({"activated": proof.reference}),
        )


def test_runtime_reference_correctness_issues_must_be_derived() -> None:
    report = build_reference_correctness_report()
    bad_comparison = replace(report.comparisons[0], comparison_status="mismatched")

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeReferenceCorrectnessReport(
            graph_name=report.graph_name,
            comparisons=(bad_comparison,),
            reference_tensor_names=report.reference_tensor_names,
            issues=(),
        )


def test_runtime_reference_correctness_requires_reference_name_inventory() -> None:
    report = build_reference_correctness_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeReferenceCorrectnessReport(
            graph_name=report.graph_name,
            comparisons=report.comparisons,
            reference_tensor_names=(),
            issues=(),
        )


def test_runtime_reference_correctness_rejects_raw_value_status() -> None:
    with pytest.raises(ValueError, match="omit output values"):
        RuntimeReferenceComparison(
            tensor_name="activated",
            expected_shape=(2,),
            expected_dtype="float64",
            output_shape=(2,),
            output_dtype="float64",
            reference_shape=(2,),
            reference_dtype="float64",
            rtol=RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL,
            atol=RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL,
            comparison_status="matched",
            output_value_status="included",
        )


def test_runtime_reference_correctness_rejects_missing_expected_dtype() -> None:
    with pytest.raises(ValueError, match="concrete dtype"):
        RuntimeReferenceComparison(
            tensor_name="activated",
            expected_shape=(2,),
            expected_dtype="missing",
            output_shape=(2,),
            output_dtype="float64",
            reference_shape=(2,),
            reference_dtype="float64",
            rtol=RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL,
            atol=RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL,
            comparison_status="mismatched",
        )


def test_runtime_reference_correctness_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeReferenceComparison(
            tensor_name="python_source",
            expected_shape=(2,),
            expected_dtype="float64",
            output_shape=(2,),
            output_dtype="float64",
            reference_shape=(2,),
            reference_dtype="float64",
            rtol=RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL,
            atol=RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL,
            comparison_status="matched",
        )


def test_runtime_reference_correctness_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_reference_correctness_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_REFERENCE_CORRECTNESS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS
    )
    assert schema["properties"]["correctness_contract"]["const"] == (
        RUNTIME_REFERENCE_CORRECTNESS_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["output_manifest_contract"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_CONTRACT
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["comparisons"]["maxItems"] == (
        MAX_RUNTIME_REFERENCE_CORRECTNESS_COMPARISONS
    )
    assert schema["properties"]["comparisons"]["minItems"] == 1
    assert schema["$defs"]["comparison"]["properties"]["expected_dtype"] == {
        "$ref": "#/$defs/concrete_dtype"
    }
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_reference_correctness_schema_fails_closed() -> None:
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
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["comparison"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "reference_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_reference_correctness_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_REFERENCE_CORRECTNESS_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS
    assert golden["correctness_contract"] == RUNTIME_REFERENCE_CORRECTNESS_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["output_manifest_contract"] == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["comparison_count"] == len(golden["comparisons"]) == 1
    assert golden["reference_tensor_names"] == ["activated"]
    assert golden["comparisons"][0]["comparison_status"] == "matched"
    assert golden["comparisons"][0]["output_value_status"] == "omitted_by_policy"
    assert golden["comparisons"][0]["reference_value_status"] == "omitted_by_policy"


def test_runtime_reference_correctness_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_reference_correctness_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_REFERENCE_CORRECTNESS.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0110-runtime-reference-correctness.md"),
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
