from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
    RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime import MAX_RUNTIME_EXECUTOR_CONFORMANCE_CASES

SCHEMA_PATH = Path("schemas/runtime_executor_conformance_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json"
)


def test_runtime_executor_conformance_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_executor_conformance_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["conformance_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["trusted_executor_registry"]["const"] == (
        TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    )
    assert schema["properties"]["checked_cases"]["maxItems"] == (
        MAX_RUNTIME_EXECUTOR_CONFORMANCE_CASES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    assert schema["$defs"]["checked_case"]["properties"]["operation_kind"]["enum"] == [
        "matmul",
        "elementwise",
        "reduction",
        "softmax",
    ]


def test_runtime_executor_conformance_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["checked_case"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_runtime_executor_conformance_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert golden["conformance_contract"] == RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["case_count"] == len(golden["checked_cases"]) == 16
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["checked_cases"][0]["case_name"] == "linear-sim_matmul_supported"
    assert golden["checked_cases"][1]["observed_status"] == "rejected"
    assert golden["checked_cases"][-1]["case_name"] == "vector-sim_softmax_supported"


def test_runtime_executor_conformance_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_executor_conformance_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_EXECUTOR_CONFORMANCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0090-runtime-executor-conformance.md"),
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
