# Performance Claim Threshold Policy Report

Performance Claim Threshold Policy Report is a diagnostic review artifact for
future native performance proof proposals.

It records the predefined threshold policy that a future performance claim must
use before benchmark artifacts can be interpreted as evidence. It is not a
benchmark report, not an execution permission, and not a native performance
proof.

The report does not run benchmarks, ingest benchmark artifacts, access devices,
inspect host hardware, execute backend artifacts, execute generated code,
discover plugins, load dynamic libraries, run subprocesses, or claim native
performance parity.

## Contract

- Boundary contract: `performance_proof_boundary.blocking.v0`
- Report schema:
  `schemas/performance_claim_threshold_policy_report.v0.schema.json`
- Report schema version: `tuc.performance_claim_threshold_policy_report.v0`
- Evidence type: `PerformanceClaimThresholdPolicy`
- API:
  `build_performance_claim_threshold_policy_report(proposal_name, policies)`
- Dump API: `dump_performance_claim_threshold_policy_report(report)`
- Example: `examples/performance_claim_threshold_policy_report.py`
- Tests: `tests/test_performance_claim_threshold_policy_report.py`
- Schema tests: `tests/test_performance_claim_threshold_policy_schema.py`

The report is ready only when at least one policy is present, every policy is
`accepted_by_maintainers`, and every policy has a SHA-256 digest. Even then,
`native_performance_claim` remains `false`; readiness means the threshold
policy is reviewable, not that the performance claim has been proven.

## Policy Fields

Each threshold policy entry is bounded plain data:

- `policy_id`: stable threshold-policy identifier
- `workload_scope_id`: linked workload-scope report identifier
- `comparison_metric_id`: metric identifier used by later comparison evidence
- `summary_policy_id`: summary policy identifier
- `threshold_kind`: `ratio_to_native_at_least` or
  `overhead_over_native_at_most`
- `threshold_basis_points`: integer threshold in basis points
- `policy_status`: `draft`, `reviewed_not_accepted`, or
  `accepted_by_maintainers`
- `policy_digest`: `not_supplied` or `sha256:<64 lowercase hex chars>`

Examples:

- `ratio_to_native_at_least` with `9500` means the later evidence must meet at
  least 95.00 percent of the scoped native baseline for the named metric.
- `overhead_over_native_at_most` with `500` means the later evidence must show
  no more than 5.00 percent overhead for the named metric.

IDs are safe identifiers, not paths or command lines. Basis-point thresholds
are claim policy, not measured results.

## Security Boundary

Performance claim threshold policy reports must not include raw benchmark
output, raw timing samples, tensors, host paths, command lines, environment
variables, hardware serials, device identifiers, generated artifacts, generated
code, plugin entrypoints, backend binaries, backend artifact contents, native
source contents, dynamic-library paths, cache paths, URLs, credentials, or
execution permission.

The report links a claim to a predefined threshold policy; it does not load
evidence, parse benchmark output, inspect native artifacts, execute backend
code, or grant device access.

Unknown fields fail closed through the schema. Duplicate policy identifiers,
unknown threshold kinds, unknown status values, path-like identifiers, invalid
basis-point values, and invalid digests fail closed in the runtime builder.

## Still Blocked

These remain blocked after this report exists:

- claiming native performance parity
- claiming 100 percent native performance
- claiming a fixed percentage of CUDA, HIP, vendor-library, or hand-optimized
  kernel performance
- claiming near-native performance without accepted benchmark evidence
- treating the threshold policy as a benchmark result
- hiding planner overhead inside execution timing
- executing backend artifacts or device code as part of policy review
