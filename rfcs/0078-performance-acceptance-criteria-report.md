# RFC 0078: Performance Acceptance Criteria Report

- Status: Accepted
- Date: 2026-06-10
- Area: Performance proof governance

## Summary

Add a bounded diagnostic report for native performance acceptance criteria.

The report records the evidence gates that must be satisfied before a future
native performance claim can be accepted.

It does not run benchmarks, load artifacts, access devices, execute backend
code, or prove native performance.

## Motivation

TUC now has a performance-proof RFC report and a threshold-policy report. The
remaining governance gap is the pass/fail contract itself:

- Which correctness evidence is required?
- Which benchmark methodology is valid?
- Which native comparison evidence is valid?
- Is planner overhead separated?
- Is break-even workload-size evidence present?
- Has HAC-IR leakage been reviewed?
- Has executable backend security been reviewed?

Without bounded acceptance criteria, a later benchmark artifact could appear to
support a claim without a versioned definition of what "accepted" means.

## Decision

Introduce:

- `PerformanceAcceptanceCriteria`
- `PerformanceAcceptanceCriteriaReport`
- `build_performance_acceptance_criteria_report(proposal_name, criteria)`
- `dump_performance_acceptance_criteria_report(report)`
- `performance_acceptance_criteria_report_to_dict(report)`
- report schema version `tuc.performance_acceptance_criteria_report.v0`
- schema file `schemas/performance_acceptance_criteria_report.v0.schema.json`

The report remains:

- `artifact_status = "diagnostic_only"`
- `performance_claim_status = "blocked"`
- `native_performance_claim = false`
- `claim_boundary = "performance_proof_boundary.blocking.v0"`

The performance proof readiness evidence list also gains
`performance_acceptance_criteria`.

## Ready Meaning

`performance_acceptance_criteria_ready` means only that acceptance-criteria
metadata is review-ready. It requires:

- at least one criteria entry
- every criteria status is `accepted_by_maintainers`
- every required evidence identifier is supplied
- every criteria entry has a SHA-256 digest

It does not mean native performance has been proven.

## Security Boundary

The report accepts only bounded identifiers, enum status values, and digest
metadata.

It must not include raw benchmark output, raw timing samples, host paths,
command lines, environment variables, device identifiers, generated code,
backend artifacts, native source, plugin entrypoints, dynamic-library paths,
cache paths, credentials, or execution permission.

Unknown fields fail closed in the schema. Duplicate criteria identifiers,
unknown status values, path-like identifiers, missing evidence identifiers, and
invalid digests fail closed in runtime validation.

## Alternatives Considered

### Keep Acceptance Criteria Only In RFC Text

Rejected because reviewers need machine-checkable metadata that can be compared
against later evidence manifests.

### Put Acceptance Criteria Inside Benchmark Reports

Rejected because benchmark reports must remain evidence artifacts. They should
not define the pass/fail contract they are evaluated against.

### Treat Threshold Policy As Full Acceptance Criteria

Rejected because a threshold is only one condition. Native performance claims
also require correctness, methodology, native comparison, planner-overhead,
break-even, leaky-abstraction, and executable-surface security evidence.

## References

- [Performance Proof Boundary](../docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance Proof RFC Report](../docs/PERFORMANCE_PROOF_RFC_REPORT.md)
- [Performance Claim Threshold Policy Report](../docs/PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md)
- [Performance Acceptance Criteria Report](../docs/PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT.md)
- [Performance Proof Readiness Report](../docs/PERFORMANCE_PROOF_READINESS.md)
- `schemas/performance_acceptance_criteria_report.v0.schema.json`
