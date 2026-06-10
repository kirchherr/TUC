# Planner Overhead Report

Planner Overhead Report is a diagnostic artifact for measuring compiler and
runtime-planning phases separately from execution time.

It does not execute backend artifacts, run generated code, access devices,
discover plugins, load dynamic libraries, run subprocesses, store raw timing
samples, or claim native performance parity.

## Contract

- Report schema: `schemas/planner_overhead_report.v0.schema.json`
- Report schema version: `tuc.planner_overhead_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Execution time status: `not_measured`
- Break-even status: `not_established`
- API: `measure_pipeline_planner_overhead(graph, backend_capabilities)`
- Dump API: `dump_planner_overhead_report(report)`
- Example: `examples/planner_overhead_report.py`
- Tests: `tests/test_planner_overhead_report.py`
- Schema tests: `tests/test_planner_overhead_report_schema.py`

The report is not a native performance proof. It is a phase-separation
diagnostic that makes hidden planner overhead visible before TUC accepts future
performance claims.

## Phase Boundary

The v0 report uses this ordered phase contract:

- `graph_construction`
- `frontend_intake`
- `tlir_module_construction`
- `tlir_to_hac_lowering`
- `runtime_planning`
- `backend_selection_report`
- `hs_ir_generation`
- `execution`

Current `measure_pipeline_planner_overhead` starts from an already constructed
`ComputeGraph`, so `graph_construction` and `frontend_intake` are explicitly
reported as `not_measured`.

Execution is also explicitly reported as `not_measured`. Planner overhead must
not be hidden inside execution time.

Break-even workload-size evidence is tracked separately by
[Break-Even Workload Size Report](BREAK_EVEN_WORKLOAD_SIZE_REPORT.md) and
`schemas/break_even_workload_size_report.v0.schema.json`. The planner-overhead
report must not embed raw timing samples or unscoped break-even claims.

## Security Boundary

The report must not include raw timing samples, host paths, hardware serials,
device identifiers, plugin entrypoints, backend artifacts, generated code,
dynamic-library paths, cache paths, environment variables, or native performance
parity fields.

The schema is fail-closed with `additionalProperties: false` on every object.

The report stores only aggregate duration values for compiler/planner phases
and explicit status markers for unmeasured phases.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- break-even workload-size claims
- planner-benefit claims for small workloads
- hiding planner overhead inside execution timing
- treating diagnostic compiler-phase timings as benchmark artifacts
- using planner timings as HAC-IR semantics
- executable backend benchmarking without a dedicated security RFC
