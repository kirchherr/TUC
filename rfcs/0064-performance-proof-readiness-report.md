# RFC 0064: Performance Proof Readiness Report

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Alpha / Delta / Epsilon

## Summary

TUC adds a deterministic readiness report for future native performance proof
proposals.

This RFC does not run benchmarks, add native benchmark suites, ingest benchmark
artifacts, claim native performance parity, access devices, inspect host
hardware, execute backend artifacts, execute generated code, discover plugins,
load dynamic libraries, does not run subprocesses, or add hardware-specific
HAC-IR semantics.

This RFC does not claim native performance parity.

## Motivation

RFC 0063 defines the Performance Proof Boundary. Maintainers also need a stable
way to review whether a future performance proof proposal has every required
piece of evidence before a claim can be made.

The readiness report makes leaky-abstraction and planner-overhead gaps visible
in deterministic JSON without importing benchmark data, touching hardware, or
executing backend code.

## Decision

Add [Performance Proof Readiness Report](../docs/PERFORMANCE_PROOF_READINESS.md)
with:

- `PerformanceProofReadinessEvidence`
- `build_performance_proof_readiness_report(proposal_name, evidence)`
- `assert_performance_proof_readiness(proposal_name, evidence)`
- `dump_performance_proof_readiness_report(report)`
- report schema version `tuc.performance_proof_readiness_report.v0`
- boundary contract `performance_proof_boundary.blocking.v0`
- blocked claims constant `PERFORMANCE_PROOF_BLOCKED_CLAIMS`

The report is ready only when every required evidence ID is present.

## Required Evidence IDs

The v0 report requires:

- `performance_proof_rfc`
- `performance_claim_threshold_policy`
- `benchmark_methodology`
- `native_baseline_provenance`
- `versioned_toolchain_environment`
- `workload_scope`
- `correctness_goldens`
- `native_baseline_comparison`
- `leaky_abstraction_report`
- `planner_overhead_report`
- `break_even_workload_size`
- `runtime_plan_goldens`
- `compiler_decision_report_goldens`
- `benchmark_report_schema`
- `benchmark_report_artifacts`
- `executable_backend_security_review`

## Security Boundary

The readiness report accepts only explicit evidence IDs and booleans. It must
not include raw benchmark output, timing samples, host paths, environment data,
hardware serials, device identifiers, generated artifacts, plugin entrypoints,
backend binaries, dynamic-library paths, cache paths, or backend artifact
contents.

Unknown evidence IDs and duplicate evidence IDs fail closed.

The report does not validate performance measurements. Measurement semantics,
benchmark report schemas, native baseline provenance, and executable backend
security review remain separate future artifacts.

Performance measurements remain blocked.

## Evidence

The implementation adds:

- `src/tuc/proof.py`
- `examples/performance_proof_readiness.py`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`

The golden report intentionally remains blocked because no native performance
proof proposal has supplied the required evidence.

## Consequences

- Native performance proposals become reviewable before claims are made.
- Leaky abstraction and planner overhead become machine-readable blockers.
- Performance proof review remains separated from benchmark execution and
  device access.
- HAC-IR neutrality is protected from performance-specific hardware knobs.

## Rejected Alternatives

1. Track readiness in prose only.

   Rejected because performance proof readiness needs deterministic review
   evidence.

2. Allow raw benchmark results inside the readiness report.

   Rejected because readiness is a gate, not a measurement artifact, and raw
   benchmark data can leak host-specific or device-specific information.

3. Treat partial evidence as enough for native performance claims.

   Rejected because both leaky abstraction and planner overhead must be
   addressed before such claims are credible.
