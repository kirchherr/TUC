# RFC 0257: Real Triton First Slice Plan

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `real_triton_first_slice_plan` as a data-only planning artifact for the
first possible Real Triton admitting slice.

## Motivation

TUC already has Real Triton readiness, admission, and full surface-gate
completion evidence. That proves the perimeter is complete, but it does not
make the next implementation step obvious.

The first-slice plan keeps admission blocked while showing the concrete path
toward a future `direct_source_ingestion` admitting slice.

## Decision

Create `examples/real_triton_first_slice_plan.py` with schema
`schemas/real_triton_first_slice_plan_report.v0.schema.json`, golden
`tests/golden/frontend/real_triton_first_slice_plan_report.json`, and
documentation at `docs/REAL_TRITON_FIRST_SLICE_PLAN.md`.

The plan binds:

- Real Triton Integration Admission Gate;
- Real Triton Surface Gate Completion;
- Source Ingestion Quarantine Gate;
- Admitting Source Ingestion RFC;
- Bounded Source Buffer API;
- Source Ingestion Sandbox Implementation;
- Parser Fuzz Negative Corpus For Admitting Slice;
- Source-Free Diagnostics Admission Tests;
- Source-To-Intent Plain-Data Output Golden For Admitted Slice;
- CI Replay For Admitted Slice;
- Source Ingestion Approval Criteria;
- Source-To-Intent Research Source Runtime Smoke;
- Source-To-Intent Research Kernel Ingress Proof Bundle.

The report keeps `admitted = false`, `source_ingestion_admission_ready = false`,
and records the missing admission evidence before `direct_source_ingestion` can
be considered for an admitting implementation. Downstream maintainer review,
approval-artifact, and admission-gate reports bind this plan by digest; this
plan does not bind them back, keeping the evidence graph acyclic.

## Contract

- Example: `examples/real_triton_first_slice_plan.py`
- Schema: `schemas/real_triton_first_slice_plan_report.v0.schema.json`
- Golden: `tests/golden/frontend/real_triton_first_slice_plan_report.json`
- Documentation: `docs/REAL_TRITON_FIRST_SLICE_PLAN.md`
- Bounded Source Buffer API: `docs/BOUNDED_SOURCE_BUFFER_API.md`
- Source Ingestion Sandbox Implementation: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`
- Source Ingestion Sandbox RFC: `rfcs/0260-source-ingestion-sandbox-implementation.md`
- Parser Fuzz Negative Corpus: `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`
- Parser Fuzz Negative Corpus RFC: `rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md`
- Source-Free Diagnostics Admission Tests: `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`
- Source-Free Diagnostics Admission Tests RFC: `rfcs/0262-source-free-diagnostics-admission-tests.md`
- Source-To-Intent Plain-Data Output Golden: `docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md`
- Source-To-Intent Plain-Data Output Golden RFC: `rfcs/0263-source-to-intent-plain-data-output-golden-for-admitted-slice.md`
- CI Replay For Admitted Slice: `docs/CI_REPLAY_FOR_ADMITTED_SLICE.md`
- CI Replay For Admitted Slice Module: `src/tuc/frontend/admitted_slice_ci_replay.py`
- CI Replay For Admitted Slice Example: `examples/ci_replay_for_admitted_slice.py`
- CI Replay For Admitted Slice Schema: `schemas/ci_replay_for_admitted_slice_report.v0.schema.json`
- CI Replay For Admitted Slice Golden: `tests/golden/frontend/ci_replay_for_admitted_slice_report.json`
- CI Replay For Admitted Slice RFC: `rfcs/0264-ci-replay-for-admitted-slice.md`
- Source Ingestion Approval Criteria: `docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md`
- Source Ingestion Approval Criteria Example: `examples/source_ingestion_approval_criteria.py`
- Source Ingestion Approval Criteria Schema: `schemas/source_ingestion_approval_criteria_report.v0.schema.json`
- Source Ingestion Approval Criteria Golden: `tests/golden/frontend/source_ingestion_approval_criteria_report.json`
- Source Ingestion Approval Criteria RFC: `rfcs/0268-source-ingestion-approval-criteria.md`
- RFC path: `rfcs/0257-real-triton-first-slice-plan.md`

## Security Boundary

This RFC does not authorize direct source ingestion, package import, plugin
discovery, Triton JIT execution, device access, generated artifact execution,
native backend execution, source-to-HAC-IR shortcuts, source-to-runtime-plan
shortcuts, backend artifact loading, runtime handle serialization, raw tensor
values, raw source text, host path exposure, commands, subprocesses, dynamic
libraries, or network access.

The plan report is digest-only and source-free.

## Acceptance Criteria

- The plan report is schema-versioned and fail-closed.
- The plan binds exactly thirteen prerequisite evidence artifacts by digest.
- `direct_source_ingestion` is only a candidate target surface, not admitted.
- All other Real Triton surfaces remain blocked.
- Maintainer security review remains explicit and machine-reviewable as the final admission evidence.
- Tests cover drift, evidence ordering, source leakage, schema closure, and
  documentation links.
