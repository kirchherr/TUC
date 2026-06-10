from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    BENCHMARK_ARTIFACT_KINDS,
    BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS,
    BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS,
    BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION,
    BENCHMARK_ARTIFACT_REQUIRED_KINDS,
    BENCHMARK_ARTIFACT_STORAGE_SCOPES,
    BenchmarkArtifactReference,
    benchmark_artifact_manifest_report_to_dict,
    build_benchmark_artifact_manifest_report,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/benchmark_artifact_manifest_report.v0.schema.json")


def test_benchmark_artifact_manifest_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/benchmark_artifact_manifest_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["required_artifact_kinds"]["const"] == list(
        BENCHMARK_ARTIFACT_REQUIRED_KINDS
    )
    assert schema["properties"]["artifacts"]["maxItems"] == 128
    assert schema["$defs"]["artifact_kind"]["enum"] == list(BENCHMARK_ARTIFACT_KINDS)
    assert schema["$defs"]["storage_scope"]["enum"] == list(
        BENCHMARK_ARTIFACT_STORAGE_SCOPES
    )


def test_benchmark_artifact_manifest_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["benchmark_artifact"]["properties"]
    assert "url" not in schema["$defs"]["benchmark_artifact"]["properties"]
    assert "device_id" not in schema["$defs"]["benchmark_artifact"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["benchmark_artifact"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_benchmark_artifact_manifest_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_benchmark_artifact_manifest_report(
        "phase1_benchmark_manifest_candidate",
        artifacts=(
            BenchmarkArtifactReference(
                artifact_id="cpu_baseline_benchmark_report_candidate",
                artifact_kind="baseline_benchmark_report",
                schema_version="tuc.baseline_benchmark_report.v0",
                artifact_digest="sha256:" + ("0123456789abcdef" * 4),
            ),
        ),
    )
    payload = benchmark_artifact_manifest_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_benchmark_artifact_manifest_schema_is_referenced() -> None:
    schema_path = "schemas/benchmark_artifact_manifest_report.v0.schema.json"

    for path in (
        Path("docs/BENCHMARK_ARTIFACT_MANIFEST.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0069-benchmark-artifact-manifest-report.md"),
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
