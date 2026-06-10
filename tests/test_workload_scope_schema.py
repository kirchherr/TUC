from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    WORKLOAD_OPERATION_FAMILIES,
    WORKLOAD_SCOPE_ARTIFACT_STATUS,
    WORKLOAD_SCOPE_CLAIM_STATUS,
    WORKLOAD_SCOPE_MAX_PROBLEM_SIZE,
    WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
    WorkloadScope,
    build_workload_scope_report,
    workload_scope_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/workload_scope_report.v0.schema.json")


def test_workload_scope_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/workload_scope_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        WORKLOAD_SCOPE_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        WORKLOAD_SCOPE_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["scopes"]["maxItems"] == 128
    assert schema["$defs"]["operation_family"]["enum"] == list(
        WORKLOAD_OPERATION_FAMILIES
    )
    assert schema["$defs"]["problem_size"]["maximum"] == (
        WORKLOAD_SCOPE_MAX_PROBLEM_SIZE
    )


def test_workload_scope_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "tensor_values" not in schema["$defs"]["workload_scope"]["properties"]
    assert "host_path" not in schema["$defs"]["workload_scope"]["properties"]
    assert "device_id" not in schema["$defs"]["workload_scope"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["workload_scope"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_workload_scope_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_workload_scope_report(
        "phase1_workload_scope_candidate",
        scopes=(
            WorkloadScope(
                scope_id="phase1_mlp_matmul_64x64",
                operation_family="matmul",
                shape_profile_id="square_64x64",
                dtype_policy_id="float64_reference",
                problem_size_min=4096,
                problem_size_max=4096,
                correctness_reference_id="numpy_reference_matmul",
            ),
        ),
    )
    payload = workload_scope_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_workload_scope_schema_is_referenced() -> None:
    schema_path = "schemas/workload_scope_report.v0.schema.json"

    for path in (
        Path("docs/WORKLOAD_SCOPE_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0070-workload-scope-report.md"),
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
