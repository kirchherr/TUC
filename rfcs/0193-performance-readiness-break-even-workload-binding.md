# RFC 0193: Performance Readiness Break-Even Workload Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to bounded Break-Even Workload Size Report
metadata for the current Kernel Ingress proof slice.

This RFC does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, access devices, execute backend artifacts,
invoke subprocesses, or claim planner benefit or native performance parity.

## Motivation

The performance proof boundary identifies planner overhead as a blocker, but a
future performance proof also needs to explain where planning cost is expected
to amortize. Without a bounded break-even surface, runtime planning can look
plausible in prose while remaining unreviewable against concrete workload
scopes.

The current project already has a diagnostic Break-Even Workload Size Report.
This RFC binds that report to the Performance Proof Readiness example while
keeping CI validation, evidence digests, benchmark artifact loading, timing
comparison, planner-benefit claims, and native performance claims blocked.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `break_even_workload_size` present only after:

1. building the accepted Kernel Ingress workload-scope report;
2. extracting every accepted workload scope and its bounded `problem_size_max`;
3. building a Break-Even Workload Size Report with one
   `estimated_not_validated` entry per workload scope;
4. verifying diagnostic-only artifact status, blocked performance-claim status,
   `performance_proof_boundary.blocking.v0`, `native_performance_claim = false`,
   and `break_even_workload_size_ready = false`;
5. verifying every entry uses the workload scope's `problem_size_max`, references
   the Kernel Ingress planner-overhead report ID, omits evidence digests, and
   exposes no host paths, environment data, device identifiers, hardware
   serials, or raw timing samples.

The break-even entries are bounded amortization metadata only. They do not load,
validate, or compare benchmark artifact contents.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding uses only existing Kernel Ingress workload-scope metadata and
bounded amortization identifiers. It must not execute generated code, execute
native code, load benchmark artifacts, parse raw benchmark output, store timing
samples, inspect host hardware, access devices, read environment variables,
discover plugins, load dynamic libraries, or invoke subprocesses.

CI validation, evidence digests, benchmark artifact manifests, executable
backend security review, performance threshold policy, performance acceptance
criteria, and native baseline measurement remain separate blockers.

## Consequences

- Performance Proof Readiness now has a concrete break-even workload-size
  metadata item.
- Future benchmark artifacts have an explicit amortization review surface to
  reference.
- Planner-benefit and native performance parity remain blocked until benchmark
  artifacts, digest validation, timing comparison, and executable backend
  security are reviewed separately.