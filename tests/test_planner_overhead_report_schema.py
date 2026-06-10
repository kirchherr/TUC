from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from examples.phase1_ir_pipeline import build_graph
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.benchmarks import (
    MAX_PLANNER_OVERHEAD_DURATION_NS,
    MAX_PLANNER_OVERHEAD_PHASES,
    PLANNER_OVERHEAD_ARTIFACT_STATUS,
    PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
    PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
    PLANNER_OVERHEAD_NOT_MEASURED_ISSUES,
    PLANNER_OVERHEAD_PHASES,
    PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
    measure_pipeline_planner_overhead,
    planner_overhead_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/planner_overhead_report.v0.schema.json")


def test_planner_overhead_report_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/planner_overhead_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        PLANNER_OVERHEAD_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["execution_time_status"]["const"] == (
        PLANNER_OVERHEAD_EXECUTION_TIME_STATUS
    )
    assert schema["properties"]["break_even_status"]["const"] == (
        PLANNER_OVERHEAD_BREAK_EVEN_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["phase_timings"]["maxItems"] == (
        MAX_PLANNER_OVERHEAD_PHASES
    )
    assert schema["properties"]["total_planning_ns"]["maximum"] == (
        MAX_PLANNER_OVERHEAD_DURATION_NS
    )
    assert schema["$defs"]["phase_name"]["enum"] == list(PLANNER_OVERHEAD_PHASES)
    assert schema["$defs"]["issue_id"]["enum"] == list(
        PLANNER_OVERHEAD_NOT_MEASURED_ISSUES
    )


def test_planner_overhead_report_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["properties"]
    assert "device_id" not in schema["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]
    assert schema["$defs"]["phase_timing"]["properties"][
        "included_in_execution_time"
    ]["const"] is False


def test_planner_overhead_report_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    simulator = LinearAlgebraSimulatorBackend()
    measurement = measure_pipeline_planner_overhead(
        build_graph(),
        [simulator.capability],
    )
    payload = planner_overhead_report_to_dict(measurement.report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION
    assert payload["execution_time_status"] == PLANNER_OVERHEAD_EXECUTION_TIME_STATUS
    assert payload["break_even_status"] == PLANNER_OVERHEAD_BREAK_EVEN_STATUS
    assert payload["planner_overhead_hidden_in_execution_time"] is False


def test_planner_overhead_report_schema_is_referenced() -> None:
    schema_path = "schemas/planner_overhead_report.v0.schema.json"

    for path in (
        Path("docs/PLANNER_OVERHEAD_REPORT.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0066-planner-overhead-report.md"),
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
