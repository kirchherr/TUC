"""CPU-first baseline benchmark harness for TUC reference kernels."""

from __future__ import annotations

import json
import platform
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from statistics import fmean, median
from time import perf_counter_ns

import numpy as np

from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT
from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
    reference_softmax,
)
from tuc.reference.kernels import FloatArray

MAX_BENCHMARK_ITERATIONS = 10_000
MAX_BENCHMARK_WARMUP = 1_000
MAX_BENCHMARK_RESULTS = 16
MAX_BENCHMARK_DEVICES = 8
BENCHMARK_SUITE_VERSION = "baseline.v0"
BENCHMARK_REPORT_SCHEMA_VERSION = "tuc.baseline_benchmark_report.v0"
BENCHMARK_REPORT_ARTIFACT_STATUS = "diagnostic_only"
BENCHMARK_REPORT_CLAIM_BOUNDARY = PERFORMANCE_PROOF_BOUNDARY_CONTRACT


class BenchmarkError(ValueError):
    """Raised when benchmark configuration is invalid or unavailable."""


@dataclass(frozen=True)
class BenchmarkDeviceStatus:
    """Availability status for one benchmark device class."""

    name: str
    available: bool
    reason: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "available": self.available,
            "name": self.name,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BenchmarkResult:
    """Timing result for one benchmark case."""

    name: str
    operation: str
    device: str
    iterations: int
    warmup: int
    min_ns: int
    median_ns: float
    mean_ns: float
    output_checksum: float

    def to_mapping(self) -> dict[str, object]:
        return {
            "device": self.device,
            "iterations": self.iterations,
            "mean_ns": self.mean_ns,
            "median_ns": self.median_ns,
            "min_ns": self.min_ns,
            "name": self.name,
            "operation": self.operation,
            "output_checksum": self.output_checksum,
            "warmup": self.warmup,
        }


@dataclass(frozen=True)
class BenchmarkReport:
    """Complete benchmark report emitted by the baseline harness."""

    suite_version: str
    devices: tuple[BenchmarkDeviceStatus, ...]
    results: tuple[BenchmarkResult, ...]
    metadata: dict[str, str]

    def to_mapping(self) -> dict[str, object]:
        return {
            "artifact_status": BENCHMARK_REPORT_ARTIFACT_STATUS,
            "claim_boundary": BENCHMARK_REPORT_CLAIM_BOUNDARY,
            "devices": [device.to_mapping() for device in self.devices],
            "metadata": dict(self.metadata),
            "native_performance_claim": False,
            "results": [result.to_mapping() for result in self.results],
            "schema_version": BENCHMARK_REPORT_SCHEMA_VERSION,
            "suite_version": self.suite_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_mapping(), indent=2, sort_keys=True)


@dataclass(frozen=True)
class _BenchmarkCase:
    name: str
    operation: str
    runner: Callable[[], FloatArray]


def run_baseline_benchmarks(
    *,
    iterations: int = 20,
    warmup: int = 3,
    include_cuda: bool = False,
    require_cuda: bool = False,
) -> BenchmarkReport:
    """Run bounded CPU reference benchmarks and report CUDA capability status."""

    _require_bounded_int(iterations, "iterations", minimum=1, maximum=MAX_BENCHMARK_ITERATIONS)
    _require_bounded_int(warmup, "warmup", minimum=0, maximum=MAX_BENCHMARK_WARMUP)
    if require_cuda and not include_cuda:
        raise BenchmarkError("require_cuda needs include_cuda=True")

    devices = _device_statuses(include_cuda=include_cuda)
    cuda_status = next(device for device in devices if device.name == "cuda")
    if require_cuda and not cuda_status.available:
        raise BenchmarkError(f"CUDA benchmark device is unavailable: {cuda_status.reason}")

    results = tuple(_run_case(case, iterations=iterations, warmup=warmup) for case in _cases())
    return BenchmarkReport(
        suite_version=BENCHMARK_SUITE_VERSION,
        devices=devices,
        results=results,
        metadata={
            "numpy_version": np.__version__,
            "python_version": platform.python_version(),
            "system": platform.system(),
        },
    )


def _run_case(
    case: _BenchmarkCase,
    *,
    iterations: int,
    warmup: int,
) -> BenchmarkResult:
    for _ in range(warmup):
        case.runner()

    durations: list[int] = []
    checksum = 0.0
    for _ in range(iterations):
        start = perf_counter_ns()
        result = case.runner()
        end = perf_counter_ns()
        durations.append(end - start)
        checksum = _checksum(result)

    return BenchmarkResult(
        name=case.name,
        operation=case.operation,
        device="cpu",
        iterations=iterations,
        warmup=warmup,
        min_ns=min(durations),
        median_ns=float(median(durations)),
        mean_ns=fmean(durations),
        output_checksum=checksum,
    )


def _cases() -> tuple[_BenchmarkCase, ...]:
    matmul_left = np.linspace(-1.0, 1.0, num=64 * 64, dtype=np.float64).reshape(64, 64)
    matmul_right = np.linspace(0.5, 1.5, num=64 * 64, dtype=np.float64).reshape(64, 64)
    elementwise_value = np.linspace(-4.0, 4.0, num=4096, dtype=np.float64)
    reduction_value = np.linspace(-2.0, 2.0, num=128 * 64, dtype=np.float64).reshape(128, 64)
    softmax_value = np.linspace(-3.0, 3.0, num=128 * 32, dtype=np.float64).reshape(128, 32)

    return (
        _BenchmarkCase(
            name="matmul_64x64",
            operation="matmul",
            runner=lambda: reference_matmul(matmul_left, matmul_right),
        ),
        _BenchmarkCase(
            name="elementwise_relu_4096",
            operation="elementwise.relu",
            runner=lambda: reference_elementwise(elementwise_value, "relu"),
        ),
        _BenchmarkCase(
            name="reduction_sum_128x64_axis1",
            operation="reduction.sum",
            runner=lambda: reference_reduction_sum(reduction_value, axis=1),
        ),
        _BenchmarkCase(
            name="softmax_128x32_axis1",
            operation="softmax",
            runner=lambda: reference_softmax(softmax_value, axis=1),
        ),
    )


def _device_statuses(*, include_cuda: bool) -> tuple[BenchmarkDeviceStatus, ...]:
    cpu = BenchmarkDeviceStatus(
        name="cpu",
        available=True,
        reason="NumPy reference kernels are available",
    )
    cuda = BenchmarkDeviceStatus(
        name="cuda",
        available=False,
        reason=(
            "not requested"
            if not include_cuda
            else "no executable CUDA backend is defined in the Phase 1 benchmark harness"
        ),
    )
    return (cpu, cuda)


def _checksum(result: FloatArray) -> float:
    checksum = float(np.sum(result, dtype=np.float64))
    if not isfinite(checksum):
        raise BenchmarkError("benchmark output checksum must be finite")
    return checksum


def _require_bounded_int(value: int, label: str, *, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BenchmarkError(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise BenchmarkError(f"{label} must be between {minimum} and {maximum}")


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
