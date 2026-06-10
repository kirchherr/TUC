from __future__ import annotations

import json

import pytest

from tuc import (
    PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS,
    PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS,
    PERFORMANCE_ACCEPTANCE_CRITERIA_DEFAULT_ISSUES,
    PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION,
    PerformanceAcceptanceCriteria,
    build_performance_acceptance_criteria_report,
    dump_performance_acceptance_criteria_report,
    performance_acceptance_criteria_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_acceptance_criteria_report_blocks_without_criteria() -> None:
    report = build_performance_acceptance_criteria_report(
        "native_performance_proposal"
    )
    payload = performance_acceptance_criteria_report_to_dict(report)

    assert payload["schema_version"] == (
        PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == (
        PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS
    )
    assert payload["native_performance_claim"] is False
    assert payload["performance_acceptance_criteria_ready"] is False
    assert payload["criteria"] == []
    assert payload["issues"] == list(PERFORMANCE_ACCEPTANCE_CRITERIA_DEFAULT_ISSUES)


def test_acceptance_criteria_report_tracks_draft_metadata() -> None:
    report = build_performance_acceptance_criteria_report(
        "native_performance_proposal",
        criteria=(
            PerformanceAcceptanceCriteria(
                criteria_id="native_matmul64_acceptance_criteria",
                workload_scope_id="matmul64_scope",
                threshold_policy_id="near_native_threshold_policy",
                correctness_evidence_id="matmul64_correctness_goldens",
                benchmark_methodology_id="ci_median_iqr_methodology",
                native_baseline_comparison_id="not_supplied",
                planner_overhead_report_id="planner_overhead_report",
                break_even_workload_size_id="not_supplied",
                leaky_abstraction_report_id="leaky_abstraction_report",
                executable_security_review_id="backend_execution_security_review",
                criteria_status="reviewed_not_accepted",
            ),
        ),
    )
    payload = performance_acceptance_criteria_report_to_dict(report)

    assert payload["performance_acceptance_criteria_ready"] is False
    assert payload["criteria"] == [
        {
            "benchmark_methodology_id": "ci_median_iqr_methodology",
            "break_even_workload_size_id": "not_supplied",
            "correctness_evidence_id": "matmul64_correctness_goldens",
            "criteria_digest": "not_supplied",
            "criteria_id": "native_matmul64_acceptance_criteria",
            "criteria_status": "reviewed_not_accepted",
            "executable_security_review_id": "backend_execution_security_review",
            "leaky_abstraction_report_id": "leaky_abstraction_report",
            "native_baseline_comparison_id": "not_supplied",
            "planner_overhead_report_id": "planner_overhead_report",
            "threshold_policy_id": "near_native_threshold_policy",
            "workload_scope_id": "matmul64_scope",
        }
    ]
    assert "performance_acceptance_criteria_not_supplied" not in payload["issues"]
    assert "performance_acceptance_criteria_not_accepted" in payload["issues"]
    assert "performance_acceptance_criteria_evidence_not_supplied" in payload["issues"]
    assert "performance_acceptance_criteria_digest_not_supplied" in payload["issues"]


def test_acceptance_criteria_report_can_be_review_ready() -> None:
    report = build_performance_acceptance_criteria_report(
        "native_performance_proposal",
        criteria=(
            PerformanceAcceptanceCriteria(
                criteria_id="native_matmul64_acceptance_criteria",
                workload_scope_id="matmul64_scope",
                threshold_policy_id="near_native_threshold_policy",
                correctness_evidence_id="matmul64_correctness_goldens",
                benchmark_methodology_id="ci_median_iqr_methodology",
                native_baseline_comparison_id="native_matmul64_comparison",
                planner_overhead_report_id="planner_overhead_report",
                break_even_workload_size_id="matmul64_break_even",
                leaky_abstraction_report_id="leaky_abstraction_report",
                executable_security_review_id="backend_execution_security_review",
                criteria_status="accepted_by_maintainers",
                criteria_digest=_DIGEST,
            ),
        ),
    )
    payload = performance_acceptance_criteria_report_to_dict(report)

    assert payload["performance_acceptance_criteria_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_acceptance_criteria_report_is_json_serializable() -> None:
    report = build_performance_acceptance_criteria_report(
        "native_performance_proposal"
    )
    payload = json.loads(dump_performance_acceptance_criteria_report(report))

    assert payload["schema_version"] == "tuc.performance_acceptance_criteria_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_acceptance_criteria_rejects_duplicate_ids() -> None:
    criteria = PerformanceAcceptanceCriteria(
        criteria_id="same_criteria",
        workload_scope_id="matmul64_scope",
        threshold_policy_id="near_native_threshold_policy",
        correctness_evidence_id="matmul64_correctness_goldens",
        benchmark_methodology_id="ci_median_iqr_methodology",
        native_baseline_comparison_id="native_matmul64_comparison",
        planner_overhead_report_id="planner_overhead_report",
        break_even_workload_size_id="matmul64_break_even",
        leaky_abstraction_report_id="leaky_abstraction_report",
        executable_security_review_id="backend_execution_security_review",
    )

    with pytest.raises(ValueError, match="duplicate performance acceptance criteria id"):
        build_performance_acceptance_criteria_report(
            "duplicate_acceptance_criteria",
            criteria=(criteria, criteria),
        )


def test_acceptance_criteria_rejects_unknown_status() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported performance acceptance criteria status",
    ):
        build_performance_acceptance_criteria_report(
            "bad_status",
            criteria=(
                PerformanceAcceptanceCriteria(
                    criteria_id="bad_status_criteria",
                    workload_scope_id="matmul64_scope",
                    threshold_policy_id="near_native_threshold_policy",
                    correctness_evidence_id="matmul64_correctness_goldens",
                    benchmark_methodology_id="ci_median_iqr_methodology",
                    native_baseline_comparison_id="native_matmul64_comparison",
                    planner_overhead_report_id="planner_overhead_report",
                    break_even_workload_size_id="matmul64_break_even",
                    leaky_abstraction_report_id="leaky_abstraction_report",
                    executable_security_review_id="backend_execution_security_review",
                    criteria_status="passed_by_timing",
                ),
            ),
        )


def test_acceptance_criteria_rejects_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="native_baseline_comparison_id"):
        build_performance_acceptance_criteria_report(
            "bad_path",
            criteria=(
                PerformanceAcceptanceCriteria(
                    criteria_id="bad_path_criteria",
                    workload_scope_id="matmul64_scope",
                    threshold_policy_id="near_native_threshold_policy",
                    correctness_evidence_id="matmul64_correctness_goldens",
                    benchmark_methodology_id="ci_median_iqr_methodology",
                    native_baseline_comparison_id="C:/benchmarks/native.json",
                    planner_overhead_report_id="planner_overhead_report",
                    break_even_workload_size_id="matmul64_break_even",
                    leaky_abstraction_report_id="leaky_abstraction_report",
                    executable_security_review_id="backend_execution_security_review",
                ),
            ),
        )


def test_acceptance_criteria_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="criteria_digest"):
        build_performance_acceptance_criteria_report(
            "bad_digest",
            criteria=(
                PerformanceAcceptanceCriteria(
                    criteria_id="bad_digest_criteria",
                    workload_scope_id="matmul64_scope",
                    threshold_policy_id="near_native_threshold_policy",
                    correctness_evidence_id="matmul64_correctness_goldens",
                    benchmark_methodology_id="ci_median_iqr_methodology",
                    native_baseline_comparison_id="native_matmul64_comparison",
                    planner_overhead_report_id="planner_overhead_report",
                    break_even_workload_size_id="matmul64_break_even",
                    leaky_abstraction_report_id="leaky_abstraction_report",
                    executable_security_review_id="backend_execution_security_review",
                    criteria_digest="sha256:ABCDEF",
                ),
            ),
        )
