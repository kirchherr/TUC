from __future__ import annotations

import json

import pytest

from tuc import (
    WORKLOAD_SCOPE_ARTIFACT_STATUS,
    WORKLOAD_SCOPE_CLAIM_STATUS,
    WORKLOAD_SCOPE_DEFAULT_ISSUES,
    WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
    WorkloadScope,
    build_workload_scope_report,
    dump_workload_scope_report,
    workload_scope_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT


def test_workload_scope_report_blocks_without_scopes() -> None:
    report = build_workload_scope_report("blocked_workload_scope")
    payload = workload_scope_report_to_dict(report)

    assert payload["schema_version"] == WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == WORKLOAD_SCOPE_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == WORKLOAD_SCOPE_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["workload_scope_ready"] is False
    assert payload["scopes"] == []
    assert payload["issues"] == list(WORKLOAD_SCOPE_DEFAULT_ISSUES)


def test_workload_scope_report_tracks_bounded_scope() -> None:
    report = build_workload_scope_report(
        "phase1_workload_scope_candidate",
        scopes=(
            WorkloadScope(
                scope_id="phase1_mlp_matmul_64x64",
                operation_family="matmul",
                shape_profile_id="square_64x64",
                dtype_policy_id="float64_reference",
                problem_size_min=4096,
                problem_size_max=4096,
                correctness_reference_id="numpy_reference_matmul",
            ),
        ),
    )
    payload = workload_scope_report_to_dict(report)

    assert payload["workload_scope_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["scopes"] == [
        {
            "correctness_reference_id": "numpy_reference_matmul",
            "dtype_policy_id": "float64_reference",
            "operation_family": "matmul",
            "problem_size_max": 4096,
            "problem_size_min": 4096,
            "scope_id": "phase1_mlp_matmul_64x64",
            "shape_profile_id": "square_64x64",
        }
    ]
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_workload_scope_report_is_json_serializable() -> None:
    report = build_workload_scope_report("blocked_workload_scope")
    payload = json.loads(dump_workload_scope_report(report))

    assert payload["schema_version"] == "tuc.workload_scope_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_workload_scope_rejects_duplicate_scope_ids() -> None:
    scope = WorkloadScope(
        scope_id="same_scope",
        operation_family="matmul",
        shape_profile_id="square_64x64",
        dtype_policy_id="float64_reference",
        problem_size_min=4096,
        problem_size_max=4096,
        correctness_reference_id="numpy_reference_matmul",
    )

    with pytest.raises(ValueError, match="duplicate workload scope id"):
        build_workload_scope_report("duplicate_scope", scopes=(scope, scope))


def test_workload_scope_rejects_unknown_operation_family() -> None:
    with pytest.raises(ValueError, match="unsupported workload operation family"):
        build_workload_scope_report(
            "bad_operation_family",
            scopes=(
                WorkloadScope(
                    scope_id="bad_scope",
                    operation_family="cuda_graph",
                    shape_profile_id="square_64x64",
                    dtype_policy_id="float64_reference",
                    problem_size_min=4096,
                    problem_size_max=4096,
                    correctness_reference_id="numpy_reference_matmul",
                ),
            ),
        )


def test_workload_scope_rejects_host_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="correctness_reference_id"):
        build_workload_scope_report(
            "bad_reference_path",
            scopes=(
                WorkloadScope(
                    scope_id="bad_scope",
                    operation_family="matmul",
                    shape_profile_id="square_64x64",
                    dtype_policy_id="float64_reference",
                    problem_size_min=4096,
                    problem_size_max=4096,
                    correctness_reference_id="C:/benchmarks/reference.py",
                ),
            ),
        )


def test_workload_scope_rejects_unbounded_problem_size() -> None:
    with pytest.raises(ValueError, match="problem_size_max"):
        build_workload_scope_report(
            "bad_problem_size",
            scopes=(
                WorkloadScope(
                    scope_id="bad_scope",
                    operation_family="matmul",
                    shape_profile_id="square_64x64",
                    dtype_policy_id="float64_reference",
                    problem_size_min=4096,
                    problem_size_max=0,
                    correctness_reference_id="numpy_reference_matmul",
                ),
            ),
        )


def test_workload_scope_rejects_inverted_problem_size_range() -> None:
    with pytest.raises(ValueError, match="min must not exceed max"):
        build_workload_scope_report(
            "bad_problem_size_range",
            scopes=(
                WorkloadScope(
                    scope_id="bad_scope",
                    operation_family="matmul",
                    shape_profile_id="square_64x64",
                    dtype_policy_id="float64_reference",
                    problem_size_min=8192,
                    problem_size_max=4096,
                    correctness_reference_id="numpy_reference_matmul",
                ),
            ),
        )
