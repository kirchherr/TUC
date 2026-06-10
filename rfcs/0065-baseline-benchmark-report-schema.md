# RFC 0065: Baseline Benchmark Report Schema

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Delta / Epsilon

## Summary

TUC adds a schema-versioned, diagnostic-only JSON report contract for the
existing CPU-first baseline benchmark harness.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, hardware discovery, generated-artifact
execution, raw timing sample storage, benchmark artifact approval, plugin
discovery, dynamic libraries, subprocess execution, or hardware-specific
HAC-IR semantics.

## Motivation

The baseline harness is useful for local drift and CI smoke checks, but its JSON
output must not become an accidental native performance proof.

RFC 0064 requires `benchmark_report_schema` evidence before native performance
proposals can pass readiness. This RFC supplies the first narrow schema for the
current diagnostic report while keeping performance claims blocked.

## Decision

Add `schemas/baseline_benchmark_report.v0.schema.json` and expose these runtime
report markers:

- `schema_version = "tuc.baseline_benchmark_report.v0"`
- `artifact_status = "diagnostic_only"`
- `claim_boundary = "performance_proof_boundary.blocking.v0"`
- `native_performance_claim = false`
- `suite_version = "baseline.v0"`

The schema is fail-closed with `additionalProperties: false` on every object.
It allows only bounded device status, bounded metadata, and aggregate timing
fields emitted by the current CPU reference-kernel harness.

## Security Boundary

The schema must not include host paths, hardware serials, device identifiers,
plugin entrypoints, backend artifacts, generated code, dynamic-library paths,
cache paths, raw timing samples, or native performance parity fields.

The report remains diagnostic only. It is not a native baseline comparison,
not a planner-overhead report, not benchmark artifact approval, and not a
performance proof.

## Evidence

The implementation adds:

- `schemas/baseline_benchmark_report.v0.schema.json`
- report markers in `src/tuc/benchmarks/baseline.py`
- schema tests in `tests/test_benchmark_report_schema.py`
- runtime report tests in `tests/test_benchmarks.py`
- documentation updates in `docs/BENCHMARKING.md`

## Consequences

- Benchmark report shape is reviewable and versioned.
- Current CPU timing data stays clearly diagnostic.
- Future native performance proposals can cite a schema artifact without
  treating current output as a performance claim.
- Any future executable backend benchmark schema must be a separate RFC.

## Rejected Alternatives

1. Leave benchmark JSON unversioned.

   Rejected because unversioned reports are too easy to misread as informal
   performance evidence.

2. Store raw timing samples in the report.

   Rejected because the current report should stay small, bounded, and
   diagnostic. Raw timing data needs a separate artifact policy.

3. Mark the CPU baseline report as native performance evidence.

   Rejected because native performance proof still requires scoped workload
   claims, native baseline provenance, leaky-abstraction evidence,
   planner-overhead evidence, correctness goldens, and security review.
