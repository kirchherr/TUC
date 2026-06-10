from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS,
    NATIVE_BASELINE_COMPARISON_CLAIM_STATUS,
    NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION,
    NATIVE_BASELINE_COMPARISON_RESULT_STATUSES,
    NativeBaselineComparison,
    build_native_baseline_comparison_report,
    native_baseline_comparison_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/native_baseline_comparison_report.v0.schema.json")


def test_native_baseline_comparison_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/native_baseline_comparison_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        NATIVE_BASELINE_COMPARISON_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["comparisons"]["maxItems"] == 128
    assert schema["$defs"]["result_status"]["enum"] == list(
        NATIVE_BASELINE_COMPARISON_RESULT_STATUSES
    )


def test_native_baseline_comparison_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["native_baseline_comparison"]["properties"]
    assert "environment" not in schema["$defs"]["native_baseline_comparison"]["properties"]
    assert "device_id" not in schema["$defs"]["native_baseline_comparison"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["native_baseline_comparison"][
        "properties"
    ]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_native_baseline_comparison_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_native_baseline_comparison_report(
        "phase1_native_comparison_candidate",
        comparisons=(
            NativeBaselineComparison(
                comparison_id="matmul64_native_comparison",
                workload_scope_id="matmul64_scope",
                baseline_artifact_id="baseline_report",
                native_artifact_id="native_report",
                comparison_metric_id="median_execution_time_ns",
                summary_policy_id="median_iqr",
                result_status="validated_by_ci",
                comparison_digest="sha256:" + ("0123456789abcdef" * 4),
            ),
        ),
    )
    payload = native_baseline_comparison_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_native_baseline_comparison_schema_is_referenced() -> None:
    schema_path = "schemas/native_baseline_comparison_report.v0.schema.json"

    for path in (
        Path("docs/NATIVE_BASELINE_COMPARISON_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0073-native-baseline-comparison-report.md"),
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
