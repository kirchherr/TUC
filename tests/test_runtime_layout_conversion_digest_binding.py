from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_hs_ir_plan_alignment import build_alignment_report
from examples.runtime_layout_conversion_digest_binding import (
    build_current_runtime_layout_conversion_digest_binding_report,
)
from examples.runtime_layout_conversion_evidence import (
    build_current_runtime_layout_conversion_evidence_report,
)
from examples.runtime_mixed_tensor_store_evidence import (
    build_mixed_tensor_store_evidence_report,
)
from tuc import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES, LayoutKind
from tuc.runtime.layout_conversion_digest_binding import (
    MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ISSUES,
    MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ROWS,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE,
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_STATUSES,
    RuntimeLayoutConversionDigestBindingError,
    assert_runtime_layout_conversion_digest_binding,
    build_runtime_layout_conversion_digest_binding_report,
    dump_runtime_layout_conversion_digest_binding_report,
)
from tuc.runtime.tensor_store_evidence import (
    RuntimeTensorStoreEvidenceIssue,
    RuntimeTensorStoreEvidenceReport,
)

SCHEMA_PATH = Path(
    "schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/runtime_layout_conversion_digest_binding/current_report.json"
)


def test_runtime_layout_conversion_digest_binding_passes() -> None:
    report = build_current_runtime_layout_conversion_digest_binding_report()

    assert report.passed is True
    assert report.binding_contract == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT
    assert report.artifact_status == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS
    )
    assert report.artifact_id == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
    assert report.binding_scope == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE
    assert report.graph_name == "runtime_mixed_backend_equivalence"
    assert report.source_hs_ir_graph_name == report.graph_name
    assert report.source_tensor_store_graph_name == report.graph_name
    assert report.source_layout_conversion_count == 1
    assert report.source_hs_ir_layout_conversion_count == 1
    assert report.source_layout_conversion_total_planned_bytes == 24
    assert report.source_hs_ir_total_layout_conversion_bytes == 24
    assert report.source_tensor_store_record_count == 6
    assert report.issues == ()
    assert len(report.bindings) == 1

    row = report.bindings[0]
    assert row.binding_status == "bound"
    assert row.issue_code == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE
    assert row.conversion_id == "layout_conversion_0000"
    assert row.tensor_name == "projection"
    assert row.source_operation == "projection"
    assert row.target_operation == "normalize"
    assert row.layout_conversion_from_backend == "systolic-sim"
    assert row.layout_conversion_to_backend == "vector-sim"
    assert row.layout_conversion_from_layout == "blocked"
    assert row.layout_conversion_to_layout == "row_major"
    assert row.hs_ir_source_backend == "systolic-sim"
    assert row.hs_ir_target_backend == "vector-sim"
    assert row.hs_ir_source_layout == "blocked"
    assert row.hs_ir_target_layout == "row_major"
    assert row.hs_ir_target_layout_conversion_bytes == 24
    assert row.tensor_store_source_backend == "systolic-sim"
    assert row.tensor_store_source_layout == "blocked"
    assert row.tensor_store_source_memory_domain == "device_sram"
    assert row.tensor_store_source_producer_id == "projection"
    assert assert_runtime_layout_conversion_digest_binding(report) is report


def test_runtime_layout_conversion_digest_binding_dump_matches_golden() -> None:
    report = build_current_runtime_layout_conversion_digest_binding_report()

    assert dump_runtime_layout_conversion_digest_binding_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_layout_conversion_digest_binding_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_layout_conversion_digest_binding.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "runtime_layout_conversion_digest_binding.data_only.v0" in (
        completed.stdout
    )
    assert '"passed": true' in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_layout_conversion_digest_binding_records_graph_mismatch() -> None:
    layout_conversion = build_current_runtime_layout_conversion_evidence_report()
    tensor_store = replace(
        build_mixed_tensor_store_evidence_report(),
        graph_name="other_runtime_graph",
    )
    report = build_runtime_layout_conversion_digest_binding_report(
        layout_conversion,
        build_alignment_report(),
        tensor_store,
    )

    assert report.passed is False
    assert ("graph", "tensor_store_graph_mismatch") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }
    with pytest.raises(RuntimeLayoutConversionDigestBindingError):
        assert_runtime_layout_conversion_digest_binding(report)


def test_runtime_layout_conversion_digest_binding_records_tensor_store_mismatch() -> None:
    layout_conversion = build_current_runtime_layout_conversion_evidence_report()
    hs_ir_alignment = build_alignment_report()
    tensor_store = build_mixed_tensor_store_evidence_report()
    bad_records = tuple(
        replace(record, planned_layout=LayoutKind.ROW_MAJOR)
        if record.tensor_name == "projection"
        else record
        for record in tensor_store.records
    )
    failing_store = RuntimeTensorStoreEvidenceReport(
        graph_name=tensor_store.graph_name,
        expected_records=tensor_store.expected_records,
        records=bad_records,
        issues=(
            RuntimeTensorStoreEvidenceIssue(
                tensor_name="projection",
                issue_code="planned_layout_mismatch",
            ),
        ),
    )

    report = build_runtime_layout_conversion_digest_binding_report(
        layout_conversion,
        hs_ir_alignment,
        failing_store,
    )

    assert report.passed is False
    assert ("source_tensor_store", "source_report_failed") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }
    assert ("layout_conversion_0000", "tensor_store_source_layout_mismatch") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }


def test_runtime_layout_conversion_digest_binding_rejects_forged_issues() -> None:
    report = build_current_runtime_layout_conversion_digest_binding_report()
    bad_row = replace(
        report.bindings[0],
        hs_ir_source_layout="row_major",
        binding_status="failed",
        issue_code="hs_ir_source_layout_mismatch",
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        replace(report, bindings=(bad_row,), issues=())


def test_runtime_layout_conversion_digest_binding_rejects_forbidden_text() -> None:
    report = build_current_runtime_layout_conversion_digest_binding_report()

    with pytest.raises(ValueError, match="forbidden execution"):
        replace(report.bindings[0], conversion_id="runtime_handle")


def test_runtime_layout_conversion_digest_binding_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS
    )
    assert schema["properties"]["artifact_id"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
    )
    assert schema["properties"]["binding_contract"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT
    )
    assert schema["properties"]["binding_scope"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE
    )
    assert schema["properties"]["bindings"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ROWS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ISSUES
    )
    assert schema["$defs"]["binding"]["properties"]["binding_status"]["enum"] == list(
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_STATUSES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_layout_conversion_digest_binding_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "device_pointer",
        "memory_address",
        "runtime_handle",
        "allocation_handle",
        "subprocess",
        "raw_tensor_value",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["binding"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_layout_conversion_digest_binding_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_SCHEMA_VERSION
    )
    assert golden["artifact_status"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS
    )
    assert golden["artifact_id"] == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
    assert golden["binding_contract"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT
    )
    assert golden["binding_scope"] == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["binding_count"] == len(golden["bindings"]) == 1
    assert golden["bindings"][0]["binding_status"] == "bound"
    assert golden["bindings"][0]["issue_code"] == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE
    )


def test_runtime_layout_conversion_digest_binding_schema_is_referenced() -> None:
    schema_path = (
        "schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json"
    )

    for path in (
        Path("docs/RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING.md"),
        Path("docs/RUNTIME_LAYOUT_CONVERSION_GATE_READINESS.md"),
        Path("docs/RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0214-runtime-layout-conversion-digest-binding.md"),
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
