from __future__ import annotations

import json

import pytest

from tuc import (
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_DEFAULT_ISSUES,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION,
    PerformanceClaimThresholdPolicy,
    build_performance_claim_threshold_policy_report,
    dump_performance_claim_threshold_policy_report,
    performance_claim_threshold_policy_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_threshold_policy_report_blocks_without_policies() -> None:
    report = build_performance_claim_threshold_policy_report(
        "native_performance_proposal"
    )
    payload = performance_claim_threshold_policy_report_to_dict(report)

    assert (
        payload["schema_version"]
        == PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == (
        PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS
    )
    assert payload["native_performance_claim"] is False
    assert payload["performance_claim_threshold_policy_ready"] is False
    assert payload["policies"] == []
    assert payload["issues"] == list(PERFORMANCE_CLAIM_THRESHOLD_POLICY_DEFAULT_ISSUES)


def test_threshold_policy_report_tracks_draft_metadata() -> None:
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
                policy_status="reviewed_not_accepted",
            ),
        ),
    )
    payload = performance_claim_threshold_policy_report_to_dict(report)

    assert payload["performance_claim_threshold_policy_ready"] is False
    assert payload["policies"] == [
        {
            "comparison_metric_id": "median_execution_time_ns",
            "policy_digest": "not_supplied",
            "policy_id": "near_native_threshold_policy",
            "policy_status": "reviewed_not_accepted",
            "summary_policy_id": "median_iqr",
            "threshold_basis_points": 9500,
            "threshold_kind": "ratio_to_native_at_least",
            "workload_scope_id": "matmul64_scope",
        }
    ]
    assert "performance_claim_threshold_policies_not_supplied" not in payload["issues"]
    assert "performance_claim_threshold_policy_not_accepted" in payload["issues"]
    assert "performance_claim_threshold_policy_digest_not_supplied" in payload["issues"]


def test_threshold_policy_report_can_be_review_ready() -> None:
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

    assert payload["performance_claim_threshold_policy_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_threshold_policy_report_is_json_serializable() -> None:
    report = build_performance_claim_threshold_policy_report(
        "native_performance_proposal"
    )
    payload = json.loads(dump_performance_claim_threshold_policy_report(report))

    assert payload["schema_version"] == (
        "tuc.performance_claim_threshold_policy_report.v0"
    )
    assert payload["performance_claim_status"] == "blocked"


def test_threshold_policy_rejects_duplicate_ids() -> None:
    policy = PerformanceClaimThresholdPolicy(
        policy_id="same_policy",
        workload_scope_id="matmul64_scope",
        comparison_metric_id="median_execution_time_ns",
        summary_policy_id="median_iqr",
        threshold_kind="ratio_to_native_at_least",
        threshold_basis_points=9500,
    )

    with pytest.raises(
        ValueError,
        match="duplicate performance claim threshold policy id",
    ):
        build_performance_claim_threshold_policy_report(
            "duplicate_threshold_policy",
            policies=(policy, policy),
        )


def test_threshold_policy_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unsupported performance claim threshold kind"):
        build_performance_claim_threshold_policy_report(
            "bad_kind",
            policies=(
                PerformanceClaimThresholdPolicy(
                    policy_id="bad_kind_policy",
                    workload_scope_id="matmul64_scope",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                    threshold_kind="sounds_fast_enough",
                    threshold_basis_points=9500,
                ),
            ),
        )


def test_threshold_policy_rejects_unknown_status() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported performance claim threshold policy status",
    ):
        build_performance_claim_threshold_policy_report(
            "bad_status",
            policies=(
                PerformanceClaimThresholdPolicy(
                    policy_id="bad_status_policy",
                    workload_scope_id="matmul64_scope",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                    threshold_kind="ratio_to_native_at_least",
                    threshold_basis_points=9500,
                    policy_status="accepted_by_timing",
                ),
            ),
        )


def test_threshold_policy_rejects_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="summary_policy_id"):
        build_performance_claim_threshold_policy_report(
            "bad_path",
            policies=(
                PerformanceClaimThresholdPolicy(
                    policy_id="bad_path_policy",
                    workload_scope_id="matmul64_scope",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="C:/benchmarks/summary.json",
                    threshold_kind="ratio_to_native_at_least",
                    threshold_basis_points=9500,
                ),
            ),
        )


def test_threshold_policy_rejects_invalid_basis_points() -> None:
    with pytest.raises(ValueError, match="threshold_basis_points"):
        build_performance_claim_threshold_policy_report(
            "bad_threshold",
            policies=(
                PerformanceClaimThresholdPolicy(
                    policy_id="bad_threshold_policy",
                    workload_scope_id="matmul64_scope",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                    threshold_kind="ratio_to_native_at_least",
                    threshold_basis_points=0,
                ),
            ),
        )


def test_threshold_policy_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="policy_digest"):
        build_performance_claim_threshold_policy_report(
            "bad_digest",
            policies=(
                PerformanceClaimThresholdPolicy(
                    policy_id="bad_digest_policy",
                    workload_scope_id="matmul64_scope",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                    threshold_kind="ratio_to_native_at_least",
                    threshold_basis_points=9500,
                    policy_digest="sha256:ABCDEF",
                ),
            ),
        )
