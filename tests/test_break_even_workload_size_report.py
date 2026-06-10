from __future__ import annotations

import json

import pytest

from tuc import (
    BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS,
    BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS,
    BREAK_EVEN_WORKLOAD_SIZE_DEFAULT_ISSUES,
    BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION,
    BreakEvenWorkloadSize,
    break_even_workload_size_report_to_dict,
    build_break_even_workload_size_report,
    dump_break_even_workload_size_report,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_break_even_workload_report_blocks_without_workloads() -> None:
    report = build_break_even_workload_size_report("blocked_break_even")
    payload = break_even_workload_size_report_to_dict(report)

    assert payload["schema_version"] == BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["break_even_workload_size_ready"] is False
    assert payload["workloads"] == []
    assert payload["issues"] == list(BREAK_EVEN_WORKLOAD_SIZE_DEFAULT_ISSUES)


def test_break_even_workload_report_tracks_estimated_metadata() -> None:
    report = build_break_even_workload_size_report(
        "phase1_break_even_candidate",
        workloads=(
            BreakEvenWorkloadSize(
                break_even_id="matmul64_break_even",
                workload_scope_id="matmul64_scope",
                planner_overhead_report_id="planner_overhead_report",
                execution_metric_id="median_execution_time_ns",
                amortization_policy_id="single_compile_many_runs",
                break_even_status="estimated_not_validated",
                break_even_problem_size=4096,
            ),
        ),
    )
    payload = break_even_workload_size_report_to_dict(report)

    assert payload["break_even_workload_size_ready"] is False
    assert payload["workloads"] == [
        {
            "amortization_policy_id": "single_compile_many_runs",
            "break_even_id": "matmul64_break_even",
            "break_even_problem_size": 4096,
            "break_even_status": "estimated_not_validated",
            "evidence_digest": "not_supplied",
            "execution_metric_id": "median_execution_time_ns",
            "planner_overhead_report_id": "planner_overhead_report",
            "workload_scope_id": "matmul64_scope",
        }
    ]
    assert "break_even_workloads_not_supplied" not in payload["issues"]
    assert "break_even_workload_not_validated_by_ci" in payload["issues"]
    assert "break_even_workload_digest_not_supplied" in payload["issues"]


def test_break_even_workload_report_can_be_review_ready() -> None:
    report = build_break_even_workload_size_report(
        "phase1_break_even_candidate",
        workloads=(
            BreakEvenWorkloadSize(
                break_even_id="matmul64_break_even",
                workload_scope_id="matmul64_scope",
                planner_overhead_report_id="planner_overhead_report",
                execution_metric_id="median_execution_time_ns",
                amortization_policy_id="single_compile_many_runs",
                break_even_status="validated_by_ci",
                break_even_problem_size=4096,
                evidence_digest=_DIGEST,
            ),
        ),
    )
    payload = break_even_workload_size_report_to_dict(report)

    assert payload["break_even_workload_size_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_break_even_workload_report_is_json_serializable() -> None:
    report = build_break_even_workload_size_report("blocked_break_even")
    payload = json.loads(dump_break_even_workload_size_report(report))

    assert payload["schema_version"] == "tuc.break_even_workload_size_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_break_even_workload_rejects_duplicate_ids() -> None:
    workload = BreakEvenWorkloadSize(
        break_even_id="same_break_even",
        workload_scope_id="matmul64_scope",
        planner_overhead_report_id="planner_overhead_report",
        execution_metric_id="median_execution_time_ns",
        amortization_policy_id="single_compile_many_runs",
    )

    with pytest.raises(ValueError, match="duplicate break-even workload id"):
        build_break_even_workload_size_report(
            "duplicate_break_even",
            workloads=(workload, workload),
        )


def test_break_even_workload_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="unsupported break-even workload status"):
        build_break_even_workload_size_report(
            "bad_status",
            workloads=(
                BreakEvenWorkloadSize(
                    break_even_id="bad_break_even",
                    workload_scope_id="matmul64_scope",
                    planner_overhead_report_id="planner_overhead_report",
                    execution_metric_id="median_execution_time_ns",
                    amortization_policy_id="single_compile_many_runs",
                    break_even_status="native_fast_enough",
                ),
            ),
        )


def test_break_even_workload_rejects_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="planner_overhead_report_id"):
        build_break_even_workload_size_report(
            "bad_report_path",
            workloads=(
                BreakEvenWorkloadSize(
                    break_even_id="bad_break_even",
                    workload_scope_id="matmul64_scope",
                    planner_overhead_report_id="C:/benchmarks/planner.json",
                    execution_metric_id="median_execution_time_ns",
                    amortization_policy_id="single_compile_many_runs",
                ),
            ),
        )


def test_break_even_workload_rejects_not_established_size() -> None:
    with pytest.raises(ValueError, match="not_established"):
        build_break_even_workload_size_report(
            "bad_unestablished_size",
            workloads=(
                BreakEvenWorkloadSize(
                    break_even_id="bad_break_even",
                    workload_scope_id="matmul64_scope",
                    planner_overhead_report_id="planner_overhead_report",
                    execution_metric_id="median_execution_time_ns",
                    amortization_policy_id="single_compile_many_runs",
                    break_even_problem_size=4096,
                ),
            ),
        )


def test_break_even_workload_rejects_invalid_problem_size() -> None:
    with pytest.raises(ValueError, match="break_even_problem_size"):
        build_break_even_workload_size_report(
            "bad_size",
            workloads=(
                BreakEvenWorkloadSize(
                    break_even_id="bad_break_even",
                    workload_scope_id="matmul64_scope",
                    planner_overhead_report_id="planner_overhead_report",
                    execution_metric_id="median_execution_time_ns",
                    amortization_policy_id="single_compile_many_runs",
                    break_even_status="estimated_not_validated",
                    break_even_problem_size=0,
                ),
            ),
        )


def test_break_even_workload_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="evidence_digest"):
        build_break_even_workload_size_report(
            "bad_digest",
            workloads=(
                BreakEvenWorkloadSize(
                    break_even_id="bad_break_even",
                    workload_scope_id="matmul64_scope",
                    planner_overhead_report_id="planner_overhead_report",
                    execution_metric_id="median_execution_time_ns",
                    amortization_policy_id="single_compile_many_runs",
                    break_even_status="estimated_not_validated",
                    break_even_problem_size=4096,
                    evidence_digest="sha256:ABCDEF",
                ),
            ),
        )
