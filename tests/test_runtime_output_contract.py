from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_multi_output_evidence import run_evidence
from examples.runtime_output_contract import build_output_contract_report
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY,
    RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS,
    RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION,
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeOutputAlias,
    RuntimeOutputContractIssue,
    RuntimeOutputContractReport,
    RuntimePublicOutput,
    assert_runtime_output_contract,
    build_runtime_output_contract_report,
    dump_runtime_output_contract_report,
    runtime_output_contract_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES

GOLDEN_PATH = Path("tests/golden/runtime_output_contract/current_report.json")
SCHEMA_PATH = Path("schemas/runtime_output_contract_report.v0.schema.json")


def test_runtime_output_contract_passes_for_multi_output_fixture() -> None:
    report = build_output_contract_report()

    assert report.output_contract == RUNTIME_OUTPUT_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.output_manifest_contract == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert report.alias_policy == RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY
    assert report.output_manifest_passed is True
    assert report.passed
    assert report.issues == ()
    assert tuple(alias.public_name for alias in report.aliases) == (
        "api_positive_projection",
        "api_row_sums",
    )
    assert tuple(alias.tensor_name for alias in report.aliases) == (
        "positive_projection",
        "row_sum",
    )
    assert report.terminal_tensor_names == ("row_sum", "positive_projection")
    assert tuple(output.public_name for output in report.public_outputs) == (
        "api_positive_projection",
        "api_row_sums",
    )
    assert tuple(output.tensor_name for output in report.public_outputs) == (
        "positive_projection",
        "row_sum",
    )
    assert tuple(runtime_output_contract_report_to_dict(report)) == (
        "alias_count",
        "alias_policy",
        "aliases",
        "artifact_status",
        "available_tensor_names",
        "blocked_execution_surfaces",
        "contract_metadata_digest",
        "executor_contract",
        "graph_name",
        "issues",
        "output_contract",
        "output_manifest_contract",
        "output_manifest_passed",
        "passed",
        "public_output_count",
        "public_outputs",
        "raw_value_policy",
        "schema_version",
        "terminal_output_policy",
        "terminal_tensor_names",
    )


def test_runtime_output_contract_dump_matches_golden() -> None:
    assert dump_runtime_output_contract_report(build_output_contract_report()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_output_contract_example_runs_without_raw_values() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_output_contract.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_output_contract.data_only.v0" in completed.stdout
    assert '"alias_policy": "explicit_output_aliases"' in completed.stdout
    assert '"public_name": "api_row_sums"' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_output_contract_assertion_returns_report() -> None:
    assert assert_runtime_output_contract(build_output_contract_report()).passed


def test_runtime_output_contract_rejects_non_plain_alias_mapping() -> None:
    class CustomAliases(dict[str, str]):
        pass

    evidence = run_evidence()

    with pytest.raises(TypeError, match="plain dict"):
        build_runtime_output_contract_report(
            evidence.graph,
            evidence.execution,
            CustomAliases({"api_row_sums": "row_sum"}),
        )


def test_runtime_output_contract_records_missing_alias() -> None:
    evidence = run_evidence()
    report = build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        {"api_row_sums": "row_sum"},
    )

    assert not report.passed
    assert RuntimeOutputContractIssue(
        public_name="unbound",
        tensor_name="positive_projection",
        issue_code="terminal_output_unbound",
    ) in report.issues


def test_runtime_output_contract_records_non_terminal_alias_target() -> None:
    evidence = run_evidence()
    report = build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        {
            "api_positive_projection": "positive_projection",
            "api_projection": "projection",
            "api_row_sums": "row_sum",
        },
    )

    assert not report.passed
    assert RuntimeOutputContractIssue(
        public_name="api_projection",
        tensor_name="projection",
        issue_code="alias_target_not_terminal",
    ) in report.issues


def test_runtime_output_contract_records_duplicate_tensor_binding() -> None:
    evidence = run_evidence()
    report = build_runtime_output_contract_report(
        evidence.graph,
        evidence.execution,
        {
            "api_row_sums": "row_sum",
            "api_row_sums_copy": "row_sum",
        },
    )

    assert not report.passed
    assert RuntimeOutputContractIssue(
        public_name="api_row_sums",
        tensor_name="row_sum",
        issue_code="duplicate_tensor_binding",
    ) in report.issues
    assert RuntimeOutputContractIssue(
        public_name="unbound",
        tensor_name="positive_projection",
        issue_code="terminal_output_unbound",
    ) in report.issues


def test_runtime_output_contract_issues_must_be_derived() -> None:
    report = build_output_contract_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeOutputContractReport(
            graph_name=report.graph_name,
            aliases=report.aliases[:-1],
            terminal_tensor_names=report.terminal_tensor_names,
            available_tensor_names=report.available_tensor_names,
            public_outputs=report.public_outputs[:-1],
            output_manifest_passed=report.output_manifest_passed,
            issues=(),
        )


def test_runtime_output_contract_rejects_raw_value_status() -> None:
    with pytest.raises(ValueError, match="omit raw values"):
        RuntimePublicOutput(
            public_name="api_row_sums",
            tensor_name="row_sum",
            shape=(2,),
            dtype="float64",
            value_role="computed",
            producer_kind="operation",
            producer_id="row_reduction",
            raw_value_status="included",
        )


def test_runtime_output_contract_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeOutputAlias(
            public_name="python_source",
            tensor_name="row_sum",
        )


def test_runtime_output_contract_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_output_contract_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS
    )
    assert schema["properties"]["output_contract"]["const"] == RUNTIME_OUTPUT_CONTRACT
    assert schema["properties"]["output_manifest_contract"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["alias_policy"]["const"] == (
        RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY
    )
    assert schema["properties"]["terminal_output_policy"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["aliases"]["maxItems"] == (
        MAX_RUNTIME_OUTPUT_CONTRACT_ALIASES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_output_contract_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["output_alias"]["properties"]
        assert forbidden not in schema["$defs"]["public_output"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "tensor_values" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_output_contract_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_OUTPUT_CONTRACT_ARTIFACT_STATUS
    assert golden["output_contract"] == RUNTIME_OUTPUT_CONTRACT
    assert golden["output_manifest_contract"] == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["alias_policy"] == RUNTIME_OUTPUT_CONTRACT_ALIAS_POLICY
    assert golden["terminal_output_policy"] == RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["alias_count"] == len(golden["aliases"]) == 2
    assert golden["public_output_count"] == len(golden["public_outputs"]) == 2
    assert golden["aliases"][0]["public_name"] == "api_positive_projection"
    assert golden["aliases"][0]["tensor_name"] == "positive_projection"
    assert golden["public_outputs"][0]["raw_value_status"] == "omitted_by_policy"
    assert golden["terminal_tensor_names"] == ["row_sum", "positive_projection"]


def test_runtime_output_contract_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_output_contract_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_OUTPUT_CONTRACT.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0112-runtime-output-contract.md"),
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
