from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_output_manifest import build_output_manifest_report
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS,
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_REPORT_SCHEMA_VERSION,
    RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY,
    RUNTIME_TENSOR_STORE_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RUNTIME_VALUE_RECORD_CONTRACT,
    RuntimeOutputManifestIssue,
    RuntimeOutputManifestReport,
    RuntimeOutputRecord,
    assert_runtime_output_manifest,
    dump_runtime_output_manifest_report,
    runtime_output_manifest_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_OUTPUT_MANIFEST_OUTPUTS

GOLDEN_PATH = Path("tests/golden/runtime_output_manifest/proof_of_execution.json")
SCHEMA_PATH = Path("schemas/runtime_output_manifest_report.v0.schema.json")


def test_runtime_output_manifest_passes_for_execution_proof() -> None:
    report = build_output_manifest_report()

    assert report.manifest_contract == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.passed
    assert report.issues == ()
    assert len(report.expected_outputs) == 1
    assert len(report.outputs) == 1
    assert report.outputs[0].tensor_name == "activated"
    assert report.outputs[0].value_role == "computed"
    assert report.outputs[0].producer_kind == "operation"
    assert report.outputs[0].producer_id == "activation"
    assert report.outputs[0].readonly is True
    assert report.outputs[0].raw_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert tuple(runtime_output_manifest_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "executor_contract",
        "expected_output_count",
        "expected_outputs",
        "graph_name",
        "issues",
        "manifest_contract",
        "output_count",
        "output_metadata_digest",
        "outputs",
        "passed",
        "raw_value_policy",
        "schema_version",
        "store_contract",
        "terminal_output_policy",
        "value_record_contract",
    )


def test_runtime_output_manifest_dump_matches_golden() -> None:
    assert dump_runtime_output_manifest_report(build_output_manifest_report()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_output_manifest_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_output_manifest.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_output_manifest.data_only.v0" in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout


def test_runtime_output_manifest_assertion_returns_report() -> None:
    assert assert_runtime_output_manifest(build_output_manifest_report()).passed


def test_runtime_output_manifest_issues_must_be_derived() -> None:
    report = build_output_manifest_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeOutputManifestReport(
            graph_name=report.graph_name,
            expected_outputs=report.expected_outputs,
            outputs=(),
            issues=(),
        )


def test_runtime_output_manifest_rejects_empty_expected_outputs() -> None:
    with pytest.raises(ValueError, match="expected outputs must not be empty"):
        RuntimeOutputManifestReport(
            graph_name="empty_outputs",
            expected_outputs=(),
            outputs=(),
            issues=(),
        )


def test_runtime_output_manifest_records_mutable_values_as_issue() -> None:
    report = build_output_manifest_report()
    mutable_output = replace(report.outputs[0], readonly=False)
    failing = RuntimeOutputManifestReport(
        graph_name=report.graph_name,
        expected_outputs=report.expected_outputs,
        outputs=(mutable_output,),
        issues=(
            RuntimeOutputManifestIssue(
                tensor_name=mutable_output.tensor_name,
                issue_code="record_value_mutable",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "record_value_mutable"


def test_runtime_output_manifest_rejects_raw_value_status() -> None:
    with pytest.raises(ValueError, match="omit raw values"):
        RuntimeOutputRecord(
            tensor_name="activated",
            shape=(2,),
            dtype="float64",
            value_role="computed",
            producer_kind="operation",
            producer_id="activation",
            readonly=True,
            raw_value_status="included",
        )


def test_runtime_output_manifest_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeOutputRecord(
            tensor_name="python_source",
            shape=(2,),
            dtype="float64",
            value_role="computed",
            producer_kind="operation",
            producer_id="activation",
            readonly=True,
        )


def test_runtime_output_manifest_records_provenance_mismatch_as_issue() -> None:
    report = build_output_manifest_report()
    bad_output = replace(report.outputs[0], producer_id="other_operation")
    failing = RuntimeOutputManifestReport(
        graph_name=report.graph_name,
        expected_outputs=report.expected_outputs,
        outputs=(bad_output,),
        issues=(
            RuntimeOutputManifestIssue(
                tensor_name=bad_output.tensor_name,
                issue_code="producer_id_mismatch",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "producer_id_mismatch"


def test_runtime_output_manifest_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_output_manifest_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS
    )
    assert schema["properties"]["manifest_contract"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["store_contract"]["const"] == (
        RUNTIME_TENSOR_STORE_CONTRACT
    )
    assert schema["properties"]["value_record_contract"]["const"] == (
        RUNTIME_VALUE_RECORD_CONTRACT
    )
    assert schema["properties"]["terminal_output_policy"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["outputs"]["maxItems"] == (
        MAX_RUNTIME_OUTPUT_MANIFEST_OUTPUTS
    )
    assert schema["properties"]["expected_outputs"]["minItems"] == 1
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_output_manifest_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["expected_output"]["properties"]
        assert forbidden not in schema["$defs"]["output_record"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "source_text" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_output_manifest_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_OUTPUT_MANIFEST_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS
    assert golden["manifest_contract"] == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["store_contract"] == RUNTIME_TENSOR_STORE_CONTRACT
    assert golden["value_record_contract"] == RUNTIME_VALUE_RECORD_CONTRACT
    assert golden["terminal_output_policy"] == RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["expected_output_count"] == len(golden["expected_outputs"]) == 1
    assert golden["output_count"] == len(golden["outputs"]) == 1
    assert golden["outputs"][0]["tensor_name"] == "activated"
    assert golden["outputs"][0]["producer_kind"] == "operation"
    assert golden["outputs"][0]["producer_id"] == "activation"
    assert golden["outputs"][0]["raw_value_status"] == "omitted_by_policy"
    assert golden["outputs"][0]["readonly"] is True


def test_runtime_output_manifest_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_output_manifest_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_OUTPUT_MANIFEST.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0109-runtime-output-manifest.md"),
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
