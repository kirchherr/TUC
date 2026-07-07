from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.triton_integration_readiness import (
    build_current_triton_integration_readiness_report,
)
from examples.triton_integration_readiness import (
    build_report as build_example_report,
)
from tuc.frontend import (
    MAX_TRITON_INTEGRATION_READINESS_PREREQUISITES,
    TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS,
    TRITON_INTEGRATION_READINESS_BLOCKED_EXECUTION_SURFACES,
    TRITON_INTEGRATION_READINESS_CONTRACT,
    TRITON_INTEGRATION_READINESS_DEFAULT_ISSUES,
    TRITON_INTEGRATION_READINESS_PREREQUISITE_STATUSES,
    TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION,
    TRITON_INTEGRATION_READINESS_TARGET,
    TritonIntegrationReadinessPrerequisite,
    build_triton_integration_readiness_report,
    triton_integration_readiness_report_to_dict,
)

SCHEMA_PATH = Path("schemas/triton_integration_readiness_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/triton_integration_readiness_report.json")


def test_current_triton_integration_readiness_is_blocked_but_informative() -> None:
    report = build_current_triton_integration_readiness_report()
    payload = triton_integration_readiness_report_to_dict(report)

    assert payload["schema_version"] == TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS
    assert payload["readiness_contract"] == TRITON_INTEGRATION_READINESS_CONTRACT
    assert payload["integration_target"] == TRITON_INTEGRATION_READINESS_TARGET
    assert payload["integration_status"] == "not_ready"
    assert payload["readiness_ready"] is False
    assert payload["direct_triton_source_ingestion"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["satisfied_prerequisite_count"] == 14
    assert payload["missing_prerequisite_count"] == 1
    assert payload["blocked_prerequisite_count"] == 2
    assert payload["issues"] == list(TRITON_INTEGRATION_READINESS_DEFAULT_ISSUES)
    assert "jit_execution" in payload["blocked_execution_surfaces"]


def test_triton_integration_readiness_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_triton_integration_readiness_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/triton_integration_readiness.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"readiness_ready": false' in completed.stdout
    assert '"direct_triton_source_ingestion": false' in completed.stdout
    assert '"triton_jit_execution": false' in completed.stdout
    assert "python_source" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_triton_integration_readiness_can_be_ready_without_jit_permission() -> None:
    report = build_triton_integration_readiness_report(
        "ready_without_jit",
        (
            TritonIntegrationReadinessPrerequisite("parser_rfc", "satisfied", "rfc"),
            TritonIntegrationReadinessPrerequisite(
                "triton_jit_execution_permission",
                "blocked_by_policy",
                "docs.TRITON_SOURCE_THREAT_MODEL",
                required_for_readiness=False,
            ),
        ),
    )
    payload = triton_integration_readiness_report_to_dict(report)

    assert payload["readiness_ready"] is True
    assert payload["integration_status"] == "ready"
    assert payload["triton_jit_execution"] is False
    assert payload["issues"] == ["triton_jit_execution_blocked"]


def test_triton_integration_readiness_rejects_duplicate_prerequisites() -> None:
    item = TritonIntegrationReadinessPrerequisite("parser_rfc", "satisfied", "rfc")

    with pytest.raises(ValueError, match="duplicate triton integration"):
        build_triton_integration_readiness_report("duplicate", (item, item))


def test_triton_integration_readiness_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="safe triton integration identifier"):
        build_triton_integration_readiness_report(
            "bad",
            (
                TritonIntegrationReadinessPrerequisite(
                    "../source.py",
                    "satisfied",
                    "rfc",
                ),
            ),
        )


def test_triton_integration_readiness_rejects_execution_surface_ids() -> None:
    with pytest.raises(ValueError, match="safe triton integration identifier"):
        build_triton_integration_readiness_report(
            "python_source",
            (TritonIntegrationReadinessPrerequisite("parser_rfc", "satisfied", "rfc"),),
        )


def test_triton_integration_readiness_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="unsupported triton integration"):
        build_triton_integration_readiness_report(
            "bad_status",
            (TritonIntegrationReadinessPrerequisite("parser_rfc", "unknown", "rfc"),),
        )


def test_triton_integration_readiness_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/triton_integration_readiness_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS
    )
    assert schema["properties"]["readiness_contract"]["const"] == (
        TRITON_INTEGRATION_READINESS_CONTRACT
    )
    assert schema["properties"]["integration_target"]["const"] == (
        TRITON_INTEGRATION_READINESS_TARGET
    )
    assert schema["properties"]["direct_triton_source_ingestion"]["const"] is False
    assert schema["properties"]["triton_jit_execution"]["const"] is False
    assert schema["properties"]["prerequisites"]["maxItems"] == (
        MAX_TRITON_INTEGRATION_READINESS_PREREQUISITES
    )
    assert schema["$defs"]["prerequisite"]["properties"]["status"]["enum"] == list(
        TRITON_INTEGRATION_READINESS_PREREQUISITE_STATUSES
    )


def test_triton_integration_readiness_schema_fails_closed() -> None:
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
        "raw_timing_samples",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["prerequisite"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]


def test_triton_integration_readiness_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS
    assert golden["readiness_ready"] is False
    assert golden["direct_triton_source_ingestion"] is False
    assert golden["triton_jit_execution"] is False
    assert len(golden["blocked_execution_surfaces"]) == len(
        TRITON_INTEGRATION_READINESS_BLOCKED_EXECUTION_SURFACES
    )


def test_triton_integration_readiness_is_documented() -> None:
    schema_path = "schemas/triton_integration_readiness_report.v0.schema.json"
    example_path = "examples/triton_integration_readiness.py"

    for path in (
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("README.md"),
        Path("rfcs/0241-triton-integration-readiness.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text


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