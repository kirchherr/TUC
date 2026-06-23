from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_allocation_admission import (
    build_current_runtime_allocation_admission_report,
)
from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from tuc import (
    MAX_RUNTIME_ALLOCATION_ADMISSION_ISSUES,
    MAX_RUNTIME_ALLOCATION_ADMISSIONS,
    RUNTIME_ALLOCATION_ADMISSION_CONTRACT,
    RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY,
    RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_ADMISSION_STATUS,
    RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT,
    RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_MEMORY_BUDGET_CONTRACT,
    RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
    MemoryDomainKind,
    RuntimeAllocationAdmission,
    RuntimeAllocationAdmissionError,
    RuntimeAllocationAdmissionReport,
    RuntimeMemoryDomainBudget,
    assert_runtime_allocation_admission,
    build_runtime_allocation_admission_report,
    build_runtime_allocation_request_manifest_report,
    build_runtime_memory_budget_report,
    dump_runtime_allocation_admission_report,
    runtime_allocation_admission_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_allocation_admission_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_allocation_admission/current_report.json")


def test_runtime_allocation_admission_report_passes() -> None:
    report = build_current_runtime_allocation_admission_report()

    assert report.passed is True
    assert report.admission_contract == RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    assert report.handle_policy == RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
    assert report.source_request_manifest_contract == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    )
    assert report.source_request_manifest_schema_version == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert report.source_memory_budget_contract == RUNTIME_MEMORY_BUDGET_CONTRACT
    assert report.source_memory_budget_schema_version == (
        RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert report.source_request_manifest_budget_allocation_digest == (
        report.source_memory_budget_allocation_digest
    )
    assert report.admission_count == len(report.admissions) > 0
    assert report.blocked_admission_count == 0
    assert report.total_admitted_bytes == sum(
        admission.bytes_reserved for admission in report.admissions
    )
    assert {admission.admission_status for admission in report.admissions} == {
        RUNTIME_ALLOCATION_ADMISSION_STATUS
    }
    assert {admission.handle_policy for admission in report.admissions} == {
        RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
    }
    assert "\"runtime_handle\"" not in dump_runtime_allocation_admission_report(
        report
    )
    assert list(runtime_allocation_admission_report_to_dict(report)) == [
        "admission_contract",
        "admission_count",
        "admissions",
        "blocked_admission_count",
        "blocked_execution_surfaces",
        "graph_name",
        "handle_policy",
        "issues",
        "operation_count",
        "passed",
        "schema_version",
        "source_memory_budget_allocation_digest",
        "source_memory_budget_contract",
        "source_memory_budget_issue_count",
        "source_memory_budget_schema_version",
        "source_request_manifest_budget_allocation_digest",
        "source_request_manifest_contract",
        "source_request_manifest_issue_count",
        "source_request_manifest_metadata_digest",
        "source_request_manifest_schema_version",
        "total_admitted_bytes",
    ]


def test_runtime_allocation_admission_dump_matches_golden() -> None:
    report = build_current_runtime_allocation_admission_report()

    assert dump_runtime_allocation_admission_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_allocation_admission_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_allocation_admission.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "python_source" not in completed.stdout
    assert "\"runtime_handle\"" not in completed.stdout


def test_runtime_allocation_admission_assertion_passes() -> None:
    report = build_current_runtime_allocation_admission_report()

    assert assert_runtime_allocation_admission(report) is report


def test_runtime_allocation_admission_records_failed_budget() -> None:
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
    report = build_runtime_allocation_admission_report(manifest, failed_budget)

    assert report.passed is False
    assert report.blocked_admission_count == report.admission_count
    assert "source_memory_budget_failed" in [
        issue.issue_code for issue in report.issues
    ]
    with pytest.raises(
        RuntimeAllocationAdmissionError,
        match="allocation admission failed",
    ):
        assert_runtime_allocation_admission(report)


def test_runtime_allocation_admission_records_digest_mismatch() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    memory_budget = build_current_runtime_memory_budget_report()
    stale_budget = replace(
        memory_budget,
        source_allocation_metadata_digest="sha256:" + "1" * 64,
    )
    manifest = build_runtime_allocation_request_manifest_report(
        allocation,
        stale_budget,
    )
    report = build_runtime_allocation_admission_report(manifest, memory_budget)

    assert report.passed is False
    assert "source_memory_budget_digest_mismatch" in [
        issue.issue_code for issue in report.issues
    ]


def test_runtime_allocation_admission_requires_derived_issues() -> None:
    report = build_current_runtime_allocation_admission_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationAdmissionReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            source_request_manifest_contract=report.source_request_manifest_contract,
            source_request_manifest_schema_version=(
                report.source_request_manifest_schema_version
            ),
            source_request_manifest_issue_count=(
                report.source_request_manifest_issue_count
            ),
            source_request_manifest_metadata_digest=(
                report.source_request_manifest_metadata_digest
            ),
            source_request_manifest_budget_allocation_digest=(
                "sha256:" + "1" * 64
            ),
            source_memory_budget_contract=report.source_memory_budget_contract,
            source_memory_budget_schema_version=(
                report.source_memory_budget_schema_version
            ),
            source_memory_budget_issue_count=report.source_memory_budget_issue_count,
            source_memory_budget_allocation_digest=(
                report.source_memory_budget_allocation_digest
            ),
            admissions=report.admissions,
            issues=(),
        )


def test_runtime_allocation_admission_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeAllocationAdmission(
            request_id="runtime_handle",
            slot_id="slot_001",
            memory_domain=MemoryDomainKind.HOST_RAM,
            budget_id="host_ram_alpha_budget",
            bytes_reserved=64,
            domain_total_reserved_bytes=192,
            domain_max_reserved_bytes=192,
            admission_status=RUNTIME_ALLOCATION_ADMISSION_STATUS,
        )


def test_runtime_allocation_admission_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_allocation_admission_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["admission_contract"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    )
    assert schema["properties"]["handle_policy"]["const"] == (
        RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
    )
    assert schema["properties"]["source_request_manifest_contract"]["const"] == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    )
    assert schema["properties"]["source_memory_budget_contract"]["const"] == (
        RUNTIME_MEMORY_BUDGET_CONTRACT
    )
    assert schema["properties"]["admissions"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_ADMISSIONS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_ADMISSION_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"][
            "prefixItems"
        ]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_allocation_admission_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "device_id",
        "dynamic_library",
        "subprocess",
        "raw_benchmark_output",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["admission"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_allocation_admission_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
    assert golden["admission_contract"] == RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    assert golden["handle_policy"] == RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
    assert golden["source_request_manifest_contract"] == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    )
    assert golden["source_memory_budget_contract"] == RUNTIME_MEMORY_BUDGET_CONTRACT
    assert golden["source_request_manifest_budget_allocation_digest"] == (
        golden["source_memory_budget_allocation_digest"]
    )
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["blocked_admission_count"] == 0
    assert golden["admission_count"] == len(golden["admissions"]) > 0


def test_runtime_allocation_admission_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_allocation_admission_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_ALLOCATION_ADMISSION.md"),
        Path("docs/RUNTIME_MEMORY_PLANNING_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0201-runtime-allocation-admission.md"),
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
