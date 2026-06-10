from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    BENCHMARK_METHODOLOGY_ARTIFACT_STATUS,
    BENCHMARK_METHODOLOGY_CLAIM_STATUS,
    BENCHMARK_METHODOLOGY_CLOCKS,
    BENCHMARK_METHODOLOGY_ISOLATION_LEVELS,
    BENCHMARK_METHODOLOGY_MAX_ITERATIONS,
    BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION,
    BENCHMARK_METHODOLOGY_STATISTIC_POLICIES,
    BenchmarkMethodology,
    benchmark_methodology_report_to_dict,
    build_benchmark_methodology_report,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/benchmark_methodology_report.v0.schema.json")


def test_benchmark_methodology_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/benchmark_methodology_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        BENCHMARK_METHODOLOGY_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        BENCHMARK_METHODOLOGY_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["methodologies"]["maxItems"] == 128
    assert schema["$defs"]["measurement_clock"]["enum"] == list(
        BENCHMARK_METHODOLOGY_CLOCKS
    )
    assert schema["$defs"]["statistic_policy"]["enum"] == list(
        BENCHMARK_METHODOLOGY_STATISTIC_POLICIES
    )
    assert schema["$defs"]["isolation_level"]["enum"] == list(
        BENCHMARK_METHODOLOGY_ISOLATION_LEVELS
    )
    methodology = schema["$defs"]["benchmark_methodology"]
    assert methodology["properties"]["measurement_iterations"]["maximum"] == (
        BENCHMARK_METHODOLOGY_MAX_ITERATIONS
    )


def test_benchmark_methodology_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["benchmark_methodology"]["properties"]
    assert "environment" not in schema["$defs"]["benchmark_methodology"]["properties"]
    assert "device_id" not in schema["$defs"]["benchmark_methodology"]["properties"]
    assert (
        "hardware_serial"
        not in schema["$defs"]["benchmark_methodology"]["properties"]
    )
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_benchmark_methodology_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_benchmark_methodology_report(
        "phase1_benchmark_methodology_candidate",
        methodologies=(
            BenchmarkMethodology(
                methodology_id="phase1_cpu_baseline_methodology",
                workload_scope_id="phase1_mlp_matmul_64x64",
                measurement_clock="monotonic_ns",
                warmup_iterations=3,
                measurement_iterations=20,
                statistic_policy="min_median_mean",
                isolation_level="process_isolated",
                outlier_policy_id="no_raw_sample_storage",
                reproducibility_policy_id="docker_dev_container",
            ),
        ),
    )
    payload = benchmark_methodology_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_benchmark_methodology_schema_is_referenced() -> None:
    schema_path = "schemas/benchmark_methodology_report.v0.schema.json"

    for path in (
        Path("docs/BENCHMARK_METHODOLOGY_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0071-benchmark-methodology-report.md"),
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
