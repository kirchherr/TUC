from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS,
    BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS,
    BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION,
    BREAK_EVEN_WORKLOAD_SIZE_STATUSES,
    BreakEvenWorkloadSize,
    break_even_workload_size_report_to_dict,
    build_break_even_workload_size_report,
)
from tuc.proof import (
    MAX_BREAK_EVEN_WORKLOAD_SIZE,
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
)

SCHEMA_PATH = Path("schemas/break_even_workload_size_report.v0.schema.json")


def test_break_even_workload_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/break_even_workload_size_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["workloads"]["maxItems"] == 128
    assert schema["$defs"]["break_even_status"]["enum"] == list(
        BREAK_EVEN_WORKLOAD_SIZE_STATUSES
    )
    assert schema["$defs"]["break_even_problem_size"]["maximum"] == (
        MAX_BREAK_EVEN_WORKLOAD_SIZE
    )


def test_break_even_workload_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["break_even_workload"]["properties"]
    assert "environment" not in schema["$defs"]["break_even_workload"]["properties"]
    assert "device_id" not in schema["$defs"]["break_even_workload"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["break_even_workload"][
        "properties"
    ]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_break_even_workload_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_break_even_workload_size_report(
        "phase1_break_even_candidate",
        workloads=(
            BreakEvenWorkloadSize(
                break_even_id="matmul64_break_even",
                workload_scope_id="matmul64_scope",
                planner_overhead_report_id="planner_overhead_report",
                execution_metric_id="median_execution_time_ns",
                amortization_policy_id="single_compile_many_runs",
                break_even_status="validated_by_ci",
                break_even_problem_size=4096,
                evidence_digest="sha256:" + ("0123456789abcdef" * 4),
            ),
        ),
    )
    payload = break_even_workload_size_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_break_even_workload_schema_is_referenced() -> None:
    schema_path = "schemas/break_even_workload_size_report.v0.schema.json"

    for path in (
        Path("docs/BREAK_EVEN_WORKLOAD_SIZE_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0074-break-even-workload-size-report.md"),
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
