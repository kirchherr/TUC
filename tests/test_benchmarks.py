from __future__ import annotations

import json
from math import isfinite

import pytest

from tuc.benchmarks import BenchmarkError, run_baseline_benchmarks


def test_baseline_benchmark_runs_cpu_cases() -> None:
    report = run_baseline_benchmarks(iterations=2, warmup=1)

    assert report.suite_version == "baseline.v0"
    assert [result.name for result in report.results] == [
        "matmul_64x64",
        "elementwise_relu_4096",
        "reduction_sum_128x64_axis1",
        "softmax_128x32_axis1",
    ]
    assert all(result.device == "cpu" for result in report.results)
    assert all(result.iterations == 2 for result in report.results)
    assert all(result.min_ns >= 0 for result in report.results)
    assert all(isfinite(result.output_checksum) for result in report.results)


def test_baseline_benchmark_reports_cuda_status_without_requiring_cuda() -> None:
    report = run_baseline_benchmarks(iterations=1, warmup=0, include_cuda=True)

    cuda_status = next(device for device in report.devices if device.name == "cuda")
    assert cuda_status.available is False
    assert "no executable CUDA backend" in cuda_status.reason


def test_baseline_benchmark_can_fail_closed_when_cuda_is_required() -> None:
    with pytest.raises(BenchmarkError, match="CUDA benchmark device is unavailable"):
        run_baseline_benchmarks(iterations=1, warmup=0, include_cuda=True, require_cuda=True)


def test_baseline_benchmark_rejects_invalid_iteration_budget() -> None:
    with pytest.raises(BenchmarkError, match="iterations"):
        run_baseline_benchmarks(iterations=0)


def test_baseline_benchmark_report_is_json_serializable() -> None:
    report = run_baseline_benchmarks(iterations=1, warmup=0)

    payload = json.loads(report.to_json())

    assert payload["suite_version"] == "baseline.v0"
    assert len(payload["results"]) == 4
