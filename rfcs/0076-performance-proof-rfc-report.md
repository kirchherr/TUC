# RFC 0076: Performance Proof RFC Report

- Status: Accepted
- Date: 2026-06-10
- Area: Performance proof governance

## Summary

Add a bounded diagnostic report for future performance-proof RFCs.

The report records whether a native performance claim proposal has a scoped RFC,
workload scope, threshold policy, acceptance criteria, evidence bundle, security
review, maintainer acceptance status, and digest.

It does not run benchmarks, load artifacts, access devices, execute backend
code, or prove native performance.

## Motivation

TUC must avoid treating benchmark output or informal "near native" language as
proof. Before native performance evidence can be evaluated, the proposal itself
must be reviewable:

- What workload is being claimed?
- What threshold is being claimed?
- Which bounded threshold-policy report defines that threshold?
- What evidence bundle is allowed to support the claim?
- What acceptance criteria apply?
- Which executable surfaces were security-reviewed?
- Did maintainers accept this exact proposal version?

Without a bounded RFC report, the performance proof boundary has a process gap:
evidence could exist without an accepted claim contract.

## Decision

Introduce:

- `PerformanceProofRFC`
- `PerformanceProofRFCReport`
- `build_performance_proof_rfc_report(proposal_name, rfcs)`
- `dump_performance_proof_rfc_report(report)`
- `performance_proof_rfc_report_to_dict(report)`
- report schema version `tuc.performance_proof_rfc_report.v0`
- schema file `schemas/performance_proof_rfc_report.v0.schema.json`

The report remains:

- `artifact_status = "diagnostic_only"`
- `performance_claim_status = "blocked"`
- `native_performance_claim = false`
- `claim_boundary = "performance_proof_boundary.blocking.v0"`

## Ready Meaning

`performance_proof_rfc_ready` means only that the RFC metadata is review-ready.
It requires:

- at least one RFC entry
- every RFC status is `accepted_by_maintainers`
- claim threshold policy, acceptance criteria, evidence bundle, and security
  review identifiers are supplied
- every RFC has a SHA-256 digest

It does not mean native performance has been proven.

## Security Boundary

The report accepts only bounded identifiers, enum status values, and digest
metadata.

It must not include raw benchmark output, raw timing samples, host paths,
command lines, environment variables, device identifiers, generated code,
backend artifacts, native source, plugin entrypoints, dynamic-library paths,
cache paths, credentials, or execution permission.

Unknown fields fail closed in the schema. Duplicate RFC identifiers, unknown
status values, path-like identifiers, and invalid digests fail closed in
runtime validation.

## Alternatives Considered

### Use Only Performance Proof Readiness

Rejected because readiness only tracks required evidence IDs. It does not
record whether the actual performance claim proposal is accepted, scoped,
thresholded, digest-pinned, or linked to security review.

### Put RFC Text Inside Benchmark Artifacts

Rejected because benchmark artifacts must remain measurement evidence, not a
place for broad claim governance or executable-surface permission.

### Accept Informal Maintainer Comments

Rejected because the native performance proof path must be repeatable and
auditable across forks, releases, and future hardware classes.

## References

- [Performance Proof Boundary](../docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance Proof Readiness Report](../docs/PERFORMANCE_PROOF_READINESS.md)
- [Performance Proof RFC Report](../docs/PERFORMANCE_PROOF_RFC_REPORT.md)
- [Performance Claim Threshold Policy Report](../docs/PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md)
- `schemas/performance_proof_rfc_report.v0.schema.json`
