# Baseline Benchmarking

TUC has a small CPU-first benchmark harness for the MVP reference kernels.

## Scope

The harness measures:

- `matmul_64x64`
- `elementwise_relu_4096`
- `reduction_sum_128x64_axis1`
- `softmax_128x32_axis1`

The benchmark uses deterministic NumPy inputs and the reference kernels in
`tuc.reference`. It emits a JSON report to stdout.

The report shape is versioned by
`schemas/baseline_benchmark_report.v0.schema.json`.

## Run

Inside the Docker development container:

```bash
python scripts/benchmark.py
```

For a faster smoke run:

```bash
python scripts/benchmark.py --iterations 2 --warmup 1
```

To include CUDA capability status without requiring CUDA:

```bash
python scripts/benchmark.py --include-cuda
```

To fail closed when CUDA benchmarks are requested but unavailable:

```bash
python scripts/benchmark.py --include-cuda --require-cuda
```

## Security Rules

The baseline harness is intentionally narrow:

- It runs CPU NumPy reference kernels only.
- It does not import backend plugins.
- It does not execute generated code.
- It does not scan the host for GPUs or invoke hardware-discovery subprocesses.
- It does not include raw timing samples, host paths, hardware serials, device
  identifiers, plugin entrypoints, backend artifacts, or generated code in the
  report.
- Iteration and warmup counts are bounded.
- Output is written to stdout; callers can redirect it if they need artifacts.

CUDA is represented as explicit capability status until TUC has an executable
CUDA backend path and a dedicated threat model for device execution.

## Current Limitations

This is not a performance claim. It is a repeatable baseline for local drift,
CI smoke checks, and future comparisons against executable backends.

Every report includes:

- `schema_version = "tuc.baseline_benchmark_report.v0"`
- `artifact_status = "diagnostic_only"`
- `claim_boundary = "performance_proof_boundary.blocking.v0"`
- `native_performance_claim = false`

Performance proof claims are gated by
[Performance Proof Boundary](PERFORMANCE_PROOF_BOUNDARY.md). Baseline benchmark
output must not be used as a native performance parity claim until leaky
abstraction evidence, planner-overhead evidence, native baseline provenance,
correctness goldens, and security review exist.

Future native performance proposals must also pass the
[Performance Proof Readiness Report](PERFORMANCE_PROOF_READINESS.md). That
readiness report does not run benchmarks, does not ingest raw benchmark output,
and does not turn local timing data into a proof claim.

Planner timing is tracked separately by the
[Planner Overhead Report](PLANNER_OVERHEAD_REPORT.md). Baseline benchmark
reports must not hide planner overhead inside execution timing.
