# RFC 0187: Performance Readiness Benchmark Schema Binding

- Status: accepted-for-prototype
- Created: 2026-06-18
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to the fail-closed baseline benchmark report
schema for the `benchmark_report_schema` evidence ID.

This RFC does not run benchmarks, accept benchmark artifacts, publish raw timing
samples, access devices, execute backend artifacts, or claim native performance
parity.

## Motivation

Performance Proof Readiness requires both a benchmark report schema and
benchmark report artifacts. These are different proof obligations.

TUC already has a bounded diagnostic baseline benchmark report schema. That
schema can count as `benchmark_report_schema` evidence only if it remains:

- fail-closed through `additionalProperties: false`;
- diagnostic-only;
- bound to `performance_proof_boundary.blocking.v0`;
- explicit that `native_performance_claim` is false.

Benchmark artifacts remain separate and blocked.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `benchmark_report_schema` present only after checking
`schemas/baseline_benchmark_report.v0.schema.json`.

The check verifies schema identity, boundary constants, diagnostic artifact
status, native-claim blocking, suite/schema version constants, and absence of
forbidden evidence surfaces such as raw timing samples, backend artifacts,
generated code, host paths, device identifiers, or plugin entrypoints.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `schemas/baseline_benchmark_report.v0.schema.json`

## Security Boundary

The binding reads only repository-controlled schema data. It must not load
benchmark artifacts, parse raw benchmark output, inspect host hardware, read
environment variables, access devices, run subprocesses, discover plugins, or
execute generated/native code.

## Consequences

- The schema proof obligation is now recognized by readiness.
- Benchmark report artifacts remain missing until separate bounded artifacts
  exist and are accepted.
- Native performance readiness remains blocked.

