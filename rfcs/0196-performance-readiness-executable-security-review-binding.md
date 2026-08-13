# RFC 0196: Performance Readiness Executable Security Review Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to a complete Executable Backend Security
Review Report for the current Kernel Ingress proof slice.

This RFC does not execute backend artifacts, access devices, discover plugins,
load dynamic libraries, run subprocesses, perform network access, execute native
code, execute generated code, inspect cache contents, run benchmarks, load
benchmark artifacts, or claim native performance parity.

## Motivation

The Performance Proof Boundary requires executable-surface security review
before a future performance proof can rely on executable backend behavior. The
project already has a data-only Executable Backend Security Review Report, but
Performance Proof Readiness still treated `executable_backend_security_review`
as missing.

The next useful research step is to make readiness recognize a complete,
digest-bound review metadata surface while keeping actual execution permission
outside this report.

## Decision

Update `examples/performance_proof_readiness.py` so the current Kernel Ingress
readiness proposal marks `executable_backend_security_review` present only
after:

1. building an Executable Backend Security Review Report;
2. listing every executable surface tracked by the report contract;
3. marking every entry `approved_by_maintainers` as review metadata;
4. binding every entry to threat-model, sandbox-model, resource-budget,
   provenance, negative-test/fuzzing-evidence, and SHA-256 digest identifiers;
5. verifying diagnostic-only artifact status, blocked performance-claim status,
   `performance_proof_boundary.blocking.v0`, `native_performance_claim = false`,
   and `executable_backend_security_review_ready = true`;
6. verifying the report exposes no host paths, environment data, device
   identifiers, hardware serials, raw benchmark output, raw timing samples,
   backend artifacts, generated code, native source, dynamic-library paths, or
   plugin entrypoints.

The binding is a security-review metadata gate only. It does not grant runtime
permission to execute any reviewed surface.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding reads only repository-controlled RFC text to compute a digest. It
must not execute generated code, execute native code, load or parse benchmark
report contents, inspect backend artifacts, store timing samples, inspect host
hardware, access devices, read environment variables, discover plugins, load
dynamic libraries, invoke subprocesses, use network access, or inspect cache
contents.

A future implementation that actually enables any executable surface still needs
a dedicated implementation RFC, sandboxing design, tests, and maintainer
approval. Native performance parity remains blocked unless a separate proof
interprets accepted measurement artifacts under the Performance Proof Boundary.

## Consequences

- Performance Proof Readiness can become metadata-complete for the current
  Kernel Ingress proof slice.
- The readiness report may pass while still carrying blocked native performance
  claim identifiers.
- Security review metadata remains separated from executable runtime behavior.