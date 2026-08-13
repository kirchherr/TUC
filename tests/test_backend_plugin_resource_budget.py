from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_plugin_resource_budget import (
    build_current_backend_plugin_resource_budget_report,
)
from tuc import (
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
    BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT,
    BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION,
    BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY,
    BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_SCHEMA_VERSION,
    BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS,
    BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS,
    BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ARTIFACT_BYTES,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CACHE_ENTRIES,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CPU_TIME_MS,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_DIAGNOSTICS_BYTES,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_OUTPUT_BYTES,
    MAX_BACKEND_PLUGIN_RESOURCE_BUDGETS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendPluginResourceBudgetError,
    BackendPluginResourceBudgetIssue,
    BackendPluginResourceBudgetRecord,
    BackendPluginResourceBudgetReport,
    assert_backend_plugin_resource_budget,
    backend_plugin_resource_budget_report_to_dict,
    build_backend_plugin_resource_budget_report,
    dump_backend_plugin_resource_budget_report,
)

SCHEMA_PATH = Path("schemas/backend_plugin_resource_budget_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/backend_plugin_resource_budget/current_report.json")
_DIGEST = "sha256:8b4f6d3c2a1e0f9d8c7b6a594837261504f3e2d1c0b9a897867564534231201f"


def test_backend_plugin_resource_budget_is_data_only_and_ready() -> None:
    report = build_current_backend_plugin_resource_budget_report()

    assert report.budget_ready
    assert not report.execution_allowed
    assert report.execution_permission == BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION
    assert report.resource_budget_contract == BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    assert report.budget_policy == BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY
    assert report.budget_status == BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS
    assert report.required_bindings == BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS
    assert report.blocked_execution_surfaces == RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    assert report.budget_count == 1
    assert report.issues == ()

    budget = report.budgets[0]
    assert budget.artifact_digest == _DIGEST
    assert budget.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    assert budget.provenance_contract == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    assert budget.budget_scope == "generated_artifact_execution"
    assert budget.budget_status == "reviewed_static_bounds"
    assert budget.cpu_time_limit_ms <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CPU_TIME_MS
    assert budget.memory_limit_bytes <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES
    assert budget.output_limit_bytes <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_OUTPUT_BYTES
    assert budget.artifact_size_limit_bytes <= (
        MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ARTIFACT_BYTES
    )
    assert budget.cache_entry_limit <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CACHE_ENTRIES
    assert budget.diagnostics_limit_bytes <= (
        MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_DIAGNOSTICS_BYTES
    )


def test_backend_plugin_resource_budget_assertion_passes() -> None:
    report = build_current_backend_plugin_resource_budget_report()

    assert assert_backend_plugin_resource_budget(report) is report


def test_backend_plugin_resource_budget_rejects_hand_written_issues() -> None:
    report = build_current_backend_plugin_resource_budget_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginResourceBudgetReport(
            budgets=report.budgets,
            issues=(
                BackendPluginResourceBudgetIssue(
                    budget_id=report.budgets[0].budget_id,
                    issue_code="duplicate_budget_id",
                ),
            ),
        )


def test_backend_plugin_resource_budget_assertion_rejects_duplicates() -> None:
    budget = build_current_backend_plugin_resource_budget_report().budgets[0]
    report = BackendPluginResourceBudgetReport(
        budgets=(budget, budget),
        issues=(
            BackendPluginResourceBudgetIssue(
                budget_id=budget.budget_id,
                issue_code="duplicate_budget_id",
            ),
        ),
    )

    assert not report.budget_ready
    with pytest.raises(BackendPluginResourceBudgetError, match="duplicate_budget_id"):
        assert_backend_plugin_resource_budget(report)


def test_backend_plugin_resource_budget_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="sha256"):
        _make_budget(artifact_digest="sha256:not-valid")


def test_backend_plugin_resource_budget_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        _make_budget(cpu_time_limit_ms=0)


def test_backend_plugin_resource_budget_rejects_limits_above_policy() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        _make_budget(memory_limit_bytes=MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES + 1)


def test_backend_plugin_resource_budget_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        _make_budget(budget_id="python_module")


def test_backend_plugin_resource_budget_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_plugin_resource_budget.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["budget_ready"] is True
    assert loaded["execution_allowed"] is False
    assert loaded["execution_permission"] == "not_granted"


def test_backend_plugin_resource_budget_dump_matches_golden() -> None:
    report = build_backend_plugin_resource_budget_report()

    assert dump_backend_plugin_resource_budget_report(
        report
    ) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_backend_plugin_resource_budget_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_plugin_resource_budget_report_to_dict(object())  # type: ignore[arg-type]


def test_backend_plugin_resource_budget_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_plugin_resource_budget_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["resource_budget_contract"]["const"] == (
        BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    )
    assert schema["properties"]["budget_policy"]["const"] == (
        BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY
    )
    assert schema["properties"]["budget_status"]["const"] == (
        BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS
    )
    assert schema["properties"]["execution_allowed"]["const"] is False
    assert schema["properties"]["execution_permission"]["const"] == "not_granted"
    assert schema["properties"]["budget_count"]["const"] == 1
    assert schema["properties"]["budgets"]["maxItems"] <= (
        MAX_BACKEND_PLUGIN_RESOURCE_BUDGETS
    )
    assert [
        item["const"]
        for item in schema["properties"]["required_bindings"]["prefixItems"]
    ] == list(BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS)
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    budget_schema = schema["$defs"]["budget"]
    assert budget_schema["properties"]["artifact_digest"]["$ref"].endswith(
        "sha256_digest"
    )
    assert budget_schema["properties"]["sandbox_model_contract"]["const"] == (
        BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    )
    assert budget_schema["properties"]["provenance_contract"]["const"] == (
        BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    )
    assert budget_schema["properties"]["memory_limit_bytes"]["maximum"] == (
        MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES
    )


def test_backend_plugin_resource_budget_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "artifact_bytes",
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "python_module",
        "generated_code",
        "raw_benchmark_output",
        "raw_timing_samples",
        "url",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["budget"]["properties"]
        assert forbidden not in schema["$defs"]["budget_issue"]["properties"]
    assert "python_module" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["sha256_digest"]["pattern"] == "^sha256:[0-9a-f]{64}$"
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_plugin_resource_budget_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_SCHEMA_VERSION
    assert golden["resource_budget_contract"] == BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["execution_allowed"] is False
    assert golden["execution_permission"] == "not_granted"
    assert golden["budget_ready"] is True
    assert golden["budget_count"] == len(golden["budgets"]) == 1
    assert golden["issues"] == []
    budget = golden["budgets"][0]
    assert budget["artifact_digest"] == _DIGEST
    assert budget["sandbox_model_contract"] == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    assert budget["provenance_contract"] == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT


def test_backend_plugin_resource_budget_schema_is_referenced() -> None:
    schema_path = "schemas/backend_plugin_resource_budget_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_PLUGIN_RESOURCE_BUDGET.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0220-backend-plugin-resource-budget.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _make_budget(**overrides: object) -> BackendPluginResourceBudgetRecord:
    values: dict[str, object] = {
        "artifact_digest": _DIGEST,
        "artifact_id": "external_vector_lowering_artifact",
        "artifact_size_limit_bytes": 1024 * 1024,
        "budget_id": "external_vector_lowering_resource_budget",
        "budget_scope": "generated_artifact_execution",
        "budget_status": "reviewed_static_bounds",
        "cache_entry_limit": 4,
        "cpu_time_limit_ms": 1000,
        "diagnostics_limit_bytes": 32 * 1024,
        "memory_limit_bytes": 64 * 1024 * 1024,
        "output_limit_bytes": 256 * 1024,
        "provenance_contract": BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
        "sandbox_model_contract": BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    }
    values.update(overrides)
    return BackendPluginResourceBudgetRecord(**values)  # type: ignore[arg-type]


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
