from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc.frontend import (
    MAX_TRITON_IDIOM_COVERAGE_ITEMS,
    TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS,
    TRITON_IDIOM_COVERAGE_CONTRACT,
    TRITON_IDIOM_COVERAGE_PARSER_STATUS,
    TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION,
    TRITON_IDIOM_COVERAGE_STATUSES,
)
from tuc.ir import OperationKind

SCHEMA_PATH = Path("schemas/triton_idiom_coverage_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/triton_idiom_coverage_report.json")


def test_triton_idiom_coverage_report_schema_matches_runtime() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/triton_idiom_coverage_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS
    )
    assert schema["properties"]["coverage_contract"]["const"] == (
        TRITON_IDIOM_COVERAGE_CONTRACT
    )
    assert schema["properties"]["parser_status"]["const"] == (
        TRITON_IDIOM_COVERAGE_PARSER_STATUS
    )
    assert schema["properties"]["coverages"]["maxItems"] == (
        MAX_TRITON_IDIOM_COVERAGE_ITEMS
    )
    assert schema["$defs"]["coverage"]["properties"]["coverage_status"]["enum"] == (
        list(TRITON_IDIOM_COVERAGE_STATUSES)
    )
    assert schema["$defs"]["coverage"]["properties"]["operation_family"]["enum"] == [
        kind.value for kind in OperationKind
    ]


def test_triton_idiom_coverage_report_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["coverage"]["properties"]
    assert schema["properties"]["direct_triton_source_ingestion"]["const"] is False
    assert schema["$defs"]["report_text"]["maxLength"] == 512
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_triton_idiom_coverage_report_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS
    assert golden["coverage_contract"] == TRITON_IDIOM_COVERAGE_CONTRACT
    assert golden["direct_triton_source_ingestion"] is False
    assert golden["parser_status"] == TRITON_IDIOM_COVERAGE_PARSER_STATUS
    assert golden["triton_idiom_coverage_ready"] is True
    assert golden["issues"] == []
    assert [item["operation_family"] for item in golden["coverages"]] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]


def test_triton_idiom_coverage_report_schema_is_referenced() -> None:
    schema_path = "schemas/triton_idiom_coverage_report.v0.schema.json"

    for path in (
        Path("docs/TRITON_IDIOM_COVERAGE_REPORT.md"),
        Path("docs/FRONTEND_ADAPTER.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0079-triton-idiom-coverage-report.md"),
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
