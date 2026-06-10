# RFC 0071: Benchmark Methodology Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Epsilon

## Summary

TUC adds a diagnostic Benchmark Methodology Report for reviewing how future
benchmark measurements are supposed to be taken and summarized.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw benchmark
output ingestion, raw timing sample storage, plugin discovery, dynamic
libraries, subprocess execution, native code storage, or hardware-specific
HAC-IR semantics.

## Motivation

RFC 0063 and RFC 0064 require benchmark methodology before future native
performance proposals can pass readiness. Without a methodology contract,
benchmark artifacts are not reproducible evidence; they are just numbers.

TUC needs a data-only way to state the timer, warmup policy, iteration policy,
statistical summary, isolation level, outlier policy, and reproducibility policy
that a benchmark proposal intends to use.

## Decision

Add [Benchmark Methodology Report](../docs/BENCHMARK_METHODOLOGY_REPORT.md)
with:

- `schemas/benchmark_methodology_report.v0.schema.json`
- `build_benchmark_methodology_report(proposal_name, methodologies=())`
- `dump_benchmark_methodology_report(report)`
- report schema version `tuc.benchmark_methodology_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report records bounded identifiers, timer policy, iteration counts,
statistical policy, isolation level, outlier policy, and reproducibility policy.

## Methodology Data

The v0 report tracks:

- `methodology_id`
- `workload_scope_id`
- `measurement_clock`
- `warmup_iterations`
- `measurement_iterations`
- `statistic_policy`
- `isolation_level`
- `outlier_policy_id`
- `reproducibility_policy_id`

Iteration counts must be explicit and finite.

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, hardware serials, device identifiers, generated
artifacts, plugin entrypoints, backend binaries, dynamic-library paths, cache
paths, native code, shell commands, or backend artifact contents.

The report must not execute backend artifacts.
The report must not load benchmark artifacts.
The report must not access devices.
The report must not add hardware-specific performance knobs to HAC-IR.

The schema is fail-closed with `additionalProperties: false` on every object.

## Evidence

The implementation adds:

- `schemas/benchmark_methodology_report.v0.schema.json`
- `examples/benchmark_methodology_report.py`
- `docs/BENCHMARK_METHODOLOGY_REPORT.md`
- `tests/test_benchmark_methodology_report.py`
- `tests/test_benchmark_methodology_schema.py`
- report APIs in `src/tuc/proof.py`

## Consequences

- Future benchmark measurements must have a reviewable methodology before they
  can become proof evidence.
- Methodology review remains separate from benchmark execution.
- Raw timing samples and native outputs remain outside the compiler boundary.
- Native performance claims remain blocked until the rest of the performance
  proof evidence exists.

## Rejected Alternatives

1. Describe methodology only in prose.

   Rejected because future performance evidence needs deterministic review
   data.

2. Store raw timing samples in the methodology report.

   Rejected because v0 defines measurement policy, not measurement output.

3. Treat a valid methodology as a performance proof.

   Rejected because methodology does not supply workload scope, native baseline
   provenance, benchmark artifacts, planner-overhead analysis,
   leaky-abstraction review, correctness goldens, or executable-backend
   security review.
