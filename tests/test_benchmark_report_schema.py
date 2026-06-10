from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc.benchmarks import (
    BENCHMARK_REPORT_ARTIFACT_STATUS,
    BENCHMARK_REPORT_CLAIM_BOUNDARY,
    BENCHMARK_REPORT_SCHEMA_VERSION,
    BENCHMARK_SUITE_VERSION,
    MAX_BENCHMARK_DEVICES,
    MAX_BENCHMARK_ITERATIONS,
    MAX_BENCHMARK_RESULTS,
    MAX_BENCHMARK_WARMUP,
    run_baseline_benchmarks,
)

SCHEMA_PATH = Path("schemas/baseline_benchmark_report.v0.schema.json")


def test_baseline_benchmark_report_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/baseline_benchmark_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BENCHMARK_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["suite_version"]["const"] == BENCHMARK_SUITE_VERSION
    assert schema["properties"]["artifact_status"]["const"] == (
        BENCHMARK_REPORT_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        BENCHMARK_REPORT_CLAIM_BOUNDARY
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["results"]["maxItems"] == MAX_BENCHMARK_RESULTS
    assert schema["properties"]["devices"]["maxItems"] == MAX_BENCHMARK_DEVICES

    result = schema["$defs"]["result"]
    assert result["properties"]["iterations"]["maximum"] == MAX_BENCHMARK_ITERATIONS
    assert result["properties"]["warmup"]["maximum"] == MAX_BENCHMARK_WARMUP


def test_baseline_benchmark_report_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "host_path" not in schema["properties"]
    assert "device_id" not in schema["$defs"]["device_status"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["device_status"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]
    assert "raw_timing_samples" not in schema["$defs"]["result"]["properties"]
    assert schema["$defs"]["report_text"]["maxLength"] == 256


def test_baseline_benchmark_report_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = run_baseline_benchmarks(iterations=1, warmup=0, include_cuda=True)
    payload = report.to_mapping()

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == BENCHMARK_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == BENCHMARK_REPORT_ARTIFACT_STATUS
    assert payload["claim_boundary"] == BENCHMARK_REPORT_CLAIM_BOUNDARY
    assert payload["native_performance_claim"] is False
    assert len(payload["results"]) == 4
    assert len(payload["devices"]) == 2


def test_baseline_benchmark_report_schema_is_referenced() -> None:
    schema_path = "schemas/baseline_benchmark_report.v0.schema.json"

    for path in (
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0065-baseline-benchmark-report-schema.md"),
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
