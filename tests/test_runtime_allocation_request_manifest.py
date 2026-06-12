from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_allocation_request_manifest import (
    build_current_runtime_allocation_request_manifest_report,
)
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from tuc import (
    MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_ISSUES,
    MAX_RUNTIME_ALLOCATION_REQUESTS,
    RUNTIME_ALLOCATION_PLAN_CONTRACT,
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY,
    RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT,
    RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_REQUEST_STATUS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_MEMORY_BUDGET_CONTRACT,
    RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
    LayoutKind,
    MemoryDomainKind,
    RuntimeAllocationRequest,
    RuntimeAllocationRequestManifestError,
    RuntimeAllocationRequestManifestReport,
    assert_runtime_allocation_request_manifest,
    build_runtime_allocation_request_manifest_report,
    dump_runtime_allocation_request_manifest_report,
    runtime_allocation_request_manifest_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_allocation_request_manifest_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_allocation_request_manifest/current_report.json")


def test_runtime_allocation_request_manifest_report_passes() -> None:
    report = build_current_runtime_allocation_request_manifest_report()

    assert report.passed is True
    assert report.manifest_contract == RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    assert report.handle_policy == RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
    assert report.source_allocation_contract == RUNTIME_ALLOCATION_PLAN_CONTRACT
    assert report.source_allocation_schema_version == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert report.source_memory_budget_contract == RUNTIME_MEMORY_BUDGET_CONTRACT
    assert report.source_memory_budget_schema_version == (
        RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert report.source_allocation_metadata_digest.startswith("sha256:")
    assert report.source_memory_budget_allocation_digest == (
        report.source_allocation_metadata_digest
    )
    assert report.request_count == len(report.requests) > 0
    assert report.total_reserved_bytes == sum(
        request.bytes_reserved for request in report.requests
    )
    assert {request.handle_policy for request in report.requests} == {
        RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
    }
    assert {request.request_status for request in report.requests} == {
        RUNTIME_ALLOCATION_REQUEST_STATUS
    }
    assert '"runtime_handle"' not in dump_runtime_allocation_request_manifest_report(
        report
    )
    assert list(runtime_allocation_request_manifest_report_to_dict(report)) == [
        "blocked_execution_surfaces",
        "graph_name",
        "handle_policy",
        "issues",
        "manifest_contract",
        "manifest_metadata_digest",
        "operation_count",
        "passed",
        "request_count",
        "requests",
        "schema_version",
        "source_allocation_contract",
        "source_allocation_metadata_digest",
        "source_allocation_schema_version",
        "source_memory_budget_allocation_digest",
        "source_memory_budget_contract",
        "source_memory_budget_schema_version",
        "total_reserved_bytes",
    ]


def test_runtime_allocation_request_manifest_dump_matches_golden() -> None:
    report = build_current_runtime_allocation_request_manifest_report()

    assert dump_runtime_allocation_request_manifest_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_allocation_request_manifest_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_allocation_request_manifest.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "python_source" not in completed.stdout
    assert '"runtime_handle"' not in completed.stdout


def test_runtime_allocation_request_manifest_assertion_passes() -> None:
    report = build_current_runtime_allocation_request_manifest_report()

    assert assert_runtime_allocation_request_manifest(report) is report


def test_runtime_allocation_request_manifest_records_digest_mismatch() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    memory_budget = build_current_runtime_memory_budget_report()
    stale_budget = replace(
        memory_budget,
        source_allocation_metadata_digest="sha256:" + "1" * 64,
    )
    report = build_runtime_allocation_request_manifest_report(
        allocation,
        stale_budget,
    )

    assert report.passed is False
    assert [issue.issue_code for issue in report.issues] == [
        "source_allocation_digest_mismatch"
    ]
    with pytest.raises(
        RuntimeAllocationRequestManifestError,
        match="runtime allocation request manifest failed",
    ):
        assert_runtime_allocation_request_manifest(report)


def test_runtime_allocation_request_manifest_requires_derived_issues() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    memory_budget = build_current_runtime_memory_budget_report()
    stale_budget = replace(
        memory_budget,
        source_allocation_metadata_digest="sha256:" + "1" * 64,
    )
    failed = build_runtime_allocation_request_manifest_report(
        allocation,
        stale_budget,
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationRequestManifestReport(
            graph_name=failed.graph_name,
            operation_count=failed.operation_count,
            source_allocation_contract=failed.source_allocation_contract,
            source_allocation_schema_version=failed.source_allocation_schema_version,
            source_allocation_metadata_digest=failed.source_allocation_metadata_digest,
            source_memory_budget_contract=failed.source_memory_budget_contract,
            source_memory_budget_schema_version=(
                failed.source_memory_budget_schema_version
            ),
            source_memory_budget_allocation_digest=(
                failed.source_memory_budget_allocation_digest
            ),
            requests=failed.requests,
            issues=(),
        )


def test_runtime_allocation_request_manifest_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeAllocationRequest(
            request_id="runtime_handle",
            slot_id="slot_001",
            memory_domain=MemoryDomainKind.HOST_RAM,
            layout=LayoutKind.ROW_MAJOR,
            dtype="float64",
            shape=(2, 2),
            bytes_reserved=32,
            tensor_names=("tensor_001",),
            allocation_kind="exclusive",
        )


def test_runtime_allocation_request_manifest_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_allocation_request_manifest_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["manifest_contract"]["const"] == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    )
    assert schema["properties"]["handle_policy"]["const"] == (
        RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
    )
    assert schema["properties"]["source_allocation_contract"]["const"] == (
        RUNTIME_ALLOCATION_PLAN_CONTRACT
    )
    assert schema["properties"]["source_allocation_schema_version"]["const"] == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["source_memory_budget_contract"]["const"] == (
        RUNTIME_MEMORY_BUDGET_CONTRACT
    )
    assert schema["properties"]["source_memory_budget_schema_version"]["const"] == (
        RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["requests"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_REQUESTS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_allocation_request_manifest_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["request"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_allocation_request_manifest_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert golden["manifest_contract"] == RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    assert golden["handle_policy"] == RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
    assert golden["source_allocation_contract"] == RUNTIME_ALLOCATION_PLAN_CONTRACT
    assert golden["source_allocation_schema_version"] == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert golden["source_memory_budget_contract"] == RUNTIME_MEMORY_BUDGET_CONTRACT
    assert golden["source_memory_budget_schema_version"] == (
        RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert golden["source_allocation_metadata_digest"].startswith("sha256:")
    assert golden["source_memory_budget_allocation_digest"] == (
        golden["source_allocation_metadata_digest"]
    )
    assert golden["manifest_metadata_digest"].startswith("sha256:")
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["request_count"] == len(golden["requests"]) > 0


def test_runtime_allocation_request_manifest_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_allocation_request_manifest_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_ALLOCATION_REQUEST_MANIFEST.md"),
        Path("docs/RUNTIME_MEMORY_PLANNING_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0133-runtime-allocation-request-manifest.md"),
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
