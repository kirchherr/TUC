from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_execution_output_closure import (
    build_execution_output_closure_report,
)
from examples.runtime_execution_receipt import build_execution_receipt_evidence_reports
from tuc import (
    MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECKS,
    MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_ISSUES,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeExecutionOutputClosureIssue,
    RuntimeExecutionOutputClosureReport,
    RuntimeExecutionReceiptReport,
    assert_runtime_execution_output_closure,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_output_closure_report,
    build_runtime_execution_receipt_report,
    dump_runtime_execution_output_closure_report,
    runtime_execution_output_closure_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/runtime_execution_output_closure/proof_of_execution.json")
SCHEMA_PATH = Path("schemas/runtime_execution_output_closure_report.v0.schema.json")


def test_runtime_execution_output_closure_passes_for_execution_proof() -> None:
    report = build_execution_output_closure_report()

    assert report.closure_contract == RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT
    assert report.closure_policy_id == RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID
    assert report.closure_status == RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS
    assert report.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert report.graph_name == "proof_of_execution"
    assert report.passed
    assert report.issues == ()
    assert tuple(check.evidence_kind for check in report.checks) == (
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS
    )
    assert {check.row_status for check in report.checks} == {
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS
    }
    assert list(runtime_execution_output_closure_report_to_dict(report)) == [
        "blocked_execution_surfaces",
        "check_count",
        "checks",
        "closure_contract",
        "closure_metadata_digest",
        "closure_policy_id",
        "closure_status",
        "graph_name",
        "issues",
        "passed",
        "raw_value_policy",
        "schema_version",
        "source_bundle_execution_receipt_metadata_digest",
        "source_execution_evidence_bundle_metadata_digest",
        "source_execution_evidence_bundle_passed",
        "source_execution_evidence_bundle_schema_version",
        "source_execution_receipt_metadata_digest",
        "source_execution_receipt_passed",
        "source_execution_receipt_schema_version",
        "source_output_contract_item_count",
        "source_output_contract_metadata_digest",
        "source_output_contract_passed",
        "source_output_contract_schema_version",
        "source_public_output_bundle_item_count",
        "source_public_output_bundle_metadata_digest",
        "source_public_output_bundle_passed",
        "source_public_output_bundle_schema_version",
    ]


def test_runtime_execution_output_closure_dump_matches_golden() -> None:
    assert dump_runtime_execution_output_closure_report(
        build_execution_output_closure_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_execution_output_closure_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_execution_output_closure.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "tensor_values" not in completed.stdout


def test_runtime_execution_output_closure_assertion_returns_report() -> None:
    report = build_execution_output_closure_report()

    assert assert_runtime_execution_output_closure(report) is report


def test_runtime_execution_output_closure_detects_forged_receipt_link() -> None:
    evidence = build_execution_receipt_evidence_reports()
    receipt = build_runtime_execution_receipt_report(
        evidence.execution,
        evidence.tensor_store,
        evidence.input_manifest,
        evidence.output_manifest,
        evidence.output_contract,
        evidence.public_output_bundle,
        evidence.reference_correctness,
    )
    forged_output_link = replace(
        receipt.evidence_links[3],
        metadata_digest="sha256:" + "1" * 64,
    )
    forged_receipt = RuntimeExecutionReceiptReport(
        graph_name=receipt.graph_name,
        evidence_links=(
            *receipt.evidence_links[:3],
            forged_output_link,
            *receipt.evidence_links[4:],
        ),
        operations=receipt.operations,
        issues=(),
    )
    bundle = build_runtime_execution_evidence_bundle_report(
        evidence.tensor_store,
        evidence.input_manifest,
        evidence.output_manifest,
        evidence.output_contract,
        evidence.public_output_bundle,
        evidence.reference_correctness,
        forged_receipt,
    )
    report = build_runtime_execution_output_closure_report(
        evidence.output_contract,
        evidence.public_output_bundle,
        forged_receipt,
        bundle,
    )

    assert not report.passed
    assert (
        RuntimeExecutionOutputClosureIssue(
            subject="output_contract",
            issue_code="receipt_metadata_digest_mismatch",
        )
        in report.issues
    )
    assert (
        RuntimeExecutionOutputClosureIssue(
            subject="execution_evidence_bundle",
            issue_code="source_report_failed",
        )
        in report.issues
    )


def test_runtime_execution_output_closure_issues_must_be_derived() -> None:
    report = build_execution_output_closure_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeExecutionOutputClosureReport(
            graph_name=report.graph_name,
            source_output_contract_schema_version=(
                report.source_output_contract_schema_version
            ),
            source_output_contract_metadata_digest=(
                report.source_output_contract_metadata_digest
            ),
            source_output_contract_item_count=report.source_output_contract_item_count,
            source_output_contract_passed=report.source_output_contract_passed,
            source_public_output_bundle_schema_version=(
                report.source_public_output_bundle_schema_version
            ),
            source_public_output_bundle_metadata_digest=(
                report.source_public_output_bundle_metadata_digest
            ),
            source_public_output_bundle_item_count=(
                report.source_public_output_bundle_item_count
            ),
            source_public_output_bundle_passed=(
                report.source_public_output_bundle_passed
            ),
            source_execution_receipt_schema_version=(
                report.source_execution_receipt_schema_version
            ),
            source_execution_receipt_metadata_digest=(
                report.source_execution_receipt_metadata_digest
            ),
            source_execution_receipt_passed=report.source_execution_receipt_passed,
            source_execution_evidence_bundle_schema_version=(
                report.source_execution_evidence_bundle_schema_version
            ),
            source_execution_evidence_bundle_metadata_digest=(
                report.source_execution_evidence_bundle_metadata_digest
            ),
            source_execution_evidence_bundle_passed=(
                report.source_execution_evidence_bundle_passed
            ),
            source_bundle_execution_receipt_metadata_digest=(
                report.source_bundle_execution_receipt_metadata_digest
            ),
            checks=report.checks[:-1],
            issues=(),
        )


def test_runtime_execution_output_closure_rejects_forbidden_surface_names() -> None:
    report = build_execution_output_closure_report()

    with pytest.raises(ValueError, match="forbidden output closure surface"):
        RuntimeExecutionOutputClosureIssue(
            subject="python_source",
            issue_code=report.issues[0].issue_code if report.issues else "issue",
        )


def test_runtime_execution_output_closure_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_execution_output_closure_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["closure_contract"]["const"] == (
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT
    )
    assert schema["properties"]["closure_policy_id"]["const"] == (
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID
    )
    assert schema["properties"]["closure_status"]["const"] == (
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["check_count"]["const"] == (
        MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECKS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_ISSUES
    )
    assert schema["$defs"]["evidence_kind"]["enum"] == list(
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_execution_output_closure_schema_fails_closed() -> None:
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
        "tensor_value",
        "tensor_values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["check"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_execution_output_closure_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION
    assert golden["closure_contract"] == RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT
    assert golden["closure_policy_id"] == RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID
    assert golden["closure_status"] == RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["graph_name"] == "proof_of_execution"
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["check_count"] == len(golden["checks"]) == 2
    assert [check["evidence_kind"] for check in golden["checks"]] == list(
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS
    )


def test_runtime_execution_output_closure_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_execution_output_closure_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_EXECUTION_OUTPUT_CLOSURE.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0205-runtime-execution-output-closure-report.md"),
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
