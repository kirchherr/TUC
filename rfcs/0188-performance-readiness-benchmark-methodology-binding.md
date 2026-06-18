# RFC 0188: Performance Readiness Benchmark Methodology Binding

- Status: accepted-for-prototype
- Created: 2026-06-18
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to bounded benchmark-methodology evidence for
the accepted Kernel Ingress workload scopes.

This RFC does not run benchmarks, ingest benchmark artifacts, publish raw timing
samples, access devices, execute backend artifacts, or claim native performance
parity.

## Motivation

Performance claims need measurement policy before measurement artifacts are
accepted. TUC already has Kernel Ingress workload scopes and a diagnostic
benchmark-methodology report contract. The methodology evidence should be
counted only when it is explicitly bound to accepted workload scopes.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `benchmark_methodology` present only after:

1. building and contract-checking Kernel Ingress workload-scope evidence;
2. creating one bounded methodology entry per accepted workload scope;
3. validating that the methodology report is ready, diagnostic-only,
   native-claim-blocked, and bound to `performance_proof_boundary.blocking.v0`;
4. verifying that report workload-scope IDs exactly match the accepted Kernel
   Ingress workload-scope IDs.

The methodology uses repository policy IDs for clock, iteration, statistic,
isolation, outlier, and reproducibility behavior. It does not contain measured
timing data.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`

## Security Boundary

The methodology binding reads only repository-controlled workload-scope data and
builds data-only policy entries. It must not read host paths, command lines,
environment variables, raw timing samples, device identifiers, benchmark
artifacts, backend binaries, generated code, or plugin entrypoints.

## Consequences

- Benchmark methodology is now visible as present readiness evidence.
- Benchmark execution and benchmark report artifacts remain separate and
  blocked.
- Native performance readiness remains blocked by the remaining evidence IDs.

