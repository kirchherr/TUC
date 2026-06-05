# RFC 0013: Baseline Benchmark Harness

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds a bounded CPU-first benchmark harness for MVP reference kernels. The
harness can run without CUDA and can report CUDA capability status without
attempting device discovery or backend execution.

## Motivation

Correctness fixtures prove semantics, but TUC also needs a repeatable local
baseline for runtime drift and future backend comparisons. This should happen
before native MLIR and executable backends make performance discussions more
complicated.

## Decision

Add `tuc.benchmarks` with:

- `run_baseline_benchmarks(...)`
- `BenchmarkReport`
- `BenchmarkResult`
- `BenchmarkDeviceStatus`

Add `scripts/benchmark.py` as a stdout-only CLI.

The initial suite measures deterministic CPU reference kernels for MatMul,
Elementwise ReLU, Sum Reduction, and Softmax.

## Security Model

The benchmark harness is not a plugin runner:

- It uses fixed in-repository reference kernels.
- It does not import user-selected modules.
- It does not execute generated code.
- It does not invoke hardware-discovery subprocesses.
- It does not write files.
- Iteration and warmup counts are bounded.

CUDA is represented as explicit status. `--include-cuda` reports that no
executable CUDA backend exists yet; `--require-cuda` fails closed.

## Consequences

- TUC has a repeatable CPU baseline that runs in the default Docker environment.
- Future executable backends can compare against the same semantic cases.
- CUDA support remains opt-in and threat-modeled instead of being guessed from
  the host environment.

## Follow-Up

1. Add benchmark artifact schema once CI stores benchmark reports.
2. Add executable CUDA benchmark cases after a CUDA backend contract exists.
3. Add backend-vs-reference comparisons once backend execution exists.
4. Add variance controls and regression thresholds only after baseline data is
   collected.
