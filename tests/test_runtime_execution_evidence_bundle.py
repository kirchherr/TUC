from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_execution_evidence_bundle import (
    build_execution_evidence_bundle_report,
)
from tuc import (
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeExecutionEvidenceBundleIssue,
    RuntimeExecutionEvidenceBundleReport,
    RuntimeExecutionReceiptReport,
    assert_runtime_execution_evidence_bundle,
    dump_runtime_execution_evidence_bundle_report,
    runtime_execution_evidence_bundle_report_to_dict,
)
from tuc.runtime import MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ISSUES

GOLDEN_PATH = Path(
    "tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json"
)
SCHEMA_PATH = Path("schemas/runtime_execution_evidence_bundle_report.v0.schema.json")


def test_runtime_execution_evidence_bundle_passes_for_execution_proof() -> None:
    report = build_execution_evidence_bundle_report()

    assert report.bundle_contract == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT
    assert report.artifact_status == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS
    assert report.linkage_policy == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY
    assert report.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert report.report_sections == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS
    assert report.graph_name == "proof_of_execution"
    assert report.passed
    assert report.issues == ()
    assert report.tensor_store_report.graph_name == report.graph_name
    assert report.input_manifest_report.graph_name == report.graph_name
    assert report.output_manifest_report.graph_name == report.graph_name
    assert report.reference_correctness_report.graph_name == report.graph_name
    assert report.execution_receipt_report.graph_name == report.graph_name
    assert tuple(runtime_execution_evidence_bundle_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "bundle_contract",
        "bundle_metadata_digest",
        "execution_receipt",
        "graph_name",
        "input_manifest",
        "issues",
        "linkage_policy",
        "output_manifest",
        "passed",
        "raw_value_policy",
        "reference_correctness",
        "report_sections",
        "schema_version",
        "tensor_store_evidence",
    )


def test_runtime_execution_evidence_bundle_dump_matches_golden() -> None:
    assert dump_runtime_execution_evidence_bundle_report(
        build_execution_evidence_bundle_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_execution_evidence_bundle_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_execution_evidence_bundle.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "python_source" not in completed.stdout


def test_runtime_execution_evidence_bundle_assertion_returns_report() -> None:
    assert assert_runtime_execution_evidence_bundle(
        build_execution_evidence_bundle_report()
    ).passed


def test_runtime_execution_evidence_bundle_issues_must_be_derived() -> None:
    report = build_execution_evidence_bundle_report()
    bad_receipt = _receipt_with_forged_input_manifest_digest(report)

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeExecutionEvidenceBundleReport(
            graph_name=report.graph_name,
            tensor_store_report=report.tensor_store_report,
            input_manifest_report=report.input_manifest_report,
            output_manifest_report=report.output_manifest_report,
            reference_correctness_report=report.reference_correctness_report,
            execution_receipt_report=bad_receipt,
            issues=(),
        )


def test_runtime_execution_evidence_bundle_records_receipt_mismatch() -> None:
    report = build_execution_evidence_bundle_report()
    bad_receipt = _receipt_with_forged_input_manifest_digest(report)
    failing = RuntimeExecutionEvidenceBundleReport(
        graph_name=report.graph_name,
        tensor_store_report=report.tensor_store_report,
        input_manifest_report=report.input_manifest_report,
        output_manifest_report=report.output_manifest_report,
        reference_correctness_report=report.reference_correctness_report,
        execution_receipt_report=bad_receipt,
        issues=(
            RuntimeExecutionEvidenceBundleIssue(
                section="input_manifest",
                issue_code="metadata_digest_mismatch",
            ),
        ),
    )

    assert not failing.passed
    assert failing.issues[0].section == "input_manifest"
    assert failing.issues[0].issue_code == "metadata_digest_mismatch"


def test_runtime_execution_evidence_bundle_rejects_forbidden_surface_names() -> None:
    report = build_execution_evidence_bundle_report()

    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeExecutionEvidenceBundleReport(
            graph_name="python_source",
            tensor_store_report=report.tensor_store_report,
            input_manifest_report=report.input_manifest_report,
            output_manifest_report=report.output_manifest_report,
            reference_correctness_report=report.reference_correctness_report,
            execution_receipt_report=report.execution_receipt_report,
            issues=(),
        )


def test_runtime_execution_evidence_bundle_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_execution_evidence_bundle_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS
    )
    assert schema["properties"]["bundle_contract"]["const"] == (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT
    )
    assert schema["properties"]["linkage_policy"]["const"] == (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["report_sections"]["const"] == list(
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ISSUES
    )
    assert schema["properties"]["tensor_store_evidence"]["$ref"] == (
        "runtime_tensor_store_evidence_report.v0.schema.json"
    )
    assert schema["properties"]["input_manifest"]["$ref"] == (
        "runtime_input_manifest_report.v0.schema.json"
    )
    assert schema["properties"]["output_manifest"]["$ref"] == (
        "runtime_output_manifest_report.v0.schema.json"
    )
    assert schema["properties"]["reference_correctness"]["$ref"] == (
        "runtime_reference_correctness_report.v0.schema.json"
    )
    assert schema["properties"]["execution_receipt"]["$ref"] == (
        "runtime_execution_receipt_report.v0.schema.json"
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_execution_evidence_bundle_schema_fails_closed() -> None:
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
        "value",
        "values",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "tensor_values" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_execution_evidence_bundle_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS
    assert golden["bundle_contract"] == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT
    assert golden["linkage_policy"] == RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["report_sections"] == list(RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS)
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["graph_name"] == "proof_of_execution"
    assert golden["tensor_store_evidence"]["graph_name"] == golden["graph_name"]
    assert golden["input_manifest"]["graph_name"] == golden["graph_name"]
    assert golden["output_manifest"]["graph_name"] == golden["graph_name"]
    assert golden["reference_correctness"]["graph_name"] == golden["graph_name"]
    assert golden["execution_receipt"]["graph_name"] == golden["graph_name"]


def test_runtime_execution_evidence_bundle_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_execution_evidence_bundle_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md"),
        Path("docs/RUNTIME_EVIDENCE_MATRIX.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0129-runtime-execution-evidence-bundle.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _receipt_with_forged_input_manifest_digest(
    report: RuntimeExecutionEvidenceBundleReport,
) -> RuntimeExecutionReceiptReport:
    bad_input_link = replace(
        report.execution_receipt_report.evidence_links[1],
        metadata_digest="sha256:" + "1" * 64,
    )
    return RuntimeExecutionReceiptReport(
        graph_name=report.execution_receipt_report.graph_name,
        evidence_links=(
            report.execution_receipt_report.evidence_links[0],
            bad_input_link,
            *report.execution_receipt_report.evidence_links[2:],
        ),
        operations=report.execution_receipt_report.operations,
        issues=(),
    )


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
