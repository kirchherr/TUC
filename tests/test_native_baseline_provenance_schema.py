from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    NATIVE_BASELINE_IMPLEMENTATION_KINDS,
    NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS,
    NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS,
    NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION,
    NATIVE_BASELINE_REPRODUCIBILITY_STATUSES,
    NativeBaselineProvenance,
    build_native_baseline_provenance_report,
    native_baseline_provenance_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/native_baseline_provenance_report.v0.schema.json")


def test_native_baseline_provenance_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/native_baseline_provenance_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["native_baseline_ready"]["const"] is False
    assert schema["properties"]["baselines"]["maxItems"] == 64
    assert schema["$defs"]["implementation_kind"]["enum"] == list(
        NATIVE_BASELINE_IMPLEMENTATION_KINDS
    )
    assert schema["$defs"]["reproducibility_status"]["enum"] == list(
        NATIVE_BASELINE_REPRODUCIBILITY_STATUSES
    )


def test_native_baseline_provenance_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["native_baseline"]["properties"]
    assert "device_id" not in schema["$defs"]["native_baseline"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["native_baseline"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_native_baseline_provenance_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_native_baseline_provenance_report(
        "phase1_native_baseline_candidate",
        baselines=(
            NativeBaselineProvenance(
                baseline_id="cuda_vendor_matmul_candidate",
                workload_scope_id="phase1_mlp_block",
                implementation_kind="vendor_sample",
                target_platform_id="cuda_sm90",
                source_provenance_id="vendor_sample_manifest",
                toolchain_id="cuda_12_4",
                reproducibility_status="documented_not_executed",
            ),
        ),
    )
    payload = native_baseline_provenance_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION
    assert payload["native_baseline_ready"] is False


def test_native_baseline_provenance_schema_is_referenced() -> None:
    schema_path = "schemas/native_baseline_provenance_report.v0.schema.json"

    for path in (
        Path("docs/NATIVE_BASELINE_PROVENANCE.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0068-native-baseline-provenance-report.md"),
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
