from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    RUNTIME_EVIDENCE_ARTIFACT_KINDS,
    RUNTIME_EVIDENCE_MATRIX_ARTIFACT_STATUS,
    RUNTIME_EVIDENCE_MATRIX_CONTRACT,
    RUNTIME_EVIDENCE_MATRIX_REPORT_SCHEMA_VERSION,
    RUNTIME_EVIDENCE_MATRIX_SOURCE_BOUNDARIES,
    RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS,
)

SCHEMA_PATH = Path("schemas/runtime_evidence_matrix_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/runtime_evidence_matrix_report.json")


def test_runtime_evidence_matrix_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_evidence_matrix_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_EVIDENCE_MATRIX_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_EVIDENCE_MATRIX_ARTIFACT_STATUS
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_EVIDENCE_MATRIX_CONTRACT
    )
    assert schema["properties"]["graphs"]["maxItems"] == 64
    assert schema["$defs"]["graph"]["properties"]["artifacts"]["maxItems"] == 32
    assert schema["$defs"]["artifact_kind"]["enum"] == list(
        RUNTIME_EVIDENCE_ARTIFACT_KINDS
    )
    assert schema["$defs"]["graph"]["properties"]["source_boundary"]["enum"] == list(
        RUNTIME_EVIDENCE_MATRIX_SOURCE_BOUNDARIES
    )


def test_runtime_evidence_matrix_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["graph"]["properties"]
        assert forbidden not in schema["$defs"]["artifact"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z][A-Za-z0-9_.-]*$"
    )


def test_runtime_evidence_matrix_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_EVIDENCE_MATRIX_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_EVIDENCE_MATRIX_ARTIFACT_STATUS
    assert golden["evidence_contract"] == RUNTIME_EVIDENCE_MATRIX_CONTRACT
    assert golden["required_artifact_kinds"] == list(
        RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS
    )
    assert golden["runtime_evidence_matrix_complete"] is True
    assert golden["graph_count"] == len(golden["graphs"]) == 7
    assert golden["issues"] == []
    assert all(graph["runtime_evidence_complete"] for graph in golden["graphs"])
    assert golden["graphs"][-1]["graph_id"] == "source_intent_return_mlp"
    assert golden["graphs"][-1]["runtime_evidence_complete"] is True
    assert {
        artifact["artifact_kind"]
        for artifact in golden["graphs"][-1]["artifacts"]
    } >= {
        "source_intent_return_semantics",
        "source_intent_runtime_returns",
    }


def test_runtime_evidence_matrix_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_evidence_matrix_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_EVIDENCE_MATRIX.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0087-runtime-evidence-matrix.md"),
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
