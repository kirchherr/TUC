from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_buffer_lifetime import build_current_runtime_buffer_lifetime_report
from tuc import (
    MAX_RUNTIME_BUFFER_LIFETIME_ISSUES,
    MAX_RUNTIME_BUFFER_LIFETIMES,
    MAX_RUNTIME_BUFFER_REUSE_GROUPS,
    RUNTIME_BUFFER_LIFETIME_CONTRACT,
    RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    LayoutKind,
    MemoryDomainKind,
    RuntimeBufferLifetime,
    RuntimeBufferLifetimeError,
    RuntimeBufferLifetimeIssue,
    RuntimeBufferLifetimeReport,
    assert_runtime_buffer_lifetime,
    dump_runtime_buffer_lifetime_report,
    runtime_buffer_lifetime_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_buffer_lifetime_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_buffer_lifetime/current_report.json")


def test_runtime_buffer_lifetime_report_passes() -> None:
    report = build_current_runtime_buffer_lifetime_report()

    assert report.passed
    assert report.lifetime_contract == RUNTIME_BUFFER_LIFETIME_CONTRACT
    assert report.tensor_lifetime_count == 4
    assert report.reuse_group_count == 3
    assert report.total_tensor_bytes == 256
    assert report.peak_live_bytes == 192
    assert report.reuse_savings_upper_bound_bytes == 64
    assert report.lifetime_metadata_digest.startswith("sha256:")
    assert assert_runtime_buffer_lifetime(report) is report
    assert tuple(runtime_buffer_lifetime_report_to_dict(report)) == (
        "blocked_execution_surfaces",
        "graph_name",
        "issues",
        "lifetime_contract",
        "lifetime_metadata_digest",
        "lifetimes",
        "operation_count",
        "passed",
        "peak_live_bytes",
        "reuse_group_count",
        "reuse_groups",
        "reuse_savings_upper_bound_bytes",
        "schema_version",
        "tensor_lifetime_count",
        "total_tensor_bytes",
    )


def test_runtime_buffer_lifetime_records_reuse_candidates() -> None:
    report = build_current_runtime_buffer_lifetime_report()
    reusable = tuple(lifetime for lifetime in report.lifetimes if lifetime.reusable)

    assert tuple(lifetime.tensor_name for lifetime in reusable) == (
        "left_tmp",
        "right_tmp",
    )
    assert reusable[0].reuse_group_id == reusable[1].reuse_group_id
    assert reusable[0].last_use_index < reusable[1].producer_index
    assert report.reuse_groups[0].tensor_names == ("left_tmp", "right_tmp")
    assert report.reuse_groups[0].non_overlapping


def test_runtime_buffer_lifetime_dump_matches_golden() -> None:
    report = build_current_runtime_buffer_lifetime_report()

    assert dump_runtime_buffer_lifetime_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_buffer_lifetime_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_buffer_lifetime.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_buffer_lifetime_issues_must_be_derived() -> None:
    report = build_current_runtime_buffer_lifetime_report()
    bad_lifetimes = (
        replace(report.lifetimes[0], reuse_group_id="missing_group"),
        *report.lifetimes[1:],
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeBufferLifetimeReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            lifetimes=bad_lifetimes,
            reuse_groups=report.reuse_groups,
            issues=(),
        )


def test_runtime_buffer_lifetime_assertion_raises() -> None:
    report = build_current_runtime_buffer_lifetime_report()
    bad_lifetime = replace(report.lifetimes[0], reuse_group_id="missing_group")
    failed = RuntimeBufferLifetimeReport(
        graph_name=report.graph_name,
        operation_count=report.operation_count,
        lifetimes=(bad_lifetime, *report.lifetimes[1:]),
        reuse_groups=report.reuse_groups,
        issues=(
            RuntimeBufferLifetimeIssue(
                subject=bad_lifetime.tensor_name,
                issue_code="reuse_group_missing",
            ),
        ),
    )

    with pytest.raises(RuntimeBufferLifetimeError, match="reuse_group_missing"):
        assert_runtime_buffer_lifetime(failed)


def test_runtime_buffer_lifetime_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeBufferLifetime(
            tensor_name="plugin_entrypoint",
            producer_operation="producer",
            producer_index=0,
            first_live_index=0,
            last_use_index=1,
            last_consumer_operation="consumer",
            lifetime_kind="intermediate",
            bytes_allocated=64,
            memory_domain=MemoryDomainKind.HOST_RAM,
            layout=LayoutKind.ROW_MAJOR,
            dtype="float32",
            shape=(4, 4),
            reuse_group_id="reuse_group_001",
            reusable=False,
        )


def test_runtime_buffer_lifetime_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        runtime_buffer_lifetime_report_to_dict(object())  # type: ignore[arg-type]


def test_runtime_buffer_lifetime_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/runtime_buffer_lifetime_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["lifetime_contract"]["const"] == (
        RUNTIME_BUFFER_LIFETIME_CONTRACT
    )
    assert schema["properties"]["lifetime_metadata_digest"] == {
        "$ref": "#/$defs/sha256_digest"
    }
    assert schema["properties"]["lifetimes"]["maxItems"] == MAX_RUNTIME_BUFFER_LIFETIMES
    assert schema["properties"]["reuse_groups"]["maxItems"] == (
        MAX_RUNTIME_BUFFER_REUSE_GROUPS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_BUFFER_LIFETIME_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_buffer_lifetime_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["lifetime"]["properties"]
        assert forbidden not in schema["$defs"]["reuse_group"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_buffer_lifetime_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION
    assert golden["lifetime_contract"] == RUNTIME_BUFFER_LIFETIME_CONTRACT
    assert golden["lifetime_metadata_digest"].startswith("sha256:")
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["tensor_lifetime_count"] == len(golden["lifetimes"]) == 4
    assert golden["reuse_group_count"] == len(golden["reuse_groups"]) == 3


def test_runtime_buffer_lifetime_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_buffer_lifetime_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_BUFFER_LIFETIME.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0101-runtime-buffer-lifetime.md"),
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
