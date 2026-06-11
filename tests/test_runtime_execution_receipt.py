from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_execution_receipt import build_execution_receipt_report
from tuc import (
    RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS,
    RUNTIME_EXECUTION_RECEIPT_CONTRACT,
    RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY,
    RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeExecutionReceiptEvidenceLink,
    RuntimeExecutionReceiptIssue,
    RuntimeExecutionReceiptReport,
    assert_runtime_execution_receipt,
    dump_runtime_execution_receipt_report,
    runtime_execution_receipt_report_to_dict,
)
from tuc.runtime import (
    MAX_RUNTIME_EXECUTION_RECEIPT_EVIDENCE_LINKS,
    MAX_RUNTIME_EXECUTION_RECEIPT_OPERATIONS,
)

GOLDEN_PATH = Path("tests/golden/runtime_execution_receipt/proof_of_execution.json")
SCHEMA_PATH = Path("schemas/runtime_execution_receipt_report.v0.schema.json")


def test_runtime_execution_receipt_passes_for_execution_proof() -> None:
    report = build_execution_receipt_report()

    assert report.receipt_contract == RUNTIME_EXECUTION_RECEIPT_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.linkage_policy == RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY
    assert report.passed
    assert report.issues == ()
    assert tuple(link.evidence_kind for link in report.evidence_links) == (
        RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS
    )
    assert tuple(operation.operation_name for operation in report.operations) == (
        "linear_projection",
        "row_reduction",
        "activation",
    )
    assert report.operations[0].planned_backend == "linear-sim"
    assert report.operations[0].executor_backend == "linear-sim"
    assert report.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert tuple(runtime_execution_receipt_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "evidence_link_count",
        "evidence_links",
        "execution_trace_metadata_digest",
        "executor_contract",
        "graph_name",
        "issues",
        "linkage_policy",
        "operation_count",
        "operations",
        "passed",
        "raw_value_policy",
        "receipt_contract",
        "receipt_metadata_digest",
        "required_evidence_kinds",
        "schema_version",
    )


def test_runtime_execution_receipt_dump_matches_golden() -> None:
    assert dump_runtime_execution_receipt_report(build_execution_receipt_report()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_execution_receipt_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_execution_receipt.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_execution_receipt.data_only.v0" in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout


def test_runtime_execution_receipt_assertion_returns_report() -> None:
    assert assert_runtime_execution_receipt(build_execution_receipt_report()).passed


def test_runtime_execution_receipt_issues_must_be_derived() -> None:
    report = build_execution_receipt_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeExecutionReceiptReport(
            graph_name=report.graph_name,
            evidence_links=report.evidence_links[:-1],
            operations=report.operations,
            issues=(),
        )


def test_runtime_execution_receipt_records_failed_evidence_as_issue() -> None:
    report = build_execution_receipt_report()
    failed_link = replace(report.evidence_links[1], passed=False)
    failing = RuntimeExecutionReceiptReport(
        graph_name=report.graph_name,
        evidence_links=(
            report.evidence_links[0],
            failed_link,
            *report.evidence_links[2:],
        ),
        operations=report.operations,
        issues=(
            RuntimeExecutionReceiptIssue(
                evidence_kind=failed_link.evidence_kind,
                issue_code="evidence_not_passed",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "evidence_not_passed"


def test_runtime_execution_receipt_records_graph_mismatch_as_issue() -> None:
    report = build_execution_receipt_report()
    bad_link = replace(report.evidence_links[0], graph_name="other_graph")
    failing = RuntimeExecutionReceiptReport(
        graph_name=report.graph_name,
        evidence_links=(bad_link, *report.evidence_links[1:]),
        operations=report.operations,
        issues=(
            RuntimeExecutionReceiptIssue(
                evidence_kind=bad_link.evidence_kind,
                issue_code="graph_name_mismatch",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].issue_code == "graph_name_mismatch"


def test_runtime_execution_receipt_rejects_raw_value_policy() -> None:
    with pytest.raises(ValueError, match="omit raw values"):
        RuntimeExecutionReceiptEvidenceLink(
            evidence_kind="input_manifest",
            graph_name="proof_of_execution",
            evidence_contract="runtime_input_manifest.data_only.v0",
            metadata_digest="sha256:" + "0" * 64,
            item_count=1,
            passed=True,
            raw_value_policy="included",
        )


def test_runtime_execution_receipt_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeExecutionReceiptEvidenceLink(
            evidence_kind="python_source",
            graph_name="proof_of_execution",
            evidence_contract="runtime_input_manifest.data_only.v0",
            metadata_digest="sha256:" + "0" * 64,
            item_count=1,
            passed=True,
        )


def test_runtime_execution_receipt_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_execution_receipt_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS
    )
    assert schema["properties"]["receipt_contract"]["const"] == (
        RUNTIME_EXECUTION_RECEIPT_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["linkage_policy"]["const"] == (
        RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["required_evidence_kinds"]["const"] == list(
        RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS
    )
    assert schema["properties"]["evidence_links"]["maxItems"] == (
        MAX_RUNTIME_EXECUTION_RECEIPT_EVIDENCE_LINKS
    )
    assert schema["properties"]["operations"]["maxItems"] == (
        MAX_RUNTIME_EXECUTION_RECEIPT_OPERATIONS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_execution_receipt_schema_fails_closed() -> None:
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
        "output_value",
        "reference_value",
        "raw_benchmark_output",
        "raw_tensor_value",
        "tensor_values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["evidence_link"]["properties"]
        assert forbidden not in schema["$defs"]["operation"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "source_text" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_execution_receipt_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS
    assert golden["receipt_contract"] == RUNTIME_EXECUTION_RECEIPT_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["linkage_policy"] == RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["required_evidence_kinds"] == list(
        RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS
    )
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["evidence_link_count"] == len(golden["evidence_links"]) == 4
    assert golden["operation_count"] == len(golden["operations"]) == 3
    assert golden["evidence_links"][0]["evidence_kind"] == "tensor_store_evidence"
    assert golden["operations"][0]["operation_name"] == "linear_projection"


def test_runtime_execution_receipt_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_execution_receipt_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_EXECUTION_RECEIPT.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/RUNTIME_EVIDENCE_MATRIX.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0126-runtime-execution-receipt.md"),
        Path("rfcs/0127-runtime-evidence-matrix-execution-receipt.md"),
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
