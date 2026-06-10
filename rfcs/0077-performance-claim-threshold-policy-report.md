# RFC 0077: Performance Claim Threshold Policy Report

- Status: Accepted
- Date: 2026-06-10
- Area: Performance proof governance

## Summary

Add a bounded diagnostic report for native performance claim threshold policies.

The report records the threshold policy that a future performance claim must use
before benchmark artifacts can be interpreted as proof evidence.

It does not run benchmarks, load artifacts, access devices, execute backend
code, or prove native performance.

## Motivation

TUC must reject broad claims such as "near native" unless the threshold is
defined before measurements are evaluated.

The Performance Proof RFC Report can identify a threshold-policy ID, but that
ID needs a bounded artifact of its own. Otherwise a reviewer can see that a
policy was named, but cannot tell whether the policy was accepted, digest
pinned, scoped to a workload, tied to a metric, or expressed in a stable unit.

## Decision

Introduce:

- `PerformanceClaimThresholdPolicy`
- `PerformanceClaimThresholdPolicyReport`
- `build_performance_claim_threshold_policy_report(proposal_name, policies)`
- `dump_performance_claim_threshold_policy_report(report)`
- `performance_claim_threshold_policy_report_to_dict(report)`
- report schema version `tuc.performance_claim_threshold_policy_report.v0`
- schema file
  `schemas/performance_claim_threshold_policy_report.v0.schema.json`

The report remains:

- `artifact_status = "diagnostic_only"`
- `performance_claim_status = "blocked"`
- `native_performance_claim = false`
- `claim_boundary = "performance_proof_boundary.blocking.v0"`

The performance proof readiness evidence list also gains
`performance_claim_threshold_policy`.

## Threshold Kinds

v0 supports two policy kinds:

- `ratio_to_native_at_least`
- `overhead_over_native_at_most`

Threshold values are stored as basis points, not floats. This keeps the policy
deterministic and avoids ambiguous percentage formatting.

## Ready Meaning

`performance_claim_threshold_policy_ready` means only that threshold-policy
metadata is review-ready. It requires:

- at least one policy entry
- every policy status is `accepted_by_maintainers`
- every policy has a SHA-256 digest

It does not mean native performance has been proven.

## Security Boundary

The report accepts only bounded identifiers, enum status values, enum threshold
kinds, integer basis points, and digest metadata.

It must not include raw benchmark output, raw timing samples, host paths,
command lines, environment variables, device identifiers, generated code,
backend artifacts, native source, plugin entrypoints, dynamic-library paths,
cache paths, credentials, or execution permission.

Unknown fields fail closed in the schema. Duplicate policy identifiers,
unknown threshold kinds, unknown status values, path-like identifiers, invalid
basis-point values, and invalid digests fail closed in runtime validation.

## Alternatives Considered

### Keep Thresholds Only In RFC Text

Rejected because native performance claims need machine-checkable review
metadata and deterministic schema validation.

### Put Thresholds In Benchmark Reports

Rejected because benchmark reports must remain evidence artifacts. They should
not define the claim they are supposed to evaluate.

### Use Floating-Point Percentages

Rejected because basis points are deterministic, easy to diff, and avoid
formatting ambiguity.

## References

- [Performance Proof Boundary](../docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance Proof RFC Report](../docs/PERFORMANCE_PROOF_RFC_REPORT.md)
- [Performance Claim Threshold Policy Report](../docs/PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md)
- [Performance Proof Readiness Report](../docs/PERFORMANCE_PROOF_READINESS.md)
- `schemas/performance_claim_threshold_policy_report.v0.schema.json`
