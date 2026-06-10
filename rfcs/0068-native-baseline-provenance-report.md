# RFC 0068: Native Baseline Provenance Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Epsilon

## Summary

TUC adds a diagnostic Native Baseline Provenance Report for reviewing which
native implementation a future performance proof proposes to compare against.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw benchmark
output ingestion, plugin discovery, dynamic libraries, subprocess execution,
native code storage, or hardware-specific HAC-IR semantics.

## Motivation

RFC 0063 identifies native performance parity as a later proof class. A future
performance proof is meaningless unless the native baseline is scoped,
provenanced, reproducible, and separated from the compiler's hardware-neutral
intent layer.

RFC 0064 requires `native_baseline_provenance` evidence before native
performance proposals can pass readiness. This RFC supplies the first narrow
diagnostic report for that evidence class.

## Decision

Add [Native Baseline Provenance Report](../docs/NATIVE_BASELINE_PROVENANCE.md)
with:

- `schemas/native_baseline_provenance_report.v0.schema.json`
- `build_native_baseline_provenance_report(proposal_name, baselines=())`
- `dump_native_baseline_provenance_report(report)`
- report schema version `tuc.native_baseline_provenance_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report records bounded identifiers for baseline, workload scope,
implementation kind, target platform, source provenance, toolchain,
reproducibility status, and artifact digest status.

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

- `schemas/native_baseline_provenance_report.v0.schema.json`
- `examples/native_baseline_provenance.py`
- `docs/NATIVE_BASELINE_PROVENANCE.md`
- `tests/test_native_baseline_provenance_report.py`
- `tests/test_native_baseline_provenance_schema.py`
- report APIs in `src/tuc/proof.py`

## Consequences

- Native baseline candidates become reviewable without native execution.
- Future benchmark proposals can identify the comparison baseline before they
  introduce executable backend or device surfaces.
- The current performance proof remains blocked until native comparison,
  benchmark artifact, correctness, planner-overhead, leaky-abstraction, and
  security evidence exists.

## Rejected Alternatives

1. Store native source paths, command lines, or raw benchmark output in the
   provenance report.

   Rejected because provenance metadata must not become an execution or secret
   leakage surface.

2. Treat documented native baseline provenance as native performance proof.

   Rejected because provenance does not supply timing, correctness comparison,
   benchmark artifacts, planner-overhead analysis, or executable-backend
   security review.

3. Use GPU as the implicit native baseline.

   Rejected because TUC is The Universal Compute. Native baselines must be
   explicit and workload-scoped rather than centered on one hardware class.
