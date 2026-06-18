# RFC 0189: Performance Readiness Leaky Abstraction Binding

- Status: accepted-for-prototype
- Created: 2026-06-18
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to Kernel Ingress leaky-abstraction evidence.

This RFC does not run benchmarks, ingest benchmark artifacts, access devices,
execute backend artifacts, publish raw timing samples, or claim native
performance parity.

## Motivation

The leaky-abstraction problem is one of TUC's central research risks. TUC must
show that performance-critical facts can exist without entering HAC-IR
semantics. If those facts leak into HAC-IR, hardware independence collapses into
vendor-specific optimization knobs.

The current Kernel Ingress MVP pipeline is the right narrow proof slice for this
binding because it already passes through realistic source-shaped input,
Source Intent, metadata conversion, HAC-IR, runtime planning, and compiler
decision evidence.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks `leaky_abstraction_report` present only after:

1. building the accepted Kernel Ingress MVP pipeline graph;
2. producing HAC-IR through the normal compiler path;
3. building a leaky-abstraction report with performance facts assigned outside
   HAC-IR;
4. verifying contract-valid HAC-IR, no detected hardware-specific leaks, no
   facts entering HAC-IR, diagnostic-only status, blocked performance-claim
   status, and `performance_proof_boundary.blocking.v0`.

The bound performance facts cover tile shape, vector width, transfer latency,
and backend sequence choice. Their homes are backend implementation, backend
capability, runtime plan, and compiler decision report.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`

## Security Boundary

The binding uses only repository-controlled graph construction and diagnostic
report data. It must not read host paths, execute generated/native code, inspect
devices, discover plugins, load dynamic libraries, ingest benchmark artifacts,
or expose raw timing samples.

## Consequences

- Leaky-abstraction evidence now counts toward Performance Proof Readiness.
- Native baseline, benchmark artifacts, break-even validation, executable
  backend security review, and performance governance remain separate blockers.
- HAC-IR neutrality stays reviewable before any native performance claim can be
  considered.

