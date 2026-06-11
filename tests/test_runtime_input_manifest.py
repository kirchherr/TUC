from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_input_manifest import build_input_manifest_report
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS,
    RUNTIME_INPUT_MANIFEST_CONTRACT,
    RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY,
    RUNTIME_INPUT_MANIFEST_REPORT_SCHEMA_VERSION,
    RUNTIME_TENSOR_STORE_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RUNTIME_VALUE_RECORD_CONTRACT,
    RuntimeInputManifestIssue,
    RuntimeInputManifestReport,
    RuntimeInputRecord,
    assert_runtime_input_manifest,
    dump_runtime_input_manifest_report,
    runtime_input_manifest_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_INPUT_MANIFEST_INPUTS
from tuc.runtime.executor import TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT

GOLDEN_PATH = Path("tests/golden/runtime_input_manifest/proof_of_execution.json")
SCHEMA_PATH = Path("schemas/runtime_input_manifest_report.v0.schema.json")


def test_runtime_input_manifest_passes_for_execution_proof() -> None:
    report = build_input_manifest_report()

    assert report.manifest_contract == RUNTIME_INPUT_MANIFEST_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.input_contract == TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT
    assert report.passed
    assert report.issues == ()
    assert tuple(input_record.tensor_name for input_record in report.expected_inputs) == (
        "lhs",
        "rhs",
    )
    assert tuple(input_record.tensor_name for input_record in report.inputs) == (
        "lhs",
        "rhs",
    )
    assert report.inputs[0].value_role == "input"
    assert report.inputs[0].producer_kind == "external_input"
    assert report.inputs[0].producer_id == "lhs"
    assert report.inputs[0].readonly is True
    assert report.inputs[0].raw_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert tuple(runtime_input_manifest_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "executor_contract",
        "expected_input_count",
        "expected_inputs",
        "external_input_policy",
        "graph_name",
        "input_contract",
        "input_count",
        "input_metadata_digest",
        "inputs",
        "issues",
        "manifest_contract",
        "passed",
        "raw_value_policy",
        "schema_version",
        "store_contract",
        "value_record_contract",
    )


def test_runtime_input_manifest_dump_matches_golden() -> None:
    assert dump_runtime_input_manifest_report(build_input_manifest_report()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_input_manifest_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_input_manifest.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_input_manifest.data_only.v0" in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout


def test_runtime_input_manifest_assertion_returns_report() -> None:
    assert assert_runtime_input_manifest(build_input_manifest_report()).passed


def test_runtime_input_manifest_issues_must_be_derived() -> None:
    report = build_input_manifest_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeInputManifestReport(
            graph_name=report.graph_name,
            expected_inputs=report.expected_inputs,
            inputs=(),
            issues=(),
        )


def test_runtime_input_manifest_rejects_empty_expected_inputs() -> None:
    with pytest.raises(ValueError, match="expected inputs must not be empty"):
        RuntimeInputManifestReport(
            graph_name="empty_inputs",
            expected_inputs=(),
            inputs=(),
            issues=(),
        )


def test_runtime_input_manifest_records_mutable_values_as_issue() -> None:
    report = build_input_manifest_report()
    mutable_input = replace(report.inputs[0], readonly=False)
    failing = RuntimeInputManifestReport(
        graph_name=report.graph_name,
        expected_inputs=report.expected_inputs,
        inputs=(mutable_input, *report.inputs[1:]),
        issues=(
            RuntimeInputManifestIssue(
                tensor_name=mutable_input.tensor_name,
                issue_code="record_value_mutable",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "record_value_mutable"


def test_runtime_input_manifest_rejects_raw_value_status() -> None:
    with pytest.raises(ValueError, match="omit raw values"):
        RuntimeInputRecord(
            tensor_name="lhs",
            shape=(2, 3),
            dtype="float64",
            value_role="input",
            producer_kind="external_input",
            producer_id="lhs",
            readonly=True,
            raw_value_status="included",
        )


def test_runtime_input_manifest_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeInputRecord(
            tensor_name="python_source",
            shape=(2, 3),
            dtype="float64",
            value_role="input",
            producer_kind="external_input",
            producer_id="python_source",
            readonly=True,
        )


def test_runtime_input_manifest_records_provenance_mismatch_as_issue() -> None:
    report = build_input_manifest_report()
    bad_input = replace(report.inputs[0], producer_id="other_input")
    failing = RuntimeInputManifestReport(
        graph_name=report.graph_name,
        expected_inputs=report.expected_inputs,
        inputs=(bad_input, *report.inputs[1:]),
        issues=(
            RuntimeInputManifestIssue(
                tensor_name=bad_input.tensor_name,
                issue_code="producer_id_mismatch",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "producer_id_mismatch"


def test_runtime_input_manifest_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/runtime_input_manifest_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_INPUT_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS
    )
    assert schema["properties"]["manifest_contract"]["const"] == (
        RUNTIME_INPUT_MANIFEST_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["input_contract"]["const"] == (
        TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT
    )
    assert schema["properties"]["store_contract"]["const"] == (
        RUNTIME_TENSOR_STORE_CONTRACT
    )
    assert schema["properties"]["value_record_contract"]["const"] == (
        RUNTIME_VALUE_RECORD_CONTRACT
    )
    assert schema["properties"]["external_input_policy"]["const"] == (
        RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["inputs"]["maxItems"] == (
        MAX_RUNTIME_INPUT_MANIFEST_INPUTS
    )
    assert schema["properties"]["expected_inputs"]["minItems"] == 1
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_input_manifest_schema_fails_closed() -> None:
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
        "input_value",
        "raw_benchmark_output",
        "raw_tensor_value",
        "tensor_values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["expected_input"]["properties"]
        assert forbidden not in schema["$defs"]["input_record"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "source_text" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_input_manifest_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_INPUT_MANIFEST_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS
    assert golden["manifest_contract"] == RUNTIME_INPUT_MANIFEST_CONTRACT
    assert golden["input_contract"] == TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT
    assert golden["external_input_policy"] == RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["expected_input_count"] == len(golden["expected_inputs"]) == 2
    assert golden["input_count"] == len(golden["inputs"]) == 2
    assert golden["inputs"][0]["tensor_name"] == "lhs"
    assert golden["inputs"][0]["producer_kind"] == "external_input"
    assert golden["inputs"][0]["producer_id"] == "lhs"
    assert golden["inputs"][0]["raw_value_status"] == "omitted_by_policy"
    assert golden["inputs"][0]["readonly"] is True


def test_runtime_input_manifest_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_input_manifest_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_INPUT_MANIFEST.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0124-runtime-input-manifest.md"),
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
