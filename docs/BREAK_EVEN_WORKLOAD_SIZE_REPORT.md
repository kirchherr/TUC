# Break-Even Workload Size Report

Break-Even Workload Size Report is a diagnostic artifact for reviewing future
claims about the problem size where compiler and runtime-planning overhead is
amortized by execution.

It does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, inspect host hardware, access devices, execute
backend artifacts, run subprocesses, or claim native performance parity.

## Contract

- Report schema: `schemas/break_even_workload_size_report.v0.schema.json`
- Report schema version: `tuc.break_even_workload_size_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_break_even_workload_size_report(proposal_name, workloads=())`
- Dump API: `dump_break_even_workload_size_report(report)`
- Example: `examples/break_even_workload_size_report.py`
- Tests: `tests/test_break_even_workload_size_report.py`
- Schema tests: `tests/test_break_even_workload_size_schema.py`

The report is not a native performance proof. It records explicit break-even
metadata that future benchmark artifacts can reference.

## Workload Fields

Each break-even workload entry is data-only and bounded:

- `break_even_id`: stable break-even evidence identifier
- `workload_scope_id`: workload scope being evaluated
- `planner_overhead_report_id`: planner-overhead report identifier
- `execution_metric_id`: execution metric identifier
- `amortization_policy_id`: policy for amortizing planning cost
- `break_even_status`: `not_established`, `estimated_not_validated`, or
  `validated_by_ci`
- `break_even_problem_size`: positive bounded integer or `null`
- `evidence_digest`: `not_supplied` or a `sha256:` digest

`not_established` entries must not include a problem size. Estimated or
validated entries must include a bounded problem size.

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, secrets, hardware serials, device identifiers,
generated artifacts, plugin entrypoints, backend binaries, dynamic-library
paths, cache paths, native code, shell commands, package-manager output, or
benchmark artifact contents.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not validate benchmark results or compute a break-even point.
It is a bounded review surface for already established break-even evidence.

`break_even_workload_size_ready` means only that at least one bounded workload
entry is present, every entry is `validated_by_ci`, every entry has a problem
size, and every entry supplies a digest. Native performance claims remain
blocked in v0.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- hidden planner overhead inside execution timing
- benchmark artifact loading during proof review
- raw timing-sample ingestion
- planner-benefit claims for workloads outside the scoped evidence
- executable backend benchmarking without a dedicated security RFC
