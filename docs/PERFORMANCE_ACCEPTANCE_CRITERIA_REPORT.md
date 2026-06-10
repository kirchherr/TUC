# Performance Acceptance Criteria Report

Performance Acceptance Criteria Report is a diagnostic review artifact for
future native performance proof proposals.

It records which bounded evidence contracts must be satisfied before a future
native performance claim can be accepted. It is not a benchmark report, not an
execution permission, and not a native performance proof.

The report does not run benchmarks, ingest benchmark artifacts, access devices,
inspect host hardware, execute backend artifacts, execute generated code,
discover plugins, load dynamic libraries, run subprocesses, or claim native
performance parity.

## Contract

- Boundary contract: `performance_proof_boundary.blocking.v0`
- Report schema: `schemas/performance_acceptance_criteria_report.v0.schema.json`
- Report schema version: `tuc.performance_acceptance_criteria_report.v0`
- Evidence type: `PerformanceAcceptanceCriteria`
- API: `build_performance_acceptance_criteria_report(proposal_name, criteria)`
- Dump API: `dump_performance_acceptance_criteria_report(report)`
- Example: `examples/performance_acceptance_criteria_report.py`
- Tests: `tests/test_performance_acceptance_criteria_report.py`
- Schema tests: `tests/test_performance_acceptance_criteria_schema.py`

The report is ready only when at least one criteria entry is present, every
entry is `accepted_by_maintainers`, every required evidence identifier is
supplied, and every entry has a SHA-256 digest. Even then,
`native_performance_claim` remains `false`; readiness means the acceptance
criteria are reviewable, not that the performance claim has been proven.

## Criteria Fields

Each acceptance criteria entry is bounded plain data:

- `criteria_id`: stable acceptance-criteria identifier
- `workload_scope_id`: linked workload-scope report identifier
- `threshold_policy_id`: linked threshold-policy report identifier
- `correctness_evidence_id`: correctness evidence identifier
- `benchmark_methodology_id`: benchmark methodology identifier
- `native_baseline_comparison_id`: native comparison report identifier
- `planner_overhead_report_id`: planner-overhead report identifier
- `break_even_workload_size_id`: break-even workload-size report identifier
- `leaky_abstraction_report_id`: leaky-abstraction report identifier
- `executable_security_review_id`: executable-surface security review
  identifier
- `criteria_status`: `draft`, `reviewed_not_accepted`, or
  `accepted_by_maintainers`
- `criteria_digest`: `not_supplied` or `sha256:<64 lowercase hex chars>`

IDs are safe identifiers, not paths or command lines. The report records pass
conditions by reference; it does not embed benchmark results or evidence
contents.

## Security Boundary

Performance acceptance criteria reports must not include raw benchmark output,
raw timing samples, tensors, host paths, command lines, environment variables,
hardware serials, device identifiers, generated artifacts, generated code,
plugin entrypoints, backend binaries, backend artifact contents, native source
contents, dynamic-library paths, cache paths, URLs, credentials, or execution
permission.

The report links a claim to required evidence gates; it does not load evidence,
parse benchmark output, inspect native artifacts, execute backend code, or
grant device access.

Unknown fields fail closed through the schema. Duplicate criteria identifiers,
unknown status values, path-like identifiers, missing evidence identifiers, and
invalid digests fail closed in the runtime builder.

## Still Blocked

These remain blocked after this report exists:

- claiming native performance parity
- claiming 100 percent native performance
- claiming a fixed percentage of CUDA, HIP, vendor-library, or hand-optimized
  kernel performance
- claiming near-native performance without accepted benchmark evidence
- treating acceptance criteria as benchmark results
- hiding planner overhead inside execution timing
- executing backend artifacts or device code as part of criteria review
