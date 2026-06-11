from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from examples.runtime_multi_output_evidence import run_evidence
from examples.runtime_public_output_bundle import build_public_output_bundle
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_VALUE_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RUNTIME_VALUE_RECORD_CONTRACT,
    RuntimePublicOutputBundleError,
    RuntimePublicOutputValue,
    assert_runtime_public_output_bundle,
    build_runtime_output_contract_report,
    build_runtime_public_output_bundle,
    dump_runtime_public_output_bundle_report,
    runtime_public_output_bundle_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_OUTPUTS

GOLDEN_PATH = Path("tests/golden/runtime_public_output_bundle/current_report.json")
SCHEMA_PATH = Path("schemas/runtime_public_output_bundle_report.v0.schema.json")


def test_runtime_public_output_bundle_resolves_public_values() -> None:
    bundle = build_public_output_bundle()

    assert bundle.bundle_contract == RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    assert bundle.output_contract == RUNTIME_OUTPUT_CONTRACT
    assert bundle.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert bundle.artifact_status == RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS
    assert bundle.passed
    assert bundle.public_output_names == (
        "api_positive_projection",
        "api_row_sums",
    )
    assert bundle.tensor_names == ("positive_projection", "row_sum")

    values = bundle.values
    assert tuple(values) == ("api_positive_projection", "api_row_sums")
    np.testing.assert_allclose(
        values["api_positive_projection"],
        np.array([[0.0, 0.0], [4.0, 0.0]], dtype=np.float64),
    )
    np.testing.assert_allclose(
        bundle.value_for("api_row_sums"),
        np.array([-4.0, 1.75], dtype=np.float64),
    )
    assert not values["api_positive_projection"].flags.writeable
    assert not values["api_row_sums"].flags.writeable
    with pytest.raises(TypeError):
        values["api_extra"] = bundle.value_for("api_row_sums")
    with pytest.raises(ValueError):
        values["api_row_sums"][0] = 0.0

    assert tuple(runtime_public_output_bundle_report_to_dict(bundle)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "bundle_contract",
        "bundle_metadata_digest",
        "executor_contract",
        "graph_name",
        "output_contract",
        "passed",
        "public_output_count",
        "public_output_names",
        "public_outputs",
        "raw_value_policy",
        "schema_version",
        "tensor_names",
    )


def test_runtime_public_output_bundle_dump_matches_golden() -> None:
    assert dump_runtime_public_output_bundle_report(build_public_output_bundle()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_public_output_bundle_example_runs_without_raw_values() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_public_output_bundle.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["bundle_contract"] == RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    assert payload["passed"] is True
    assert payload["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert all(output["readonly"] is True for output in payload["public_outputs"])
    _assert_forbidden_keys_absent(payload)
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_values" not in completed.stdout
    assert "python_source" not in completed.stdout


def test_runtime_public_output_bundle_assertion_returns_bundle() -> None:
    assert assert_runtime_public_output_bundle(build_public_output_bundle()).passed


def test_runtime_public_output_bundle_rejects_failed_output_contract() -> None:
    evidence = run_evidence()
    output_contract = build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        {"api_row_sums": "row_sum"},
    )

    with pytest.raises(RuntimePublicOutputBundleError, match="output contract failed"):
        build_runtime_public_output_bundle(evidence.execution, output_contract)


def test_runtime_public_output_bundle_rejects_graph_mismatch() -> None:
    evidence = run_evidence()
    output_contract = build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        {
            "api_positive_projection": "positive_projection",
            "api_row_sums": "row_sum",
        },
    )
    mismatched_contract = replace(output_contract, graph_name="other_graph")

    with pytest.raises(RuntimePublicOutputBundleError, match="graph name mismatch"):
        build_runtime_public_output_bundle(evidence.execution, mismatched_contract)


def test_runtime_public_output_value_copies_and_freezes() -> None:
    raw = np.array([1.0, 2.0], dtype=np.float64)
    output = RuntimePublicOutputValue(
        public_name="api_row_sums",
        tensor_name="row_sum",
        value=raw,
        shape=(2,),
        dtype="float64",
        value_role="computed",
        producer_kind="operation",
        producer_id="row_reduction",
    )

    raw[0] = 99.0

    assert output.readonly
    np.testing.assert_allclose(output.value, np.array([1.0, 2.0], dtype=np.float64))
    with pytest.raises(ValueError):
        output.value[0] = 0.0


def test_runtime_public_output_value_rejects_raw_value_status() -> None:
    with pytest.raises(ValueError, match="omit raw values"):
        RuntimePublicOutputValue(
            public_name="api_row_sums",
            tensor_name="row_sum",
            value=np.array([1.0, 2.0], dtype=np.float64),
            shape=(2,),
            dtype="float64",
            value_role="computed",
            producer_kind="operation",
            producer_id="row_reduction",
            raw_value_status="included",
        )


def test_runtime_public_output_value_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimePublicOutputValue(
            public_name="python_source",
            tensor_name="row_sum",
            value=np.array([1.0, 2.0], dtype=np.float64),
            shape=(2,),
            dtype="float64",
            value_role="computed",
            producer_kind="operation",
            producer_id="row_reduction",
        )


def test_runtime_public_output_bundle_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_public_output_bundle_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS
    )
    assert schema["properties"]["bundle_contract"]["const"] == (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    )
    assert schema["properties"]["output_contract"]["const"] == RUNTIME_OUTPUT_CONTRACT
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["public_outputs"]["maxItems"] == (
        MAX_RUNTIME_PUBLIC_OUTPUT_BUNDLE_OUTPUTS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_public_output_bundle_schema_fails_closed() -> None:
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
        "tensor_values",
        "value",
        "values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["public_output"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "tensor_values" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_public_output_bundle_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_PUBLIC_OUTPUT_BUNDLE_ARTIFACT_STATUS
    assert golden["bundle_contract"] == RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    assert golden["output_contract"] == RUNTIME_OUTPUT_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["public_output_count"] == len(golden["public_outputs"]) == 2
    assert golden["public_output_names"] == [
        "api_positive_projection",
        "api_row_sums",
    ]
    assert golden["tensor_names"] == ["positive_projection", "row_sum"]
    assert golden["public_outputs"][0]["readonly"] is True
    assert golden["public_outputs"][0]["value_contract"] == (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_VALUE_CONTRACT
    )
    assert golden["public_outputs"][0]["record_contract"] == RUNTIME_VALUE_RECORD_CONTRACT
    assert "value" not in golden["public_outputs"][0]


def test_runtime_public_output_bundle_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_public_output_bundle_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0114-runtime-public-output-bundle.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_forbidden_keys_absent(value: object) -> None:
    forbidden_keys = {
        "file_path",
        "generated_code",
        "host_path",
        "python_source",
        "raw_output_value",
        "raw_tensor_value",
        "source_text",
        "tensor_value",
        "tensor_values",
        "value",
        "values",
    }
    if isinstance(value, dict):
        assert not (set(value) & forbidden_keys)
        for item in value.values():
            _assert_forbidden_keys_absent(item)
    elif isinstance(value, list):
        for item in value:
            _assert_forbidden_keys_absent(item)


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
