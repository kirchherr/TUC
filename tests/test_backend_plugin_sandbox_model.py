from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_plugin_sandbox_model import (
    build_current_backend_plugin_sandbox_model_report,
)
from tuc import (
    BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    BACKEND_PLUGIN_SANDBOX_MODEL_REPORT_SCHEMA_VERSION,
    BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS,
    MAX_BACKEND_PLUGIN_SANDBOX_CONTROLS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendPluginSandboxControl,
    BackendPluginSandboxIssue,
    BackendPluginSandboxModelReport,
    assert_backend_plugin_sandbox_model,
    backend_plugin_sandbox_model_report_to_dict,
    build_backend_plugin_sandbox_model_report,
    dump_backend_plugin_sandbox_model_report,
)

SCHEMA_PATH = Path("schemas/backend_plugin_sandbox_model_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/backend_plugin_sandbox_model/current_report.json")


def test_backend_plugin_sandbox_model_is_data_only_and_ready() -> None:
    report = build_current_backend_plugin_sandbox_model_report()

    assert report.model_ready
    assert not report.execution_allowed
    assert report.execution_permission == "not_granted"
    assert report.isolation_strategy == "separate_worker_process_or_container_required"
    assert tuple(control.control_id for control in report.controls) == (
        BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS
    )
    assert {control.status for control in report.controls} == {"required"}
    assert report.issues == ()


def test_backend_plugin_sandbox_model_assertion_passes() -> None:
    report = build_current_backend_plugin_sandbox_model_report()

    assert assert_backend_plugin_sandbox_model(report) is report


def test_backend_plugin_sandbox_model_rejects_hand_written_issues() -> None:
    report = build_current_backend_plugin_sandbox_model_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginSandboxModelReport(
            controls=report.controls,
            issues=(
                BackendPluginSandboxIssue(
                    subject="execution_permission",
                    issue_code="execution_permission_granted",
                ),
            ),
        )


def test_backend_plugin_sandbox_model_rejects_missing_required_control() -> None:
    report = build_current_backend_plugin_sandbox_model_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginSandboxModelReport(
            controls=report.controls[:-1],
            issues=(),
        )


def test_backend_plugin_sandbox_model_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        BackendPluginSandboxControl(
            control_id="python_module",
            status="required",
            protects_surface="backend_plugin_discovery",
        )


def test_backend_plugin_sandbox_model_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_plugin_sandbox_model.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["model_ready"] is True
    assert loaded["execution_allowed"] is False
    assert loaded["control_count"] == 12


def test_backend_plugin_sandbox_model_dump_matches_golden() -> None:
    report = build_backend_plugin_sandbox_model_report()

    assert dump_backend_plugin_sandbox_model_report(
        report
    ) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_backend_plugin_sandbox_model_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_plugin_sandbox_model_report_to_dict(object())  # type: ignore[arg-type]


def test_backend_plugin_sandbox_model_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_plugin_sandbox_model_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_PLUGIN_SANDBOX_MODEL_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["sandbox_contract"]["const"] == (
        BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    )
    assert schema["properties"]["model_ready"]["const"] is True
    assert schema["properties"]["execution_allowed"]["const"] is False
    assert schema["properties"]["execution_permission"]["const"] == "not_granted"
    assert schema["properties"]["control_count"]["const"] == 12
    assert schema["properties"]["controls"]["maxItems"] == (
        len(BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS)
    )
    assert (
        schema["properties"]["controls"]["maxItems"]
    ) <= MAX_BACKEND_PLUGIN_SANDBOX_CONTROLS
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_backend_plugin_sandbox_model_schema_fails_closed() -> None:
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
        "python_module",
        "generated_code",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["control"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_module" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_plugin_sandbox_model_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == BACKEND_PLUGIN_SANDBOX_MODEL_REPORT_SCHEMA_VERSION
    assert golden["sandbox_contract"] == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["model_ready"] is True
    assert golden["execution_allowed"] is False
    assert golden["control_count"] == len(golden["controls"]) == 12
    assert golden["issues"] == []


def test_backend_plugin_sandbox_model_schema_is_referenced() -> None:
    schema_path = "schemas/backend_plugin_sandbox_model_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_PLUGIN_SANDBOX_MODEL.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0218-backend-plugin-sandbox-model.md"),
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
