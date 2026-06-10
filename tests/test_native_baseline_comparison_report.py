from __future__ import annotations

import json

import pytest

from tuc import (
    NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS,
    NATIVE_BASELINE_COMPARISON_CLAIM_STATUS,
    NATIVE_BASELINE_COMPARISON_DEFAULT_ISSUES,
    NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION,
    NativeBaselineComparison,
    build_native_baseline_comparison_report,
    dump_native_baseline_comparison_report,
    native_baseline_comparison_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_native_baseline_comparison_report_blocks_without_comparisons() -> None:
    report = build_native_baseline_comparison_report("blocked_native_comparison")
    payload = native_baseline_comparison_report_to_dict(report)

    assert payload["schema_version"] == NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == NATIVE_BASELINE_COMPARISON_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["native_baseline_comparison_ready"] is False
    assert payload["comparisons"] == []
    assert payload["issues"] == list(NATIVE_BASELINE_COMPARISON_DEFAULT_ISSUES)


def test_native_baseline_comparison_report_tracks_candidate_metadata() -> None:
    report = build_native_baseline_comparison_report(
        "phase1_native_comparison_candidate",
        comparisons=(
            NativeBaselineComparison(
                comparison_id="matmul64_native_comparison",
                workload_scope_id="matmul64_scope",
                baseline_artifact_id="baseline_report",
                native_artifact_id="native_report",
                comparison_metric_id="median_execution_time_ns",
                summary_policy_id="median_iqr",
                result_status="reported_not_validated",
            ),
        ),
    )
    payload = native_baseline_comparison_report_to_dict(report)

    assert payload["native_baseline_comparison_ready"] is False
    assert payload["comparisons"] == [
        {
            "baseline_artifact_id": "baseline_report",
            "comparison_digest": "not_supplied",
            "comparison_id": "matmul64_native_comparison",
            "comparison_metric_id": "median_execution_time_ns",
            "native_artifact_id": "native_report",
            "result_status": "reported_not_validated",
            "summary_policy_id": "median_iqr",
            "workload_scope_id": "matmul64_scope",
        }
    ]
    assert "native_baseline_comparisons_not_supplied" not in payload["issues"]
    assert "native_baseline_comparison_not_validated_by_ci" in payload["issues"]
    assert "native_baseline_comparison_digest_not_supplied" in payload["issues"]


def test_native_baseline_comparison_report_can_be_review_ready() -> None:
    report = build_native_baseline_comparison_report(
        "phase1_native_comparison_candidate",
        comparisons=(
            NativeBaselineComparison(
                comparison_id="matmul64_native_comparison",
                workload_scope_id="matmul64_scope",
                baseline_artifact_id="baseline_report",
                native_artifact_id="native_report",
                comparison_metric_id="median_execution_time_ns",
                summary_policy_id="median_iqr",
                result_status="validated_by_ci",
                comparison_digest=_DIGEST,
            ),
        ),
    )
    payload = native_baseline_comparison_report_to_dict(report)

    assert payload["native_baseline_comparison_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_native_baseline_comparison_report_is_json_serializable() -> None:
    report = build_native_baseline_comparison_report("blocked_native_comparison")
    payload = json.loads(dump_native_baseline_comparison_report(report))

    assert payload["schema_version"] == "tuc.native_baseline_comparison_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_native_baseline_comparison_rejects_duplicate_comparisons() -> None:
    comparison = NativeBaselineComparison(
        comparison_id="same_comparison",
        workload_scope_id="matmul64_scope",
        baseline_artifact_id="baseline_report",
        native_artifact_id="native_report",
        comparison_metric_id="median_execution_time_ns",
        summary_policy_id="median_iqr",
    )

    with pytest.raises(ValueError, match="duplicate native baseline comparison id"):
        build_native_baseline_comparison_report(
            "duplicate_native_comparison",
            comparisons=(comparison, comparison),
        )


def test_native_baseline_comparison_rejects_unknown_status() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported native baseline comparison result status",
    ):
        build_native_baseline_comparison_report(
            "bad_status",
            comparisons=(
                NativeBaselineComparison(
                    comparison_id="bad_comparison",
                    workload_scope_id="matmul64_scope",
                    baseline_artifact_id="baseline_report",
                    native_artifact_id="native_report",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                    result_status="native_wins",
                ),
            ),
        )


def test_native_baseline_comparison_rejects_host_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="baseline_artifact_id"):
        build_native_baseline_comparison_report(
            "bad_artifact_path",
            comparisons=(
                NativeBaselineComparison(
                    comparison_id="bad_comparison",
                    workload_scope_id="matmul64_scope",
                    baseline_artifact_id="C:/benchmarks/baseline.json",
                    native_artifact_id="native_report",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                ),
            ),
        )


def test_native_baseline_comparison_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="comparison_digest"):
        build_native_baseline_comparison_report(
            "bad_digest",
            comparisons=(
                NativeBaselineComparison(
                    comparison_id="bad_digest_comparison",
                    workload_scope_id="matmul64_scope",
                    baseline_artifact_id="baseline_report",
                    native_artifact_id="native_report",
                    comparison_metric_id="median_execution_time_ns",
                    summary_policy_id="median_iqr",
                    comparison_digest="sha256:ABCDEF",
                ),
            ),
        )
