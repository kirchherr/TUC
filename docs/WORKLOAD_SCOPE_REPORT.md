# Workload Scope Report

Workload Scope Report is a diagnostic artifact for defining the workload
families and problem-size bounds of a future performance claim.

It does not run benchmarks, load benchmark artifacts, execute backend artifacts,
access devices, inspect host hardware, discover plugins, load dynamic
libraries, run subprocesses, store tensors, store raw benchmark output, store
raw timing samples, or claim native performance parity.

## Contract

- Report schema: `schemas/workload_scope_report.v0.schema.json`
- Report schema version: `tuc.workload_scope_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_workload_scope_report(proposal_name, scopes=())`
- Dump API: `dump_workload_scope_report(report)`
- Example: `examples/workload_scope_report.py`
- Tests: `tests/test_workload_scope_report.py`
- Schema tests: `tests/test_workload_scope_schema.py`

The report is not a native performance proof. It defines the scope that a
future performance proof proposal must stay within.

## Scope Fields

Each workload scope entry is data-only and bounded:

- `scope_id`: stable identifier for the scope
- `operation_family`: `matmul`, `elementwise`, `reduction`, or `softmax`
- `shape_profile_id`: stable shape-family identifier, not tensor data
- `dtype_policy_id`: stable dtype policy identifier
- `problem_size_min`: smallest included problem size
- `problem_size_max`: largest included problem size
- `correctness_reference_id`: stable reference-semantics identifier

The report intentionally accepts identifiers and integer bounds, not tensors,
host paths, command lines, environment variables, raw benchmark output, backend
binaries, generated code, or device details.

## Security Boundary

The report must not include tensors, raw benchmark output, raw timing samples,
host paths, environment variables, hardware serials, device identifiers,
generated artifacts, plugin entrypoints, backend binaries, dynamic-library
paths, cache paths, native code, shell commands, or backend artifact contents.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not execute backend code and does not load benchmark artifacts.
It is a workload boundary review surface only.

## Current Status

The current report can identify bounded workload scopes and keep performance
claims constrained to explicit operation families, shape profiles, dtype
policies, problem-size bounds, and correctness references.

`workload_scope_ready` means only that at least one bounded workload scope is
present. Native performance claims remain blocked in v0.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- benchmark methodology acceptance
- benchmark artifact acceptance as proof
- raw benchmark result ingestion
- native benchmark execution
- executable backend benchmarking without a dedicated security RFC
- device access, generated-artifact execution, dynamic-library loading, or
  subprocess execution as part of proof review
