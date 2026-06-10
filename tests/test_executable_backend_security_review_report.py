from __future__ import annotations

import json

import pytest

from tuc import (
    EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_DEFAULT_ISSUES,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION,
    ExecutableBackendSecurityReview,
    build_executable_backend_security_review_report,
    dump_executable_backend_security_review_report,
    executable_backend_security_review_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_executable_backend_security_report_blocks_without_reviews() -> None:
    report = build_executable_backend_security_review_report(
        "blocked_backend_security",
    )
    payload = executable_backend_security_review_report_to_dict(report)

    assert payload["schema_version"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS
    )
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == (
        EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS
    )
    assert payload["native_performance_claim"] is False
    assert payload["executable_backend_security_review_ready"] is False
    assert payload["reviews"] == []
    assert payload["issues"] == list(
        EXECUTABLE_BACKEND_SECURITY_REVIEW_DEFAULT_ISSUES
    )


def test_executable_backend_security_report_tracks_review_metadata() -> None:
    report = build_executable_backend_security_review_report(
        "phase1_backend_security_candidate",
        reviews=(
            ExecutableBackendSecurityReview(
                review_id="cuda_artifact_execution_review",
                reviewed_surface="backend_artifact_execution",
                threat_model_id="backend_execution_threat_model",
                sandbox_model_id="not_supplied",
                resource_budget_id="backend_execution_budget",
                provenance_id="security_rfc_0075",
                review_status="reviewed_not_approved",
            ),
        ),
    )
    payload = executable_backend_security_review_report_to_dict(report)

    assert payload["executable_backend_security_review_ready"] is False
    assert payload["reviews"] == [
        {
            "fuzzing_evidence_id": "not_supplied",
            "provenance_id": "security_rfc_0075",
            "resource_budget_id": "backend_execution_budget",
            "review_digest": "not_supplied",
            "review_id": "cuda_artifact_execution_review",
            "review_status": "reviewed_not_approved",
            "reviewed_surface": "backend_artifact_execution",
            "sandbox_model_id": "not_supplied",
            "threat_model_id": "backend_execution_threat_model",
        }
    ]
    assert "executable_backend_security_reviews_not_supplied" not in (
        payload["issues"]
    )
    assert "executable_backend_security_review_not_approved" in payload["issues"]
    assert "executable_backend_security_review_evidence_not_supplied" in (
        payload["issues"]
    )
    assert "executable_backend_security_review_digest_not_supplied" in (
        payload["issues"]
    )


def test_executable_backend_security_report_can_be_review_ready() -> None:
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
                review_digest=_DIGEST,
            ),
        ),
    )
    payload = executable_backend_security_review_report_to_dict(report)

    assert payload["executable_backend_security_review_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_executable_backend_security_report_is_json_serializable() -> None:
    report = build_executable_backend_security_review_report(
        "blocked_backend_security",
    )
    payload = json.loads(dump_executable_backend_security_review_report(report))

    assert (
        payload["schema_version"]
        == "tuc.executable_backend_security_review_report.v0"
    )
    assert payload["performance_claim_status"] == "blocked"


def test_executable_backend_security_rejects_duplicate_reviews() -> None:
    review = ExecutableBackendSecurityReview(
        review_id="same_review",
        reviewed_surface="backend_artifact_execution",
        threat_model_id="backend_execution_threat_model",
        sandbox_model_id="backend_execution_sandbox",
        resource_budget_id="backend_execution_budget",
        provenance_id="security_rfc_0075",
    )

    with pytest.raises(ValueError, match="duplicate executable backend security review"):
        build_executable_backend_security_review_report(
            "duplicate_backend_security_review",
            reviews=(review, review),
        )


def test_executable_backend_security_rejects_unknown_surface() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported executable backend security surface",
    ):
        build_executable_backend_security_review_report(
            "bad_surface",
            reviews=(
                ExecutableBackendSecurityReview(
                    review_id="bad_review",
                    reviewed_surface="raw_cuda_launch",
                    threat_model_id="backend_execution_threat_model",
                    sandbox_model_id="backend_execution_sandbox",
                    resource_budget_id="backend_execution_budget",
                    provenance_id="security_rfc_0075",
                ),
            ),
        )


def test_executable_backend_security_rejects_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="provenance_id"):
        build_executable_backend_security_review_report(
            "bad_provenance_path",
            reviews=(
                ExecutableBackendSecurityReview(
                    review_id="bad_review",
                    reviewed_surface="backend_artifact_execution",
                    threat_model_id="backend_execution_threat_model",
                    sandbox_model_id="backend_execution_sandbox",
                    resource_budget_id="backend_execution_budget",
                    provenance_id="C:/security/review.md",
                ),
            ),
        )


def test_executable_backend_security_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="review_digest"):
        build_executable_backend_security_review_report(
            "bad_digest",
            reviews=(
                ExecutableBackendSecurityReview(
                    review_id="bad_digest_review",
                    reviewed_surface="backend_artifact_execution",
                    threat_model_id="backend_execution_threat_model",
                    sandbox_model_id="backend_execution_sandbox",
                    resource_budget_id="backend_execution_budget",
                    provenance_id="security_rfc_0075",
                    review_digest="sha256:ABCDEF",
                ),
            ),
        )
