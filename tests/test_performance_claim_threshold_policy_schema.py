from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_KINDS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_STATUSES,
    PerformanceClaimThresholdPolicy,
    build_performance_claim_threshold_policy_report,
    performance_claim_threshold_policy_report_to_dict,
)
from tuc.proof import (
    MAX_PERFORMANCE_CLAIM_THRESHOLD_BASIS_POINTS,
    MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICIES,
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
)

SCHEMA_PATH = Path("schemas/performance_claim_threshold_policy_report.v0.schema.json")
_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_threshold_policy_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/performance_claim_threshold_policy_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["policies"]["maxItems"] == (
        MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICIES
    )
    assert schema["$defs"]["threshold_kind"]["enum"] == list(
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_KINDS
    )
    assert schema["$defs"]["policy_status"]["enum"] == list(
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_STATUSES
    )
    assert schema["$defs"]["threshold_basis_points"]["maximum"] == (
        MAX_PERFORMANCE_CLAIM_THRESHOLD_BASIS_POINTS
    )


def test_threshold_policy_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["threshold_policy"]["properties"]
    assert "environment" not in schema["$defs"]["threshold_policy"]["properties"]
    assert "device_id" not in schema["$defs"]["threshold_policy"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_threshold_policy_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_performance_claim_threshold_policy_report(
        "native_performance_proposal",
        policies=(
            PerformanceClaimThresholdPolicy(
                policy_id="near_native_threshold_policy",
                workload_scope_id="matmul64_scope",
                comparison_metric_id="median_execution_time_ns",
                summary_policy_id="median_iqr",
                threshold_kind="ratio_to_native_at_least",
                threshold_basis_points=9500,
                policy_status="accepted_by_maintainers",
                policy_digest=_DIGEST,
            ),
        ),
    )
    payload = performance_claim_threshold_policy_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == (
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION
    )
    assert payload["native_performance_claim"] is False


def test_threshold_policy_schema_is_referenced() -> None:
    schema_path = "schemas/performance_claim_threshold_policy_report.v0.schema.json"

    for path in (
        Path("docs/PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0077-performance-claim-threshold-policy-report.md"),
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
