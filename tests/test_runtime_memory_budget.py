from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from tuc import (
    MAX_RUNTIME_MEMORY_BUDGET_ISSUES,
    MAX_RUNTIME_MEMORY_BUDGET_USAGES,
    MAX_RUNTIME_MEMORY_BUDGETS,
    RUNTIME_ALLOCATION_PLAN_CONTRACT,
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_MEMORY_BUDGET_CONTRACT,
    RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
    MemoryDomainKind,
    RuntimeMemoryBudgetError,
    RuntimeMemoryBudgetReport,
    RuntimeMemoryDomainBudget,
    assert_runtime_memory_budget,
    build_runtime_memory_budget_report,
    dump_runtime_memory_budget_report,
    runtime_memory_budget_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_memory_budget_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_memory_budget/current_report.json")


def test_runtime_memory_budget_report_passes() -> None:
    report = build_current_runtime_memory_budget_report()

    assert report.passed
    assert report.budget_contract == RUNTIME_MEMORY_BUDGET_CONTRACT
    assert report.source_allocation_contract == RUNTIME_ALLOCATION_PLAN_CONTRACT
    assert report.source_allocation_schema_version == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert report.source_allocation_issue_count == 0
    assert report.source_allocation_metadata_digest.startswith("sha256:")
    assert report.budget_count == 1
    assert report.usage_count == 1
    assert report.total_reserved_bytes == 192
    assert report.total_peak_live_bytes == 192
    assert assert_runtime_memory_budget(report) is report
    assert tuple(runtime_memory_budget_report_to_dict(report)) == (
        "blocked_execution_surfaces",
        "budget_contract",
        "budget_count",
        "budgets",
        "graph_name",
        "issues",
        "operation_count",
        "passed",
        "schema_version",
        "source_allocation_contract",
        "source_allocation_issue_count",
        "source_allocation_metadata_digest",
        "source_allocation_schema_version",
        "total_peak_live_bytes",
        "total_reserved_bytes",
        "usage_count",
        "usages",
    )


def test_runtime_memory_budget_records_domain_usage() -> None:
    report = build_current_runtime_memory_budget_report()
    usage = report.usages[0]

    assert usage.memory_domain is MemoryDomainKind.HOST_RAM
    assert usage.budget_id == "host_ram_alpha_budget"
    assert usage.total_reserved_bytes == 192
    assert usage.peak_live_bytes == 192
    assert usage.status == "within_budget"


def test_runtime_memory_budget_dump_matches_golden() -> None:
    report = build_current_runtime_memory_budget_report()

    assert dump_runtime_memory_budget_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_memory_budget_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_memory_budget.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_memory_budget_fails_closed_without_domain_budget() -> None:
    allocation_report = build_current_runtime_allocation_plan_report()
    report = build_runtime_memory_budget_report(allocation_report, ())

    assert not report.passed
    assert [issue.issue_code for issue in report.issues] == [
        "memory_budgets_missing",
        "memory_domain_budget_missing",
    ]
    assert report.usages[0].status == "missing_budget"
    assert report.usages[0].max_reserved_bytes == 0


def test_runtime_memory_budget_fails_closed_when_budget_is_too_small() -> None:
    allocation_report = build_current_runtime_allocation_plan_report()
    report = build_runtime_memory_budget_report(
        allocation_report,
        (
            RuntimeMemoryDomainBudget(
                budget_id="tiny_host_ram_budget",
                memory_domain=MemoryDomainKind.HOST_RAM,
                max_reserved_bytes=64,
                max_peak_live_bytes=192,
            ),
        ),
    )

    assert not report.passed
    assert report.usages[0].status == "reserved_exceeded"
    assert [issue.issue_code for issue in report.issues] == [
        "reserved_bytes_exceed_budget"
    ]


def test_runtime_memory_budget_issues_must_be_derived() -> None:
    allocation_report = build_current_runtime_allocation_plan_report()
    failed = build_runtime_memory_budget_report(allocation_report, ())

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeMemoryBudgetReport(
            graph_name=failed.graph_name,
            operation_count=failed.operation_count,
            source_allocation_contract=failed.source_allocation_contract,
            source_allocation_schema_version=failed.source_allocation_schema_version,
            source_allocation_issue_count=failed.source_allocation_issue_count,
            source_allocation_metadata_digest=failed.source_allocation_metadata_digest,
            budgets=failed.budgets,
            usages=failed.usages,
            issues=(),
        )


def test_runtime_memory_budget_assertion_raises() -> None:
    allocation_report = build_current_runtime_allocation_plan_report()
    failed = build_runtime_memory_budget_report(allocation_report, ())

    with pytest.raises(RuntimeMemoryBudgetError, match="memory_domain_budget_missing"):
        assert_runtime_memory_budget(failed)


def test_runtime_memory_budget_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeMemoryDomainBudget(
            budget_id="plugin_entrypoint",
            memory_domain=MemoryDomainKind.HOST_RAM,
            max_reserved_bytes=192,
            max_peak_live_bytes=192,
        )


def test_runtime_memory_budget_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        runtime_memory_budget_report_to_dict(object())  # type: ignore[arg-type]


def test_runtime_memory_budget_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/runtime_memory_budget_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["budget_contract"]["const"] == (
        RUNTIME_MEMORY_BUDGET_CONTRACT
    )
    assert schema["properties"]["source_allocation_contract"]["const"] == (
        RUNTIME_ALLOCATION_PLAN_CONTRACT
    )
    assert schema["properties"]["source_allocation_schema_version"]["const"] == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["source_allocation_metadata_digest"] == {
        "$ref": "#/$defs/sha256_digest"
    }
    assert schema["properties"]["budgets"]["maxItems"] == MAX_RUNTIME_MEMORY_BUDGETS
    assert schema["properties"]["usages"]["maxItems"] == (
        MAX_RUNTIME_MEMORY_BUDGET_USAGES
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_MEMORY_BUDGET_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_memory_budget_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["budget"]["properties"]
        assert forbidden not in schema["$defs"]["usage"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_memory_budget_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
    assert golden["budget_contract"] == RUNTIME_MEMORY_BUDGET_CONTRACT
    assert golden["source_allocation_contract"] == RUNTIME_ALLOCATION_PLAN_CONTRACT
    assert golden["source_allocation_schema_version"] == (
        RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
    )
    assert golden["source_allocation_metadata_digest"].startswith("sha256:")
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["budget_count"] == len(golden["budgets"]) == 1
    assert golden["usage_count"] == len(golden["usages"]) == 1


def test_runtime_memory_budget_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_memory_budget_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_MEMORY_BUDGET.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0103-runtime-memory-budget.md"),
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
