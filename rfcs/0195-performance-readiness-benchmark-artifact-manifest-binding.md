# RFC 0195: Performance Readiness Benchmark Artifact Manifest Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to a complete Benchmark Artifact Manifest for
the current Kernel Ingress proof slice.

This RFC does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, access devices, execute backend artifacts,
invoke subprocesses, validate native comparison results, or claim native
performance parity.

## Motivation

The performance proof boundary requires benchmark report artifacts before a
future native performance proposal can be reviewed. The project already has a
fail-closed Benchmark Artifact Manifest Report contract, but Performance Proof
Readiness still treated `benchmark_report_artifacts` as missing.

The next useful research step is to make readiness recognize a complete,
digest-bound artifact inventory while keeping artifact contents, benchmark
result acceptance, executable backend security review, and native performance
claims separate.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `benchmark_report_artifacts` present only after:

1. building a Benchmark Artifact Manifest Report;
2. listing all required artifact kinds: baseline benchmark report, native
   benchmark report, and native baseline comparison report;
3. binding every artifact entry to a repository-golden descriptor with a
   `sha256:` digest;
4. verifying diagnostic-only artifact status, blocked performance-claim status,
   `performance_proof_boundary.blocking.v0`, `native_performance_claim = false`,
   and `benchmark_artifact_manifest_complete = true`;
5. verifying the manifest entries expose no host paths, URLs, environment data,
   device identifiers, hardware serials, raw timing samples, raw benchmark
   output, or backend artifact contents.

The repository-golden descriptors are manifest review objects. They are not raw
benchmark reports and are not interpreted as native performance evidence by the
readiness example.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `tests/golden/proofs/benchmark_artifacts/`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding reads only repository-controlled descriptor files to compute
digests. It must not execute generated code, execute native code, load or parse
benchmark report contents, store timing samples, inspect host hardware, access
devices, read environment variables, discover plugins, load dynamic libraries,
or invoke subprocesses.

Executable backend security review remains a separate blocker. Native
performance parity remains blocked.

## Consequences

- Performance Proof Readiness now has a complete benchmark artifact inventory
  surface for the current Kernel Ingress proof slice.
- Future benchmark proposals can replace descriptors with accepted report
  artifacts without changing the readiness evidence ID.
- The readiness report still fails until executable backend security review is
  supplied separately.