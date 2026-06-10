from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS,
    PERFORMANCE_PROOF_RFC_CLAIM_STATUS,
    PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION,
    PERFORMANCE_PROOF_RFC_STATUSES,
    PerformanceProofRFC,
    build_performance_proof_rfc_report,
    performance_proof_rfc_report_to_dict,
)
from tuc.proof import MAX_PERFORMANCE_PROOF_RFCS, PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/performance_proof_rfc_report.v0.schema.json")
_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_performance_proof_rfc_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/performance_proof_rfc_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        PERFORMANCE_PROOF_RFC_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["rfcs"]["maxItems"] == MAX_PERFORMANCE_PROOF_RFCS
    assert schema["$defs"]["rfc_status"]["enum"] == list(
        PERFORMANCE_PROOF_RFC_STATUSES
    )


def test_performance_proof_rfc_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["performance_proof_rfc"]["properties"]
    assert "environment" not in schema["$defs"]["performance_proof_rfc"]["properties"]
    assert "device_id" not in schema["$defs"]["performance_proof_rfc"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_performance_proof_rfc_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_performance_proof_rfc_report(
        "native_performance_proposal",
        rfcs=(
            PerformanceProofRFC(
                rfc_id="native_matmul64_performance_rfc",
                workload_scope_id="matmul64_scope",
                claim_threshold_policy_id="near_native_threshold_policy",
                acceptance_criteria_id="native_performance_acceptance_criteria",
                evidence_bundle_id="performance_evidence_bundle",
                security_review_id="backend_execution_security_review",
                rfc_status="accepted_by_maintainers",
                rfc_digest=_DIGEST,
            ),
        ),
    )
    payload = performance_proof_rfc_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION
    assert payload["native_performance_claim"] is False


def test_performance_proof_rfc_schema_is_referenced() -> None:
    schema_path = "schemas/performance_proof_rfc_report.v0.schema.json"

    for path in (
        Path("docs/PERFORMANCE_PROOF_RFC_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0076-performance-proof-rfc-report.md"),
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
