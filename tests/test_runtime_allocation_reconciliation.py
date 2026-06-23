from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_allocation_reconciliation import (
    build_current_runtime_allocation_reconciliation_report,
)
from tuc import (
    MAX_RUNTIME_ALLOCATION_RECONCILIATION_ISSUES,
    MAX_RUNTIME_ALLOCATION_RECONCILIATION_ROWS,
    RUNTIME_ALLOCATION_ADMISSION_CONTRACT,
    RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE,
    RUNTIME_ALLOCATION_RECEIPT_CONTRACT,
    RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT,
    RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY,
    RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID,
    RUNTIME_ALLOCATION_RECONCILIATION_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_RECONCILIATION_ROW_STATUS,
    RUNTIME_ALLOCATION_RECONCILIATION_STATUS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    MemoryDomainKind,
    RuntimeAllocationReconciliationError,
    RuntimeAllocationReconciliationReport,
    RuntimeAllocationReconciliationRow,
    RuntimeMemoryDomainBudget,
    assert_runtime_allocation_reconciliation,
    build_runtime_allocation_admission_report,
    build_runtime_allocation_receipt_report,
    build_runtime_allocation_reconciliation_report,
    build_runtime_allocation_request_manifest_report,
    build_runtime_memory_budget_report,
    dump_runtime_allocation_reconciliation_report,
    runtime_allocation_reconciliation_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_allocation_reconciliation_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_allocation_reconciliation/current_report.json")


def test_runtime_allocation_reconciliation_report_passes() -> None:
    report = build_current_runtime_allocation_reconciliation_report()

    assert report.passed is True
    assert report.reconciliation_contract == RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT
    assert report.reconciliation_policy_id == RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID
    assert report.reconciliation_status == RUNTIME_ALLOCATION_RECONCILIATION_STATUS
    assert report.allocation_mode == RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    assert report.handle_policy == RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY
    assert report.source_admission_contract == RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    assert report.source_receipt_contract == RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    assert report.row_count == len(report.rows) == 3
    assert report.source_admission_count == report.source_receipt_count == 3
    assert report.total_reconciled_bytes == report.source_admission_total_admitted_bytes
    assert report.total_reconciled_bytes == report.source_receipt_total_receipted_bytes
    assert tuple(row.domain_offset_bytes for row in report.rows) == (0, 64, 128)
    assert {row.row_status for row in report.rows} == {
        RUNTIME_ALLOCATION_RECONCILIATION_ROW_STATUS
    }
    dumped = dump_runtime_allocation_reconciliation_report(report)
    assert "memory_address" not in dumped
    assert "\"runtime_handle\"" not in dumped
    assert list(runtime_allocation_reconciliation_report_to_dict(report)) == [
        "allocation_mode",
        "blocked_execution_surfaces",
        "graph_name",
        "handle_policy",
        "issues",
        "operation_count",
        "passed",
        "reconciliation_contract",
        "reconciliation_metadata_digest",
        "reconciliation_policy_id",
        "reconciliation_status",
        "row_count",
        "rows",
        "schema_version",
        "source_admission_contract",
        "source_admission_count",
        "source_admission_issue_count",
        "source_admission_metadata_digest",
        "source_admission_schema_version",
        "source_admission_total_admitted_bytes",
        "source_receipt_contract",
        "source_receipt_count",
        "source_receipt_issue_count",
        "source_receipt_metadata_digest",
        "source_receipt_schema_version",
        "source_receipt_source_admission_metadata_digest",
        "source_receipt_total_receipted_bytes",
        "total_reconciled_bytes",
    ]


def test_runtime_allocation_reconciliation_dump_matches_golden() -> None:
    report = build_current_runtime_allocation_reconciliation_report()

    assert dump_runtime_allocation_reconciliation_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_allocation_reconciliation_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_allocation_reconciliation.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "runtime_allocation_reconciliation.data_only.v0" in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "\"runtime_handle\"" not in completed.stdout


def test_runtime_allocation_reconciliation_assertion_passes() -> None:
    report = build_current_runtime_allocation_reconciliation_report()

    assert assert_runtime_allocation_reconciliation(report) is report


def test_runtime_allocation_reconciliation_records_failed_sources() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    failed_budget = build_runtime_memory_budget_report(
        allocation,
        (
            RuntimeMemoryDomainBudget(
                budget_id="tiny_host_ram_budget",
                memory_domain=MemoryDomainKind.HOST_RAM,
                max_reserved_bytes=64,
                max_peak_live_bytes=192,
            ),
        ),
    )
    manifest = build_runtime_allocation_request_manifest_report(
        allocation,
        failed_budget,
    )
    admission = build_runtime_allocation_admission_report(manifest, failed_budget)
    receipt = build_runtime_allocation_receipt_report(admission)
    report = build_runtime_allocation_reconciliation_report(admission, receipt)

    assert report.passed is False
    assert report.row_count == 0
    assert "source_allocation_admission_failed" in [
        issue.issue_code for issue in report.issues
    ]
    assert "source_allocation_receipt_failed" in [
        issue.issue_code for issue in report.issues
    ]
    with pytest.raises(
        RuntimeAllocationReconciliationError,
        match="allocation reconciliation failed",
    ):
        assert_runtime_allocation_reconciliation(report)


def test_runtime_allocation_reconciliation_requires_derived_issues() -> None:
    report = build_current_runtime_allocation_reconciliation_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationReconciliationReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            source_admission_contract=report.source_admission_contract,
            source_admission_schema_version=report.source_admission_schema_version,
            source_admission_issue_count=report.source_admission_issue_count,
            source_admission_metadata_digest=report.source_admission_metadata_digest,
            source_admission_count=report.source_admission_count,
            source_admission_total_admitted_bytes=(
                report.source_admission_total_admitted_bytes
            ),
            source_receipt_contract=report.source_receipt_contract,
            source_receipt_schema_version=report.source_receipt_schema_version,
            source_receipt_issue_count=report.source_receipt_issue_count,
            source_receipt_metadata_digest=report.source_receipt_metadata_digest,
            source_receipt_source_admission_metadata_digest=(
                report.source_receipt_source_admission_metadata_digest
            ),
            source_receipt_count=report.source_receipt_count,
            source_receipt_total_receipted_bytes=(
                report.source_receipt_total_receipted_bytes
            ),
            rows=(),
            issues=(),
        )


def test_runtime_allocation_reconciliation_detects_stale_receipt_binding() -> None:
    report = build_current_runtime_allocation_reconciliation_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationReconciliationReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            source_admission_contract=report.source_admission_contract,
            source_admission_schema_version=report.source_admission_schema_version,
            source_admission_issue_count=report.source_admission_issue_count,
            source_admission_metadata_digest=report.source_admission_metadata_digest,
            source_admission_count=report.source_admission_count,
            source_admission_total_admitted_bytes=(
                report.source_admission_total_admitted_bytes
            ),
            source_receipt_contract=report.source_receipt_contract,
            source_receipt_schema_version=report.source_receipt_schema_version,
            source_receipt_issue_count=report.source_receipt_issue_count,
            source_receipt_metadata_digest=report.source_receipt_metadata_digest,
            source_receipt_source_admission_metadata_digest="sha256:" + "1" * 64,
            source_receipt_count=report.source_receipt_count,
            source_receipt_total_receipted_bytes=(
                report.source_receipt_total_receipted_bytes
            ),
            rows=report.rows,
            issues=(),
        )


def test_runtime_allocation_reconciliation_rejects_row_binding_mismatch() -> None:
    report = build_current_runtime_allocation_reconciliation_report()
    bad_row = replace(report.rows[0], receipt_request_id="alloc_request_other")

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationReconciliationReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            source_admission_contract=report.source_admission_contract,
            source_admission_schema_version=report.source_admission_schema_version,
            source_admission_issue_count=report.source_admission_issue_count,
            source_admission_metadata_digest=report.source_admission_metadata_digest,
            source_admission_count=report.source_admission_count,
            source_admission_total_admitted_bytes=(
                report.source_admission_total_admitted_bytes
            ),
            source_receipt_contract=report.source_receipt_contract,
            source_receipt_schema_version=report.source_receipt_schema_version,
            source_receipt_issue_count=report.source_receipt_issue_count,
            source_receipt_metadata_digest=report.source_receipt_metadata_digest,
            source_receipt_source_admission_metadata_digest=(
                report.source_receipt_source_admission_metadata_digest
            ),
            source_receipt_count=report.source_receipt_count,
            source_receipt_total_receipted_bytes=(
                report.source_receipt_total_receipted_bytes
            ),
            rows=(bad_row, *report.rows[1:]),
            issues=(),
        )


def test_runtime_allocation_reconciliation_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden allocation or execution surface"):
        RuntimeAllocationReconciliationRow(
            row_id="runtime_handle",
            admission_request_id="alloc_request_001",
            receipt_request_id="alloc_request_001",
            admission_slot_id="slot_001",
            receipt_slot_id="slot_001",
            receipt_id="allocation_receipt_001",
            admission_memory_domain=MemoryDomainKind.HOST_RAM,
            receipt_memory_domain=MemoryDomainKind.HOST_RAM,
            admission_budget_id="host_ram_alpha_budget",
            receipt_budget_id="host_ram_alpha_budget",
            admitted_bytes=64,
            receipted_bytes=64,
            domain_offset_bytes=0,
            domain_end_bytes=64,
            domain_total_reserved_bytes=192,
            domain_max_reserved_bytes=192,
        )


def test_runtime_allocation_reconciliation_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_allocation_reconciliation_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_ALLOCATION_RECONCILIATION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["reconciliation_contract"]["const"] == (
        RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT
    )
    assert schema["properties"]["reconciliation_policy_id"]["const"] == (
        RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID
    )
    assert schema["properties"]["reconciliation_status"]["const"] == (
        RUNTIME_ALLOCATION_RECONCILIATION_STATUS
    )
    assert schema["properties"]["source_admission_contract"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    )
    assert schema["properties"]["source_admission_schema_version"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["source_receipt_contract"]["const"] == (
        RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    )
    assert schema["properties"]["source_receipt_schema_version"]["const"] == (
        RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["rows"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_RECONCILIATION_ROWS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_RECONCILIATION_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_allocation_reconciliation_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "device_id",
        "device_pointer",
        "memory_address",
        "pointer",
        "runtime_handle",
        "allocator_handle",
        "subprocess",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["row"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_allocation_reconciliation_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_ALLOCATION_RECONCILIATION_REPORT_SCHEMA_VERSION
    assert golden["reconciliation_contract"] == RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT
    assert golden["reconciliation_policy_id"] == RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID
    assert golden["reconciliation_status"] == RUNTIME_ALLOCATION_RECONCILIATION_STATUS
    assert golden["allocation_mode"] == RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    assert golden["handle_policy"] == RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY
    assert golden["source_admission_contract"] == RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    assert golden["source_receipt_contract"] == RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["row_count"] == len(golden["rows"]) > 0
    assert golden["total_reconciled_bytes"] == (
        golden["source_admission_total_admitted_bytes"]
    )
    assert golden["total_reconciled_bytes"] == (
        golden["source_receipt_total_receipted_bytes"]
    )


def test_runtime_allocation_reconciliation_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_allocation_reconciliation_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_ALLOCATION_RECONCILIATION.md"),
        Path("docs/RUNTIME_MEMORY_PLANNING_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0203-runtime-allocation-reconciliation.md"),
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
