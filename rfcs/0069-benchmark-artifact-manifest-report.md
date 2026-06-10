# RFC 0069: Benchmark Artifact Manifest Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Epsilon

## Summary

TUC adds a diagnostic Benchmark Artifact Manifest Report for reviewing which
benchmark report artifacts a future native performance proposal claims to have.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw benchmark
output ingestion, raw timing sample storage, plugin discovery, dynamic
libraries, subprocess execution, native code storage, or hardware-specific
HAC-IR semantics.

## Motivation

RFC 0063 and RFC 0064 require benchmark report artifacts before future native
performance proposals can pass readiness. A benchmark artifact gate needs a
safe inventory format before TUC can accept any artifact evidence.

Without a bounded manifest, benchmark evidence could accidentally become a path
ingestion surface, a raw-output storage surface, or a disguised executable
backend artifact.

## Decision

Add [Benchmark Artifact Manifest Report](../docs/BENCHMARK_ARTIFACT_MANIFEST.md)
with:

- `schemas/benchmark_artifact_manifest_report.v0.schema.json`
- `build_benchmark_artifact_manifest_report(proposal_name, artifacts=())`
- `dump_benchmark_artifact_manifest_report(report)`
- report schema version `tuc.benchmark_artifact_manifest_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report records bounded identifiers, artifact kinds, schema versions,
SHA-256 digest status, and storage scopes for benchmark report artifacts.

## Required Artifact Kinds

The v0 manifest tracks:

- `baseline_benchmark_report`
- `native_benchmark_report`
- `native_baseline_comparison_report`

Missing kinds remain explicit report issues.

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

- `schemas/benchmark_artifact_manifest_report.v0.schema.json`
- `examples/benchmark_artifact_manifest.py`
- `docs/BENCHMARK_ARTIFACT_MANIFEST.md`
- `tests/test_benchmark_artifact_manifest_report.py`
- `tests/test_benchmark_artifact_manifest_schema.py`
- report APIs in `src/tuc/proof.py`

## Consequences

- Benchmark artifact evidence becomes inventory-first and reviewable.
- Future benchmark proposals can list report artifacts without loading them.
- Raw timing samples and native outputs remain outside the compiler boundary.
- Native performance claims remain blocked until the rest of the performance
  proof evidence exists.

## Rejected Alternatives

1. Store benchmark artifact paths in the manifest.

   Rejected because host paths and URLs are not needed for compiler review and
   can leak local or infrastructure details.

2. Embed raw benchmark output in the manifest.

   Rejected because the manifest is an inventory contract, not a benchmark
   result format.

3. Treat a complete manifest as native performance proof.

   Rejected because manifest completeness does not supply methodology review,
   correctness comparison, planner-overhead analysis, leaky-abstraction review,
   native baseline provenance, or executable-backend security review.
