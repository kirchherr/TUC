from __future__ import annotations

import json

import pytest

from tuc import (
    PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS,
    PERFORMANCE_PROOF_RFC_CLAIM_STATUS,
    PERFORMANCE_PROOF_RFC_DEFAULT_ISSUES,
    PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION,
    PerformanceProofRFC,
    build_performance_proof_rfc_report,
    dump_performance_proof_rfc_report,
    performance_proof_rfc_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_performance_proof_rfc_report_blocks_without_rfcs() -> None:
    report = build_performance_proof_rfc_report("native_performance_proposal")
    payload = performance_proof_rfc_report_to_dict(report)

    assert payload["schema_version"] == PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == PERFORMANCE_PROOF_RFC_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["performance_proof_rfc_ready"] is False
    assert payload["rfcs"] == []
    assert payload["issues"] == list(PERFORMANCE_PROOF_RFC_DEFAULT_ISSUES)


def test_performance_proof_rfc_report_tracks_draft_metadata() -> None:
    report = build_performance_proof_rfc_report(
        "native_performance_proposal",
        rfcs=(
            PerformanceProofRFC(
                rfc_id="native_matmul64_performance_rfc",
                workload_scope_id="matmul64_scope",
                claim_threshold_policy_id="near_native_threshold_policy",
                acceptance_criteria_id="native_performance_acceptance_criteria",
                evidence_bundle_id="not_supplied",
                security_review_id="not_supplied",
                rfc_status="reviewed_not_accepted",
            ),
        ),
    )
    payload = performance_proof_rfc_report_to_dict(report)

    assert payload["performance_proof_rfc_ready"] is False
    assert payload["rfcs"] == [
        {
            "acceptance_criteria_id": "native_performance_acceptance_criteria",
            "claim_threshold_policy_id": "near_native_threshold_policy",
            "evidence_bundle_id": "not_supplied",
            "rfc_digest": "not_supplied",
            "rfc_id": "native_matmul64_performance_rfc",
            "rfc_status": "reviewed_not_accepted",
            "security_review_id": "not_supplied",
            "workload_scope_id": "matmul64_scope",
        }
    ]
    assert "performance_proof_rfcs_not_supplied" not in payload["issues"]
    assert "performance_proof_rfc_not_accepted" in payload["issues"]
    assert "performance_proof_rfc_evidence_not_supplied" in payload["issues"]
    assert "performance_proof_rfc_digest_not_supplied" in payload["issues"]


def test_performance_proof_rfc_report_can_be_review_ready() -> None:
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

    assert payload["performance_proof_rfc_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_performance_proof_rfc_report_is_json_serializable() -> None:
    report = build_performance_proof_rfc_report("native_performance_proposal")
    payload = json.loads(dump_performance_proof_rfc_report(report))

    assert payload["schema_version"] == "tuc.performance_proof_rfc_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_performance_proof_rfc_rejects_duplicate_ids() -> None:
    rfc = PerformanceProofRFC(
        rfc_id="same_rfc",
        workload_scope_id="matmul64_scope",
        claim_threshold_policy_id="near_native_threshold_policy",
        acceptance_criteria_id="native_performance_acceptance_criteria",
        evidence_bundle_id="performance_evidence_bundle",
        security_review_id="backend_execution_security_review",
    )

    with pytest.raises(ValueError, match="duplicate performance proof RFC id"):
        build_performance_proof_rfc_report(
            "duplicate_rfc",
            rfcs=(rfc, rfc),
        )


def test_performance_proof_rfc_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="unsupported performance proof RFC status"):
        build_performance_proof_rfc_report(
            "bad_status",
            rfcs=(
                PerformanceProofRFC(
                    rfc_id="bad_status_rfc",
                    workload_scope_id="matmul64_scope",
                    claim_threshold_policy_id="near_native_threshold_policy",
                    acceptance_criteria_id="native_performance_acceptance_criteria",
                    evidence_bundle_id="performance_evidence_bundle",
                    security_review_id="backend_execution_security_review",
                    rfc_status="approved_by_benchmark",
                ),
            ),
        )


def test_performance_proof_rfc_rejects_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="evidence_bundle_id"):
        build_performance_proof_rfc_report(
            "bad_path",
            rfcs=(
                PerformanceProofRFC(
                    rfc_id="bad_path_rfc",
                    workload_scope_id="matmul64_scope",
                    claim_threshold_policy_id="near_native_threshold_policy",
                    acceptance_criteria_id="native_performance_acceptance_criteria",
                    evidence_bundle_id="C:/benchmarks/native.json",
                    security_review_id="backend_execution_security_review",
                ),
            ),
        )


def test_performance_proof_rfc_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="rfc_digest"):
        build_performance_proof_rfc_report(
            "bad_digest",
            rfcs=(
                PerformanceProofRFC(
                    rfc_id="bad_digest_rfc",
                    workload_scope_id="matmul64_scope",
                    claim_threshold_policy_id="near_native_threshold_policy",
                    acceptance_criteria_id="native_performance_acceptance_criteria",
                    evidence_bundle_id="performance_evidence_bundle",
                    security_review_id="backend_execution_security_review",
                    rfc_digest="sha256:ABCDEF",
                ),
            ),
        )
