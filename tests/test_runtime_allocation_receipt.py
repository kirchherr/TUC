from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_allocation_receipt import (
    build_current_runtime_allocation_receipt_report,
)
from tuc import (
    MAX_RUNTIME_ALLOCATION_RECEIPT_ISSUES,
    MAX_RUNTIME_ALLOCATION_RECEIPTS,
    RUNTIME_ALLOCATION_ADMISSION_CONTRACT,
    RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE,
    RUNTIME_ALLOCATION_RECEIPT_CONTRACT,
    RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY,
    RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_RECEIPT_STATUS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    MemoryDomainKind,
    RuntimeAllocationReceipt,
    RuntimeAllocationReceiptError,
    RuntimeAllocationReceiptReport,
    RuntimeMemoryDomainBudget,
    assert_runtime_allocation_receipt,
    build_runtime_allocation_admission_report,
    build_runtime_allocation_receipt_report,
    build_runtime_allocation_request_manifest_report,
    build_runtime_memory_budget_report,
    dump_runtime_allocation_receipt_report,
    runtime_allocation_receipt_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_allocation_receipt_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_allocation_receipt/current_report.json")


def test_runtime_allocation_receipt_report_passes() -> None:
    report = build_current_runtime_allocation_receipt_report()

    assert report.passed is True
    assert report.receipt_contract == RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    assert report.allocation_mode == RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    assert report.handle_policy == RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY
    assert report.source_admission_contract == RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    assert report.source_admission_schema_version == (
        RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert report.receipt_count == len(report.receipts) > 0
    assert report.total_receipted_bytes == report.source_admission_total_admitted_bytes
    assert tuple(receipt.domain_offset_bytes for receipt in report.receipts) == (
        0,
        64,
        128,
    )
    assert {receipt.allocation_status for receipt in report.receipts} == {
        RUNTIME_ALLOCATION_RECEIPT_STATUS
    }
    assert {receipt.allocation_mode for receipt in report.receipts} == {
        RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    }
    dumped = dump_runtime_allocation_receipt_report(report)
    assert "\"runtime_handle\"" not in dumped
    assert "memory_address" not in dumped
    assert list(runtime_allocation_receipt_report_to_dict(report)) == [
        "allocation_mode",
        "blocked_execution_surfaces",
        "graph_name",
        "handle_policy",
        "issues",
        "operation_count",
        "passed",
        "receipt_contract",
        "receipt_count",
        "receipt_metadata_digest",
        "receipts",
        "schema_version",
        "source_admission_contract",
        "source_admission_issue_count",
        "source_admission_metadata_digest",
        "source_admission_schema_version",
        "source_admission_total_admitted_bytes",
        "total_receipted_bytes",
    ]


def test_runtime_allocation_receipt_dump_matches_golden() -> None:
    report = build_current_runtime_allocation_receipt_report()

    assert dump_runtime_allocation_receipt_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_allocation_receipt_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_allocation_receipt.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "runtime_allocation_receipt.data_only.v0" in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "\"runtime_handle\"" not in completed.stdout


def test_runtime_allocation_receipt_assertion_passes() -> None:
    report = build_current_runtime_allocation_receipt_report()

    assert assert_runtime_allocation_receipt(report) is report


def test_runtime_allocation_receipt_records_failed_admission() -> None:
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
    report = build_runtime_allocation_receipt_report(admission)

    assert report.passed is False
    assert report.receipt_count == 0
    assert "source_allocation_admission_failed" in [
        issue.issue_code for issue in report.issues
    ]
    with pytest.raises(
        RuntimeAllocationReceiptError,
        match="allocation receipt failed",
    ):
        assert_runtime_allocation_receipt(report)


def test_runtime_allocation_receipt_requires_derived_issues() -> None:
    report = build_current_runtime_allocation_receipt_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationReceiptReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            source_admission_contract=report.source_admission_contract,
            source_admission_schema_version=report.source_admission_schema_version,
            source_admission_issue_count=report.source_admission_issue_count,
            source_admission_metadata_digest=report.source_admission_metadata_digest,
            source_admission_total_admitted_bytes=(
                report.source_admission_total_admitted_bytes
            ),
            receipts=(),
            issues=(),
        )


def test_runtime_allocation_receipt_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden allocation or execution surface"):
        RuntimeAllocationReceipt(
            receipt_id="runtime_handle",
            request_id="alloc_request_001",
            slot_id="slot_001",
            memory_domain=MemoryDomainKind.HOST_RAM,
            budget_id="host_ram_alpha_budget",
            bytes_reserved=64,
            domain_offset_bytes=0,
            domain_total_reserved_bytes=192,
            domain_max_reserved_bytes=192,
        )


def test_runtime_allocation_receipt_rejects_address_like_receipt() -> None:
    report = build_current_runtime_allocation_receipt_report()

    with pytest.raises(ValueError, match="forbidden allocation or execution surface"):
        replace(report.receipts[0], receipt_id="memory_address")


def test_runtime_allocation_receipt_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_allocation_receipt_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["receipt_contract"]["const"] == (
        RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    )
    assert schema["properties"]["allocation_mode"]["const"] == (
        RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    )
    assert schema["properties"]["handle_policy"]["const"] == (
        RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY
    )
    assert schema["properties"]["source_admission_contract"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    )
    assert schema["properties"]["source_admission_schema_version"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["receipts"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_RECEIPTS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_RECEIPT_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"][
            "prefixItems"
        ]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_allocation_receipt_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["receipt"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_allocation_receipt_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION
    assert golden["receipt_contract"] == RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    assert golden["allocation_mode"] == RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    assert golden["handle_policy"] == RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY
    assert golden["source_admission_contract"] == RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["receipt_count"] == len(golden["receipts"]) > 0
    assert golden["total_receipted_bytes"] == (
        golden["source_admission_total_admitted_bytes"]
    )


def test_runtime_allocation_receipt_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_allocation_receipt_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_ALLOCATION_RECEIPT.md"),
        Path("docs/RUNTIME_MEMORY_PLANNING_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0202-runtime-allocation-receipt.md"),
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
