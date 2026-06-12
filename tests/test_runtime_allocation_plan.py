from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from tuc import (
    MAX_RUNTIME_ALLOCATION_BINDINGS,
    MAX_RUNTIME_ALLOCATION_ISSUES,
    MAX_RUNTIME_ALLOCATION_SLOTS,
    RUNTIME_ALLOCATION_PLAN_CONTRACT,
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RUNTIME_BUFFER_LIFETIME_CONTRACT,
    RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    LayoutKind,
    MemoryDomainKind,
    RuntimeAllocationIssue,
    RuntimeAllocationPlanError,
    RuntimeAllocationPlanReport,
    RuntimeAllocationSlot,
    assert_runtime_allocation_plan,
    dump_runtime_allocation_plan_report,
    runtime_allocation_plan_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_allocation_plan_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_allocation_plan/current_report.json")


def test_runtime_allocation_plan_report_passes() -> None:
    report = build_current_runtime_allocation_plan_report()

    assert report.passed
    assert report.allocation_contract == RUNTIME_ALLOCATION_PLAN_CONTRACT
    assert report.source_lifetime_contract == RUNTIME_BUFFER_LIFETIME_CONTRACT
    assert report.source_lifetime_schema_version == (
        RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION
    )
    assert report.source_lifetime_issue_count == 0
    assert report.tensor_binding_count == 4
    assert report.slot_count == 3
    assert report.reuse_slot_count == 1
    assert report.total_tensor_bytes == 256
    assert report.total_reserved_bytes == 192
    assert report.committed_reuse_savings_bytes == 64
    assert report.allocation_metadata_digest.startswith("sha256:")
    assert report.peak_live_bytes == 192
    assert assert_runtime_allocation_plan(report) is report
    assert tuple(runtime_allocation_plan_report_to_dict(report)) == (
        "allocation_contract",
        "allocation_metadata_digest",
        "bindings",
        "blocked_execution_surfaces",
        "committed_reuse_savings_bytes",
        "graph_name",
        "issues",
        "operation_count",
        "passed",
        "peak_live_bytes",
        "reuse_slot_count",
        "schema_version",
        "slot_count",
        "slots",
        "source_lifetime_contract",
        "source_lifetime_issue_count",
        "source_lifetime_schema_version",
        "tensor_binding_count",
        "total_reserved_bytes",
        "total_tensor_bytes",
    )


def test_runtime_allocation_plan_records_reused_slot() -> None:
    report = build_current_runtime_allocation_plan_report()
    reused_slots = tuple(slot for slot in report.slots if slot.allocation_kind == "reused")

    assert len(reused_slots) == 1
    assert reused_slots[0].slot_id == "slot_001"
    assert reused_slots[0].source_reuse_group_id == "reuse_group_001"
    assert reused_slots[0].tensor_names == ("left_tmp", "right_tmp")
    assert reused_slots[0].live_ranges_non_overlapping
    assert tuple(
        binding.tensor_name for binding in report.bindings if binding.slot_id == "slot_001"
    ) == ("left_tmp", "right_tmp")


def test_runtime_allocation_plan_dump_matches_golden() -> None:
    report = build_current_runtime_allocation_plan_report()

    assert dump_runtime_allocation_plan_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_allocation_plan_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_allocation_plan.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_allocation_plan_issues_must_be_derived() -> None:
    report = build_current_runtime_allocation_plan_report()
    bad_slots = (
        replace(report.slots[0], live_ranges_non_overlapping=False),
        *report.slots[1:],
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeAllocationPlanReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            source_lifetime_contract=report.source_lifetime_contract,
            source_lifetime_schema_version=report.source_lifetime_schema_version,
            source_lifetime_issue_count=report.source_lifetime_issue_count,
            bindings=report.bindings,
            slots=bad_slots,
            issues=(),
        )


def test_runtime_allocation_plan_assertion_raises() -> None:
    report = build_current_runtime_allocation_plan_report()
    bad_slots = (
        replace(report.slots[0], live_ranges_non_overlapping=False),
        *report.slots[1:],
    )
    failed = RuntimeAllocationPlanReport(
        graph_name=report.graph_name,
        operation_count=report.operation_count,
        source_lifetime_contract=report.source_lifetime_contract,
        source_lifetime_schema_version=report.source_lifetime_schema_version,
        source_lifetime_issue_count=report.source_lifetime_issue_count,
        bindings=report.bindings,
        slots=bad_slots,
        issues=(
            RuntimeAllocationIssue(
                subject="slot_001",
                issue_code="allocation_slot_lifetimes_overlap",
            ),
        ),
    )

    with pytest.raises(RuntimeAllocationPlanError, match="allocation_slot_lifetimes_overlap"):
        assert_runtime_allocation_plan(failed)


def test_runtime_allocation_plan_rejects_reserved_byte_overflow() -> None:
    report = build_current_runtime_allocation_plan_report()
    bad_slots = (replace(report.slots[0], bytes_reserved=512), *report.slots[1:])
    failed = RuntimeAllocationPlanReport(
        graph_name=report.graph_name,
        operation_count=report.operation_count,
        source_lifetime_contract=report.source_lifetime_contract,
        source_lifetime_schema_version=report.source_lifetime_schema_version,
        source_lifetime_issue_count=report.source_lifetime_issue_count,
        bindings=report.bindings,
        slots=bad_slots,
        issues=(
            RuntimeAllocationIssue(
                subject="plan",
                issue_code="reserved_bytes_exceed_tensor_bytes",
            ),
        ),
    )

    assert failed.committed_reuse_savings_bytes == 0
    with pytest.raises(RuntimeAllocationPlanError, match="reserved_bytes_exceed"):
        assert_runtime_allocation_plan(failed)


def test_runtime_allocation_plan_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeAllocationSlot(
            slot_id="plugin_entrypoint",
            source_reuse_group_id="reuse_group_001",
            memory_domain=MemoryDomainKind.HOST_RAM,
            layout=LayoutKind.ROW_MAJOR,
            dtype="float32",
            shape=(4, 4),
            bytes_reserved=64,
            tensor_names=("left_tmp",),
            allocation_kind="exclusive",
            live_ranges_non_overlapping=True,
        )


def test_runtime_allocation_plan_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        runtime_allocation_plan_report_to_dict(object())  # type: ignore[arg-type]


def test_runtime_allocation_plan_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/runtime_allocation_plan_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["allocation_contract"]["const"] == (
        RUNTIME_ALLOCATION_PLAN_CONTRACT
    )
    assert schema["properties"]["allocation_metadata_digest"] == {
        "$ref": "#/$defs/sha256_digest"
    }
    assert schema["properties"]["source_lifetime_contract"]["const"] == (
        RUNTIME_BUFFER_LIFETIME_CONTRACT
    )
    assert schema["properties"]["source_lifetime_schema_version"]["const"] == (
        RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["bindings"]["maxItems"] == MAX_RUNTIME_ALLOCATION_BINDINGS
    assert schema["properties"]["slots"]["maxItems"] == MAX_RUNTIME_ALLOCATION_SLOTS
    assert schema["properties"]["issues"]["maxItems"] == MAX_RUNTIME_ALLOCATION_ISSUES
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_allocation_plan_schema_fails_closed() -> None:
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
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["binding"]["properties"]
        assert forbidden not in schema["$defs"]["slot"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_allocation_plan_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    assert golden["allocation_contract"] == RUNTIME_ALLOCATION_PLAN_CONTRACT
    assert golden["allocation_metadata_digest"].startswith("sha256:")
    assert golden["source_lifetime_contract"] == RUNTIME_BUFFER_LIFETIME_CONTRACT
    assert golden["source_lifetime_schema_version"] == (
        RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION
    )
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["tensor_binding_count"] == len(golden["bindings"]) == 4
    assert golden["slot_count"] == len(golden["slots"]) == 3
    assert golden["reuse_slot_count"] == 1


def test_runtime_allocation_plan_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_allocation_plan_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_ALLOCATION_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0102-runtime-allocation-plan.md"),
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
