# RFC 0264: CI Replay For Admitted Slice

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `ci_replay_for_admitted_slice` as source-free, digest-only CI replay
evidence for the future first admitting `direct_source_ingestion` slice.

## Motivation

The first admitted source slice must not rely on local-only proof artifacts.
After the bounded buffer, sandbox, negative corpus, source-free diagnostics, and
plain-data output golden are defined, TUC needs a CI-bound replay artifact that
recomputes those reports, validates their contracts, and binds their digests.

This makes the future admission path reviewable without opening source
ingestion or allowing generated/compiler artifacts to appear in CI evidence.

## Decision

Create `src/tuc/frontend/admitted_slice_ci_replay.py` and
`examples/ci_replay_for_admitted_slice.py` with schema
`schemas/ci_replay_for_admitted_slice_report.v0.schema.json`, golden
`tests/golden/frontend/ci_replay_for_admitted_slice_report.json`, workflow step
in `.github/workflows/ci.yml`, and documentation at
`docs/CI_REPLAY_FOR_ADMITTED_SLICE.md`.

The report:

- replays the five current admitted-slice prerequisite artifacts by digest;
- verifies the CI workflow keeps `permissions: contents: read`;
- verifies checkout uses `persist-credentials: false`;
- verifies the CI workflow runs `examples/ci_replay_for_admitted_slice.py`;
- keeps `direct_source_ingestion = false`;
- keeps source-to-ComputeGraph, source-to-HAC-IR, and source-to-runtime-plan
  blocked;
- records that maintainer security review approval is still required.

## Security Boundary

This RFC does not authorize source ingestion implementation, default parser
admission, package import, plugin discovery, Triton JIT execution, device
access, generated artifact execution, native backend execution,
source-to-HAC-IR shortcuts, source-to-runtime-plan shortcuts, backend artifact
loading, runtime handle serialization, raw tensor values, raw source text, host
path exposure, commands, subprocesses, dynamic libraries, or network access.

The report is digest-only and source-free. The CI workflow remains read-only and
does not gain write tokens for this replay.

## Contract

- Module: `src/tuc/frontend/admitted_slice_ci_replay.py`
- Example: `examples/ci_replay_for_admitted_slice.py`
- Schema: `schemas/ci_replay_for_admitted_slice_report.v0.schema.json`
- Golden: `tests/golden/frontend/ci_replay_for_admitted_slice_report.json`
- Documentation: `docs/CI_REPLAY_FOR_ADMITTED_SLICE.md`
- Workflow: `.github/workflows/ci.yml`
- First Slice Plan: `docs/REAL_TRITON_FIRST_SLICE_PLAN.md`
- Admitting Source Ingestion RFC: `docs/ADMITTING_SOURCE_INGESTION_RFC.md`
- RFC path: `rfcs/0264-ci-replay-for-admitted-slice.md`

## Acceptance Criteria

- The replay report is schema-versioned and fail-closed.
- The replay report is source-free and digest-only.
- The replay report binds all five admitted-slice prerequisite artifacts in
  deterministic order.
- The CI workflow keeps read-only permissions and disabled checkout credential
  persistence.
- The CI workflow runs the replay example explicitly.
- The Admitting Source Ingestion RFC removes `ci_replay_for_admitted_slice`
  from remaining evidence.
- The Real Triton First Slice Plan binds this item as satisfied evidence and
  still keeps admission blocked until maintainer security review approval
  exists.
