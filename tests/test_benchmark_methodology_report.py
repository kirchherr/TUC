from __future__ import annotations

import json

import pytest

from tuc import (
    BENCHMARK_METHODOLOGY_ARTIFACT_STATUS,
    BENCHMARK_METHODOLOGY_CLAIM_STATUS,
    BENCHMARK_METHODOLOGY_DEFAULT_ISSUES,
    BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION,
    BenchmarkMethodology,
    benchmark_methodology_report_to_dict,
    build_benchmark_methodology_report,
    dump_benchmark_methodology_report,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT


def test_benchmark_methodology_report_blocks_without_methodologies() -> None:
    report = build_benchmark_methodology_report("blocked_benchmark_methodology")
    payload = benchmark_methodology_report_to_dict(report)

    assert payload["schema_version"] == BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == BENCHMARK_METHODOLOGY_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == BENCHMARK_METHODOLOGY_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["benchmark_methodology_ready"] is False
    assert payload["methodologies"] == []
    assert payload["issues"] == list(BENCHMARK_METHODOLOGY_DEFAULT_ISSUES)


def test_benchmark_methodology_report_tracks_bounded_methodology() -> None:
    report = build_benchmark_methodology_report(
        "phase1_benchmark_methodology_candidate",
        methodologies=(
            BenchmarkMethodology(
                methodology_id="phase1_cpu_baseline_methodology",
                workload_scope_id="phase1_mlp_matmul_64x64",
                measurement_clock="monotonic_ns",
                warmup_iterations=3,
                measurement_iterations=20,
                statistic_policy="min_median_mean",
                isolation_level="process_isolated",
                outlier_policy_id="no_raw_sample_storage",
                reproducibility_policy_id="docker_dev_container",
            ),
        ),
    )
    payload = benchmark_methodology_report_to_dict(report)

    assert payload["benchmark_methodology_ready"] is True
    assert payload["native_performance_claim"] is False
    assert payload["methodologies"] == [
        {
            "isolation_level": "process_isolated",
            "measurement_clock": "monotonic_ns",
            "measurement_iterations": 20,
            "methodology_id": "phase1_cpu_baseline_methodology",
            "outlier_policy_id": "no_raw_sample_storage",
            "reproducibility_policy_id": "docker_dev_container",
            "statistic_policy": "min_median_mean",
            "warmup_iterations": 3,
            "workload_scope_id": "phase1_mlp_matmul_64x64",
        }
    ]
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_benchmark_methodology_report_is_json_serializable() -> None:
    report = build_benchmark_methodology_report("blocked_benchmark_methodology")
    payload = json.loads(dump_benchmark_methodology_report(report))

    assert payload["schema_version"] == "tuc.benchmark_methodology_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_benchmark_methodology_rejects_duplicate_ids() -> None:
    methodology = BenchmarkMethodology(
        methodology_id="same_methodology",
        workload_scope_id="phase1_mlp_matmul_64x64",
        measurement_clock="monotonic_ns",
        warmup_iterations=3,
        measurement_iterations=20,
        statistic_policy="min_median_mean",
        isolation_level="process_isolated",
        outlier_policy_id="no_raw_sample_storage",
        reproducibility_policy_id="docker_dev_container",
    )

    with pytest.raises(ValueError, match="duplicate benchmark methodology id"):
        build_benchmark_methodology_report(
            "duplicate_methodology",
            methodologies=(methodology, methodology),
        )


def test_benchmark_methodology_rejects_unknown_clock() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported benchmark methodology measurement clock",
    ):
        build_benchmark_methodology_report(
            "bad_clock",
            methodologies=(
                BenchmarkMethodology(
                    methodology_id="bad_methodology",
                    workload_scope_id="phase1_mlp_matmul_64x64",
                    measurement_clock="cuda_magic_timer",
                    warmup_iterations=3,
                    measurement_iterations=20,
                    statistic_policy="min_median_mean",
                    isolation_level="process_isolated",
                    outlier_policy_id="no_raw_sample_storage",
                    reproducibility_policy_id="docker_dev_container",
                ),
            ),
        )


def test_benchmark_methodology_rejects_host_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="reproducibility_policy_id"):
        build_benchmark_methodology_report(
            "bad_reproducibility_path",
            methodologies=(
                BenchmarkMethodology(
                    methodology_id="bad_methodology",
                    workload_scope_id="phase1_mlp_matmul_64x64",
                    measurement_clock="monotonic_ns",
                    warmup_iterations=3,
                    measurement_iterations=20,
                    statistic_policy="min_median_mean",
                    isolation_level="process_isolated",
                    outlier_policy_id="no_raw_sample_storage",
                    reproducibility_policy_id="C:/ci/runner.env",
                ),
            ),
        )


def test_benchmark_methodology_rejects_invalid_iteration_count() -> None:
    with pytest.raises(ValueError, match="measurement_iterations"):
        build_benchmark_methodology_report(
            "bad_iterations",
            methodologies=(
                BenchmarkMethodology(
                    methodology_id="bad_methodology",
                    workload_scope_id="phase1_mlp_matmul_64x64",
                    measurement_clock="monotonic_ns",
                    warmup_iterations=3,
                    measurement_iterations=0,
                    statistic_policy="min_median_mean",
                    isolation_level="process_isolated",
                    outlier_policy_id="no_raw_sample_storage",
                    reproducibility_policy_id="docker_dev_container",
                ),
            ),
        )


def test_benchmark_methodology_rejects_bool_iteration_count() -> None:
    with pytest.raises(ValueError, match="warmup_iterations"):
        build_benchmark_methodology_report(
            "bad_bool_iterations",
            methodologies=(
                BenchmarkMethodology(
                    methodology_id="bad_methodology",
                    workload_scope_id="phase1_mlp_matmul_64x64",
                    measurement_clock="monotonic_ns",
                    warmup_iterations=True,
                    measurement_iterations=20,
                    statistic_policy="min_median_mean",
                    isolation_level="process_isolated",
                    outlier_policy_id="no_raw_sample_storage",
                    reproducibility_policy_id="docker_dev_container",
                ),
            ),
        )
