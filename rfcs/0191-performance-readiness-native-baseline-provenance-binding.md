# RFC 0191: Performance Readiness Native Baseline Provenance Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to bounded Native Baseline Provenance Report
evidence for the current Kernel Ingress proof slice.

This RFC does not run benchmarks, execute native artifacts, access devices,
inspect host hardware, discover plugins, load dynamic libraries, read raw
benchmark output, ingest timing samples, or claim native performance parity.

## Motivation

The performance proof boundary requires native baseline provenance before any
future native performance comparison can be reviewed. Without a provenance
surface, benchmark numbers would have no stable answer to: which native
implementation, for which workload scope, under which toolchain boundary?

The current project has a diagnostic Native Baseline Provenance Report. This RFC
binds that report to the Performance Proof Readiness example while deliberately
keeping reproduction, artifact digests, comparison evidence, and native claims
blocked.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `native_baseline_provenance` present only after:

1. building the accepted Kernel Ingress workload-scope report;
2. extracting every accepted workload scope ID from that report;
3. building a Native Baseline Provenance Report with one data-only baseline
   candidate per workload scope;
4. verifying diagnostic-only artifact status, blocked performance-claim status,
   `performance_proof_boundary.blocking.v0`, `native_performance_claim = false`,
   and `native_baseline_ready = false`;
5. verifying each candidate remains `documented_not_executed`, omits artifact
   digests, and exposes no host paths, environment data, device identifiers, or
   hardware serials.

The current candidate class is a portable CPU native-library baseline surface.
It is intentionally not a native performance result and not a GPU-centered
default.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding uses only existing Kernel Ingress workload-scope metadata and
bounded native baseline identifiers. It must not execute generated code, execute
native code, inspect host hardware, read environment variables, discover
plugins, load dynamic libraries, invoke subprocesses, store native code, or load
benchmark artifacts.

Native baseline comparison, benchmark artifact manifests, break-even workload
validation, executable backend security review, performance threshold policy,
and performance acceptance criteria remain separate blockers.

## Consequences

- Performance Proof Readiness now has a concrete native baseline provenance
  evidence item.
- Future native comparisons have a scope-bound provenance surface to reference.
- Native performance parity remains blocked until comparison artifacts,
  reproducibility, break-even evidence, and executable backend security are
  reviewed separately.