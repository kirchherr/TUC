# RFC 0070: Workload Scope Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Epsilon

## Summary

TUC adds a diagnostic Workload Scope Report for defining the workload families
and problem-size bounds of a future native performance proposal.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw benchmark
output ingestion, raw timing sample storage, tensor storage, plugin discovery,
dynamic libraries, subprocess execution, native code storage, or
hardware-specific HAC-IR semantics.

## Motivation

RFC 0063 and RFC 0064 require workload scope before future native performance
proposals can pass readiness. Performance claims without workload bounds are
not falsifiable and are too easy to overgeneralize.

TUC needs a data-only way to say which operation family, shape family, dtype
policy, problem-size range, and correctness reference a future performance
claim covers.

## Decision

Add [Workload Scope Report](../docs/WORKLOAD_SCOPE_REPORT.md) with:

- `schemas/workload_scope_report.v0.schema.json`
- `build_workload_scope_report(proposal_name, scopes=())`
- `dump_workload_scope_report(report)`
- report schema version `tuc.workload_scope_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report records bounded identifiers and integer problem-size bounds only.

## Scope Data

The v0 report tracks:

- `scope_id`
- `operation_family`
- `shape_profile_id`
- `dtype_policy_id`
- `problem_size_min`
- `problem_size_max`
- `correctness_reference_id`

Problem-size bounds must be explicit and finite.

## Security Boundary

The report must not include tensors, raw benchmark output, raw timing samples,
host paths, environment variables, hardware serials, device identifiers,
generated artifacts, plugin entrypoints, backend binaries, dynamic-library
paths, cache paths, native code, shell commands, or backend artifact contents.

The report must not execute backend artifacts.
The report must not load benchmark artifacts.
The report must not access devices.
The report must not add hardware-specific performance knobs to HAC-IR.

The schema is fail-closed with `additionalProperties: false` on every object.

## Evidence

The implementation adds:

- `schemas/workload_scope_report.v0.schema.json`
- `examples/workload_scope_report.py`
- `docs/WORKLOAD_SCOPE_REPORT.md`
- `tests/test_workload_scope_report.py`
- `tests/test_workload_scope_schema.py`
- report APIs in `src/tuc/proof.py`

## Consequences

- Future performance claims must be bounded before they are discussed.
- Workload scope becomes reviewable without benchmark execution.
- Raw tensor data and hardware details remain outside the compiler boundary.
- Native performance claims remain blocked until the rest of the performance
  proof evidence exists.

## Rejected Alternatives

1. Describe workload scope only in prose.

   Rejected because future performance claims need deterministic review data.

2. Store tensor shapes, sample tensors, or raw benchmark inputs directly in the
   report.

   Rejected because v0 should define scope boundaries, not benchmark payloads.

3. Treat a valid workload scope as a performance proof.

   Rejected because workload scope does not supply methodology review, native
   baseline provenance, benchmark artifacts, planner-overhead analysis,
   leaky-abstraction review, correctness goldens, or executable-backend
   security review.
