from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    TOOLCHAIN_COMPONENT_KINDS,
    TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS,
    TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS,
    TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION,
    ToolchainComponent,
    build_toolchain_environment_report,
    toolchain_environment_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/toolchain_environment_report.v0.schema.json")


def test_toolchain_environment_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/toolchain_environment_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["components"]["maxItems"] == 128
    assert schema["$defs"]["component_kind"]["enum"] == list(
        TOOLCHAIN_COMPONENT_KINDS
    )


def test_toolchain_environment_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["toolchain_component"]["properties"]
    assert "environment" not in schema["$defs"]["toolchain_component"]["properties"]
    assert "device_id" not in schema["$defs"]["toolchain_component"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["toolchain_component"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_toolchain_environment_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_toolchain_environment_report(
        "phase1_toolchain_environment_candidate",
        components=(
            ToolchainComponent(
                component_id="python_runtime",
                component_kind="python_runtime",
                version_id="python_3.11",
                provenance_id="docker_dev_container",
                component_digest="sha256:" + ("0123456789abcdef" * 4),
            ),
        ),
    )
    payload = toolchain_environment_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_toolchain_environment_schema_is_referenced() -> None:
    schema_path = "schemas/toolchain_environment_report.v0.schema.json"

    for path in (
        Path("docs/TOOLCHAIN_ENVIRONMENT_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0072-toolchain-environment-report.md"),
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
