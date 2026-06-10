# Benchmark Methodology Report

Benchmark Methodology Report is a diagnostic artifact for reviewing how future
benchmark measurements are supposed to be taken and summarized.

It does not run benchmarks, load benchmark artifacts, execute backend artifacts,
access devices, inspect host hardware, discover plugins, load dynamic
libraries, run subprocesses, store raw timing samples, store raw benchmark
output, or claim native performance parity.

## Contract

- Report schema: `schemas/benchmark_methodology_report.v0.schema.json`
- Report schema version: `tuc.benchmark_methodology_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_benchmark_methodology_report(proposal_name, methodologies=())`
- Dump API: `dump_benchmark_methodology_report(report)`
- Example: `examples/benchmark_methodology_report.py`
- Tests: `tests/test_benchmark_methodology_report.py`
- Schema tests: `tests/test_benchmark_methodology_schema.py`

The report is not a native performance proof. It defines the measurement policy
that future benchmark artifacts must follow.

## Methodology Fields

Each methodology entry is data-only and bounded:

- `methodology_id`: stable methodology identifier
- `workload_scope_id`: workload scope covered by the methodology
- `measurement_clock`: `monotonic_ns`, `device_event_timer`, or
  `external_profiler`
- `warmup_iterations`: bounded warmup iteration count
- `measurement_iterations`: bounded measurement iteration count
- `statistic_policy`: `min_median_mean`, `median_iqr`, or
  `confidence_interval`
- `isolation_level`: `none`, `process_isolated`, `dedicated_runner`, or
  `ci_controlled`
- `outlier_policy_id`: stable outlier policy identifier
- `reproducibility_policy_id`: stable reproducibility policy identifier

The report intentionally accepts identifiers and aggregate policy choices, not
raw timing samples, command lines, environment variables, host paths, backend
binaries, generated code, or device details.

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, hardware serials, device identifiers, generated
artifacts, plugin entrypoints, backend binaries, dynamic-library paths, cache
paths, native code, shell commands, or backend artifact contents.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not execute backend code and does not load benchmark artifacts.
It is a benchmark policy review surface only.

## Current Status

The current report can identify bounded methodology policies and keep benchmark
measurements tied to explicit workload scopes, timers, warmup policies,
iteration policies, statistics, isolation, outlier handling, and
reproducibility policy.

`benchmark_methodology_ready` means only that at least one bounded methodology
policy is present. Native performance claims remain blocked in v0.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- benchmark artifact acceptance as proof
- raw benchmark result ingestion
- native benchmark execution
- executable backend benchmarking without a dedicated security RFC
- device access, generated-artifact execution, dynamic-library loading, or
  subprocess execution as part of proof review
