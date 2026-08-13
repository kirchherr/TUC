# RFC 0194: Performance Readiness Governance Binding

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Alpha / Epsilon

## Summary

Bind Performance Proof Readiness to accepted, digest-pinned governance metadata
for the current Kernel Ingress proof slice.

This RFC does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, access devices, execute backend artifacts,
invoke subprocesses, grant execution permission, or claim native performance
parity.

## Motivation

Performance evidence is not reviewable unless the claim contract is defined
before results are interpreted. The current readiness report already checks
workload scope, methodology, toolchain metadata, native-baseline provenance,
native comparison metadata, planner overhead, break-even metadata,
leaky-abstraction evidence, and goldens. It still lacked a bound governance
surface for the claim proposal, threshold policy, and acceptance criteria.

The next useful research step is to make these governance gates present as
bounded data while keeping benchmark artifacts and executable-backend security
review as explicit remaining blockers.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks these evidence IDs present only after contract-checking
accepted, digest-pinned governance reports for every accepted Kernel Ingress
workload scope:

- `performance_proof_rfc`
- `performance_claim_threshold_policy`
- `performance_acceptance_criteria`

The binding must:

1. build the accepted Kernel Ingress workload-scope report;
2. extract every accepted workload scope ID;
3. build a Performance Proof RFC Report with one accepted RFC entry per scope;
4. build a Performance Claim Threshold Policy Report with one accepted
   basis-point threshold policy per scope;
5. build a Performance Acceptance Criteria Report with one accepted criteria
   entry per scope;
6. verify each report is diagnostic-only, claim-blocked, boundary-bound, and
   sets `native_performance_claim = false`;
7. verify each entry carries a `sha256:` digest from repository-controlled RFC
   files and exposes no host paths, environment data, command lines, device
   identifiers, hardware serials, generated code, backend artifacts, or raw
   timing samples.

The governance entries are metadata only. They do not load evidence, interpret
benchmark results, validate native comparisons, approve executable surfaces, or
make a performance claim.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`
- `docs/ROADMAP_STATUS.md`
- `ROADMAP.md`

## Security Boundary

The binding uses only existing workload-scope metadata and repository-controlled
RFC file digests. It must not execute generated code, execute native code, load
benchmark artifacts, parse raw benchmark output, store timing samples, inspect
host hardware, access devices, read environment variables, discover plugins,
load dynamic libraries, or invoke subprocesses.

Benchmark artifact manifests and executable backend security review remain
separate blockers. Native performance parity remains blocked.

## Consequences

- Performance Proof Readiness now has concrete governance metadata for the
  current Kernel Ingress proof slice.
- Future benchmark artifacts have a predefined claim contract, threshold policy,
  and acceptance criteria to reference.
- The readiness report still fails until benchmark artifacts and executable
  backend security review are supplied separately.