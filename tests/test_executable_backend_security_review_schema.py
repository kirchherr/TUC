from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc import (
    EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_STATUSES,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES,
    ExecutableBackendSecurityReview,
    build_executable_backend_security_review_report,
    executable_backend_security_review_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/executable_backend_security_review_report.v0.schema.json")


def test_executable_backend_security_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/executable_backend_security_review_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["reviews"]["maxItems"] == 128
    assert schema["$defs"]["review_status"]["enum"] == list(
        EXECUTABLE_BACKEND_SECURITY_REVIEW_STATUSES
    )
    assert schema["$defs"]["reviewed_surface"]["enum"] == list(
        EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES
    )


def test_executable_backend_security_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "raw_timing_samples" not in schema["properties"]
    assert "host_path" not in schema["$defs"]["security_review"]["properties"]
    assert "environment" not in schema["$defs"]["security_review"]["properties"]
    assert "device_id" not in schema["$defs"]["security_review"]["properties"]
    assert "hardware_serial" not in schema["$defs"]["security_review"]["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_executable_backend_security_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    report = build_executable_backend_security_review_report(
        "phase1_backend_security_candidate",
        reviews=(
            ExecutableBackendSecurityReview(
                review_id="cuda_artifact_execution_review",
                reviewed_surface="backend_artifact_execution",
                threat_model_id="backend_execution_threat_model",
                sandbox_model_id="backend_execution_sandbox",
                resource_budget_id="backend_execution_budget",
                provenance_id="security_rfc_0075",
                review_status="approved_by_maintainers",
                fuzzing_evidence_id="backend_execution_fuzzing_plan",
                review_digest="sha256:" + ("0123456789abcdef" * 4),
            ),
        ),
    )
    payload = executable_backend_security_review_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert payload["native_performance_claim"] is False


def test_executable_backend_security_schema_is_referenced() -> None:
    schema_path = "schemas/executable_backend_security_review_report.v0.schema.json"

    for path in (
        Path("docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md"),
        Path("docs/BENCHMARKING.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0075-executable-backend-security-review-report.md"),
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
