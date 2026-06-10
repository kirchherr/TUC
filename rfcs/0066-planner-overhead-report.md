# RFC 0066: Planner Overhead Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Delta / Epsilon

## Summary

TUC adds a diagnostic Planner Overhead Report for separating compiler and
runtime-planning time from execution time.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw timing
sample storage, plugin discovery, dynamic libraries, subprocess execution,
break-even claims, or hardware-specific HAC-IR semantics.

## Motivation

RFC 0063 identifies runtime planner overhead as one of the main limits of the
Universal Compute proof. If planning time is hidden inside execution time, TUC
could appear faster or more useful than it is.

RFC 0064 requires `planner_overhead_report` evidence before native performance
proposals can pass readiness. This RFC supplies the first narrow diagnostic
report for compiler/planner phase separation.

## Decision

Add [Planner Overhead Report](../docs/PLANNER_OVERHEAD_REPORT.md) with:

- `schemas/planner_overhead_report.v0.schema.json`
- `measure_pipeline_planner_overhead(graph, backend_capabilities)`
- `dump_planner_overhead_report(report)`
- report schema version `tuc.planner_overhead_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- execution status `not_measured`
- break-even status `not_established`

The v0 report measures compile/planner phases available inside the current
`ComputeGraph` pipeline and explicitly marks graph construction, frontend
intake, execution time, and break-even workload size as not yet established.

## Security Boundary

The report must not include raw timing samples, host paths, hardware serials,
device identifiers, plugin entrypoints, backend artifacts, generated code,
dynamic-library paths, cache paths, environment variables, or native
performance parity fields.

The report must not execute backend artifacts.
The report must not hide planner overhead inside execution time.

The schema is fail-closed with `additionalProperties: false` on every object.

## Evidence

The implementation adds:

- `src/tuc/benchmarks/planner_overhead.py`
- `schemas/planner_overhead_report.v0.schema.json`
- `examples/planner_overhead_report.py`
- `docs/PLANNER_OVERHEAD_REPORT.md`
- `tests/test_planner_overhead_report.py`
- `tests/test_planner_overhead_report_schema.py`

## Consequences

- Planner overhead becomes an explicit diagnostic artifact.
- Execution time remains separate and currently unmeasured.
- Break-even workload-size claims remain blocked.
- Future native performance proposals can point to phase-separation evidence
  without treating it as performance parity evidence.

## Rejected Alternatives

1. Put planner timings into the baseline benchmark report.

   Rejected because benchmark execution and compiler planning are different
   evidence classes.

2. Hide planning time inside execution time.

   Rejected because this is one of the explicit failure modes of the proof.

3. Claim break-even workload size from the first diagnostic report.

   Rejected because break-even evidence requires execution timings, workload
   families, native baseline provenance, and benchmark artifact policy.
