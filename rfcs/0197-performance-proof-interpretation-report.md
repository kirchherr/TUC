# RFC 0197: Performance Proof Interpretation Report

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Add a data-only Performance Proof Interpretation Report after Performance Proof
Readiness.

This RFC does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, parse raw timing samples, access devices, inspect host hardware,
execute backend artifacts, execute generated code, discover plugins, load
dynamic libraries, run subprocesses, or claim native performance parity.

## Motivation

Performance Proof Readiness can now be metadata-complete for the current Kernel
Ingress proof slice. That is useful, but it must not be confused with a native
performance proof.

The next practical safety step is a separate interpretation gate that says:
readiness is complete, but accepted measurement interpretation artifacts are
not yet supplied, so native performance claims remain blocked.

## Decision

Add `performance_proof_interpretation_report.v0` with:

1. schema-versioned diagnostic JSON output;
2. a builder and deterministic dump API;
3. a current Kernel Ingress example and golden artifact;
4. explicit linkage to the Performance Proof Boundary and readiness proposal;
5. bounded measurement-interpretation artifact IDs only;
6. no raw benchmark output, timing samples, paths, device IDs, backend
   artifacts, generated code, native source, dynamic-library paths, plugin
   entrypoints, or execution permission.

The current report must show `readiness_ready = true`,
`measurement_interpretation_status = not_supplied`,
`performance_proof_interpretation_ready = false`, and
`native_performance_claim = false`.

## Evidence

- `src/tuc/proof.py`
- `schemas/performance_proof_interpretation_report.v0.schema.json`
- `examples/performance_proof_interpretation.py`
- `tests/test_performance_proof_interpretation.py`
- `tests/golden/proofs/performance_proof_interpretation_report.json`
- `docs/PERFORMANCE_PROOF_INTERPRETATION.md`

## Consequences

- Readiness and performance interpretation are separate review steps.
- A green readiness report cannot silently become a native performance claim.
- Future benchmark work needs accepted measurement interpretation artifacts
  before performance-proof interpretation can be complete.
