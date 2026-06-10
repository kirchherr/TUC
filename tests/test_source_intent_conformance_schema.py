from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc.frontend import (
    MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES,
    SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION,
)

SCHEMA_PATH = Path(
    "schemas/source_intent_frontend_conformance_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/source_intent_frontend_conformance_report.json"
)


def test_source_intent_frontend_conformance_report_schema_matches_runtime() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/source_intent_frontend_conformance_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["checked_cases"]["maxItems"] == (
        MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES
    )
    assert schema["properties"]["accepted_case_count"]["maximum"] == (
        MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES
    )
    assert schema["properties"]["rejected_case_count"]["maximum"] == (
        MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES
    )


def test_source_intent_frontend_conformance_report_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "payload" not in schema["properties"]
    assert "source_text" not in schema["properties"]
    assert "file_path" not in schema["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "raw_payload" not in schema["$defs"]["issue"]["properties"]
    assert schema["$defs"]["report_text"]["maxLength"] == 512


def test_source_intent_frontend_conformance_report_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert len(golden["checked_cases"]) == (
        golden["accepted_case_count"] + golden["rejected_case_count"]
    )
    assert golden["passed"] is True
    assert golden["issues"] == []


def test_source_intent_frontend_conformance_report_schema_is_referenced() -> None:
    schema_path = "schemas/source_intent_frontend_conformance_report.v0.schema.json"

    for path in (
        Path("docs/SOURCE_INTENT_FRONTEND_CONFORMANCE.md"),
        Path("rfcs/0060-source-intent-frontend-conformance-report-schema.md"),
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
