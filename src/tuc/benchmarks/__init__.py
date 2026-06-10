"""Benchmark helpers for TUC prototype validation."""

from tuc.benchmarks.baseline import (
    BENCHMARK_REPORT_ARTIFACT_STATUS,
    BENCHMARK_REPORT_CLAIM_BOUNDARY,
    BENCHMARK_REPORT_SCHEMA_VERSION,
    BENCHMARK_SUITE_VERSION,
    MAX_BENCHMARK_DEVICES,
    MAX_BENCHMARK_ITERATIONS,
    MAX_BENCHMARK_RESULTS,
    MAX_BENCHMARK_WARMUP,
    BenchmarkDeviceStatus,
    BenchmarkError,
    BenchmarkReport,
    BenchmarkResult,
    run_baseline_benchmarks,
)

__all__ = [
    "BENCHMARK_REPORT_ARTIFACT_STATUS",
    "BENCHMARK_REPORT_CLAIM_BOUNDARY",
    "BENCHMARK_REPORT_SCHEMA_VERSION",
    "BENCHMARK_SUITE_VERSION",
    "MAX_BENCHMARK_DEVICES",
    "MAX_BENCHMARK_ITERATIONS",
    "MAX_BENCHMARK_RESULTS",
    "MAX_BENCHMARK_WARMUP",
    "BenchmarkDeviceStatus",
    "BenchmarkError",
    "BenchmarkReport",
    "BenchmarkResult",
    "run_baseline_benchmarks",
]
