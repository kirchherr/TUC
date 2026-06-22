# RFC 0192: Performance Readiness Native Baseline Comparison Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to bounded Native Baseline Comparison Report
metadata for the current Kernel Ingress proof slice.

This RFC does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, access devices, execute backend artifacts,
invoke subprocesses, or claim native performance parity.

## Motivation

A native baseline provenance surface identifies candidate native implementations,
but a future performance proof also needs an explicit comparison surface between
TUC baseline artifacts and native benchmark artifacts. Without that comparison
metadata, benchmark artifacts would be hard to review and easy to confuse with
unbounded native performance claims.

The current project already has a diagnostic Native Baseline Comparison Report.
This RFC binds that report to the Performance Proof Readiness example while
keeping measurement, digest validation, artifact loading, and native claims
blocked.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `native_baseline_comparison` present only after:

1. building the accepted Kernel Ingress workload-scope report;
2. extracting every accepted workload scope ID from that report;
3. building a Native Baseline Comparison Report with one data-only comparison
   reference per workload scope;
4. verifying diagnostic-only artifact status, blocked performance-claim status,
   `performance_proof_boundary.blocking.v0`, `native_performance_claim = false`,
   and `native_baseline_comparison_ready = false`;
5. verifying every comparison is `not_measured`, omits comparison digests, and
   exposes no host paths, environment data, device identifiers, hardware serials,
   or raw timing samples.

The comparison entries reference future baseline and native artifact IDs only.
They do not load, validate, or compare benchmark artifact contents.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding uses only existing Kernel Ingress workload-scope metadata and
bounded comparison identifiers. It must not execute generated code, execute
native code, load benchmark artifacts, parse raw benchmark output, store timing
samples, inspect host hardware, access devices, read environment variables,
discover plugins, load dynamic libraries, or invoke subprocesses.

Benchmark artifact manifests, break-even workload validation, executable backend
security review, performance threshold policy, and performance acceptance
criteria remain separate blockers.

## Consequences

- Performance Proof Readiness now has a concrete native baseline comparison
  metadata item.
- Future benchmark artifacts have a scope-bound comparison surface to reference.
- Native performance parity remains blocked until benchmark artifacts, digest
  validation, break-even evidence, and executable backend security are reviewed
  separately.