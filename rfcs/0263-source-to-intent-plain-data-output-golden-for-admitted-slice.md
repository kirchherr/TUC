# RFC 0263: Source-To-Intent Plain-Data Output Golden For Admitted Slice

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `source_to_intent_plain_data_output_golden_for_admitted_slice` as a
source-free, non-admitting evidence artifact for the future first admitting
`direct_source_ingestion` slice.

## Motivation

The Real Triton First Slice Plan and Admitting Source Ingestion RFC require a
reviewable golden for the only output shape the first admitted slice may emit:
validated `source_intent.v0` plain data. Without this golden, the future source
parser would be under-specified and could accidentally drift toward metadata,
`ComputeGraph`, HAC-IR, runtime plans, or execution surfaces.

This RFC keeps the project practical while preserving the security boundary:
prove the plain-data output shape before admitting source ingestion.

## Decision

Create `src/tuc/frontend/source_to_intent_admitted_slice_golden.py` and
`examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py` with
schema
`schemas/source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0.schema.json`,
report golden
`tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_report.json`,
Source Intent golden
`tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_source_intent.json`,
and documentation at
`docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md`.

The report:

- binds Source-Free Diagnostics Admission Tests by digest;
- covers `elementwise`, `matmul`, `reduction`, and `softmax` across two cases;
- validates each plain-data output through Source Intent Intake;
- records only digests and safe metadata in the public report;
- keeps `direct_source_ingestion = false`;
- keeps source-to-ComputeGraph, source-to-HAC-IR, and source-to-runtime-plan
  blocked.

## Security Boundary

This RFC does not authorize source ingestion implementation, default parser
admission, package import, plugin discovery, Triton JIT execution, device access,
generated artifact execution, native backend execution, source-to-HAC-IR
shortcuts, source-to-runtime-plan shortcuts, backend artifact loading, runtime
handle serialization, raw tensor values, raw source text, host path exposure,
commands, subprocesses, dynamic libraries, or network access.

The report is digest-only and source-free. The separate Source Intent golden is
reviewable plain data only and remains disconnected from compiler execution.

## Contract

- Module: `src/tuc/frontend/source_to_intent_admitted_slice_golden.py`
- Example: `examples/source_to_intent_plain_data_output_golden_for_admitted_slice.py`
- Schema: `schemas/source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0.schema.json`
- Report Golden: `tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_report.json`
- Source Intent Golden: `tests/golden/frontend/source_to_intent_plain_data_output_golden_for_admitted_slice_source_intent.json`
- Documentation: `docs/SOURCE_TO_INTENT_PLAIN_DATA_OUTPUT_GOLDEN_FOR_ADMITTED_SLICE.md`
- First Slice Plan: `docs/REAL_TRITON_FIRST_SLICE_PLAN.md`
- Admitting Source Ingestion RFC: `docs/ADMITTING_SOURCE_INGESTION_RFC.md`
- CI Replay For Admitted Slice: `docs/CI_REPLAY_FOR_ADMITTED_SLICE.md`
- CI Replay For Admitted Slice Example: `examples/ci_replay_for_admitted_slice.py`
- CI Replay For Admitted Slice Schema: `schemas/ci_replay_for_admitted_slice_report.v0.schema.json`
- CI Replay For Admitted Slice Golden: `tests/golden/frontend/ci_replay_for_admitted_slice_report.json`
- CI Replay For Admitted Slice Module: `src/tuc/frontend/admitted_slice_ci_replay.py`
- CI Replay For Admitted Slice RFC: `rfcs/0264-ci-replay-for-admitted-slice.md`
- RFC path: `rfcs/0263-source-to-intent-plain-data-output-golden-for-admitted-slice.md`

## Acceptance Criteria

- The report is schema-versioned and fail-closed.
- The report is source-free and digest-only.
- The separate Source Intent golden validates through Source Intent Intake.
- MVP operation-family coverage is complete for the admitted-slice candidate.
- The Admitting Source Ingestion RFC removes this item from remaining evidence.
- The Real Triton First Slice Plan binds this item as satisfied evidence and
  still keeps admission blocked until CI replay and maintainer security review
  approval exist.
