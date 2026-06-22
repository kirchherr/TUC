from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from examples.performance_proof_interpretation import (
    build_current_performance_proof_interpretation_report,
)
from tuc import (
    PERFORMANCE_PROOF_BLOCKED_CLAIMS,
    PERFORMANCE_PROOF_INTERPRETATION_ARTIFACT_STATUS,
    PERFORMANCE_PROOF_INTERPRETATION_CLAIM_STATUS,
    PERFORMANCE_PROOF_INTERPRETATION_DEFAULT_ISSUES,
    PERFORMANCE_PROOF_INTERPRETATION_REPORT_SCHEMA_VERSION,
    PERFORMANCE_PROOF_REQUIRED_EVIDENCE,
    PerformanceProofReadinessEvidence,
    build_performance_proof_interpretation_report,
    build_performance_proof_readiness_report,
    dump_performance_proof_interpretation_report,
    performance_proof_interpretation_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/performance_proof_interpretation_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/performance_proof_interpretation_report.json")


def test_current_performance_proof_interpretation_blocks_native_claims() -> None:
    report = build_current_performance_proof_interpretation_report()
    payload = performance_proof_interpretation_report_to_dict(report)

    assert payload["schema_version"] == PERFORMANCE_PROOF_INTERPRETATION_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == PERFORMANCE_PROOF_INTERPRETATION_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == PERFORMANCE_PROOF_INTERPRETATION_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["readiness_ready"] is True
    assert payload["readiness_issue_count"] == 0
    assert payload["measurement_interpretation_artifacts"] == []
    assert payload["measurement_interpretation_status"] == "not_supplied"
    assert payload["performance_proof_interpretation_ready"] is False
    assert payload["blocked_claims"] == list(PERFORMANCE_PROOF_BLOCKED_CLAIMS)
    assert payload["issues"] == list(PERFORMANCE_PROOF_INTERPRETATION_DEFAULT_ISSUES)


def test_performance_proof_interpretation_dump_matches_golden() -> None:
    report = build_current_performance_proof_interpretation_report()
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n")

    assert dump_performance_proof_interpretation_report(report) == expected + "\n"


def test_performance_proof_interpretation_tracks_missing_readiness() -> None:
    readiness = build_performance_proof_readiness_report(
        "missing_readiness_for_interpretation",
        (PerformanceProofReadinessEvidence("performance_proof_rfc", True),),
    )
    report = build_performance_proof_interpretation_report(
        "blocked_interpretation",
        readiness,
        measurement_interpretation_artifacts=("accepted_measurement_summary",),
    )
    payload = performance_proof_interpretation_report_to_dict(report)

    assert payload["readiness_ready"] is False
    assert payload["readiness_issue_count"] > 0
    assert payload["measurement_interpretation_status"] == "interpreted"
    assert payload["performance_proof_interpretation_ready"] is False
    assert "performance_proof_readiness_not_ready" in payload["issues"]
    assert "native_performance_claim_blocked" in payload["issues"]


def test_interpretation_can_be_metadata_complete_without_native_claim() -> None:
    readiness = build_performance_proof_readiness_report(
        "synthetic_ready_interpretation",
        tuple(
            PerformanceProofReadinessEvidence(evidence_id, True)
            for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
        ),
    )
    report = build_performance_proof_interpretation_report(
        "metadata_complete_interpretation",
        readiness,
        measurement_interpretation_artifacts=("accepted_measurement_summary",),
    )
    payload = performance_proof_interpretation_report_to_dict(report)

    assert payload["performance_proof_interpretation_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["performance_claim_status"] == "blocked"
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_performance_proof_interpretation_rejects_duplicate_artifacts() -> None:
    readiness = build_performance_proof_readiness_report(
        "synthetic_ready_interpretation",
        tuple(
            PerformanceProofReadinessEvidence(evidence_id, True)
            for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate performance proof interpretation artifact",
    ):
        build_performance_proof_interpretation_report(
            "duplicate_artifacts",
            readiness,
            measurement_interpretation_artifacts=("artifact", "artifact"),
        )


def test_performance_proof_interpretation_rejects_path_like_artifacts() -> None:
    readiness = build_performance_proof_readiness_report(
        "synthetic_ready_interpretation",
        tuple(
            PerformanceProofReadinessEvidence(evidence_id, True)
            for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
        ),
    )

    with pytest.raises(ValueError, match="measurement_interpretation_artifact"):
        build_performance_proof_interpretation_report(
            "bad_artifact",
            readiness,
            measurement_interpretation_artifacts=("C:/benchmarks/raw.json",),
        )


def test_performance_proof_interpretation_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/performance_proof_interpretation_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PERFORMANCE_PROOF_INTERPRETATION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        PERFORMANCE_PROOF_INTERPRETATION_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        PERFORMANCE_PROOF_INTERPRETATION_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert (
        schema["properties"]["measurement_interpretation_artifacts"]["maxItems"]
        == 128
    )


def test_performance_proof_interpretation_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "native_performance_parity",
        "raw_benchmark_output",
        "raw_timing_samples",
        "host_path",
        "url",
        "environment",
        "device_id",
        "hardware_serial",
        "plugin_entrypoint",
        "backend_artifact",
        "generated_code",
        "native_source",
        "dynamic_library_path",
    ):
        assert forbidden not in schema["properties"]


def test_performance_proof_interpretation_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    payload = performance_proof_interpretation_report_to_dict(
        build_current_performance_proof_interpretation_report()
    )

    assert sorted(payload) == sorted(schema["required"])
    assert (
        payload["schema_version"]
        == PERFORMANCE_PROOF_INTERPRETATION_REPORT_SCHEMA_VERSION
    )


def test_performance_proof_interpretation_schema_is_referenced() -> None:
    schema_path = "schemas/performance_proof_interpretation_report.v0.schema.json"

    for path in (
        Path("docs/PERFORMANCE_PROOF_INTERPRETATION.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0197-performance-proof-interpretation-report.md"),
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
