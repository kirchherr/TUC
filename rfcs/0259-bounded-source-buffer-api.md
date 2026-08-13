# RFC 0259: Bounded Source Buffer API

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `bounded_source_buffer_api` as the first concrete source-ingestion boundary
API for a future admitting `direct_source_ingestion` slice.

## Motivation

The Admitting Source Ingestion RFC requires a bounded source-buffer API before
any source-ingestion slice can become admitting. TUC now wraps this boundary in
the Source Ingestion Sandbox Implementation; fuzzing, diagnostics admission
tests, Source Intent goldens, replay, and maintainer approval remain separate
requirements.

## Decision

Create `src/tuc/frontend/bounded_source_buffer.py` and
`examples/bounded_source_buffer_api.py`.

The API validates source text as untrusted data, enforces byte, line, AST-node,
AST-depth, shape-profile-entry, rank, and dimension limits, and returns only a
metadata record with digests and counts.

The report records:

- accepted metadata-only records;
- source-free rejection cases;
- enforced budgets;
- required controls;
- blocked compiler outputs;
- blocked execution surfaces;
- admission remains false for source-to-graph, source-to-HAC-IR, and
  source-to-runtime-plan paths.

## Security Boundary

This RFC does not authorize source-to-Intent output, source-to-ComputeGraph,
source-to-HAC-IR, source-to-runtime-plan, package import, plugin discovery,
Triton JIT execution, decorator evaluation, generated artifact execution,
device access, native backend execution, subprocesses, dynamic libraries,
network access, raw source serialization, host path exposure, command exposure,
runtime handle serialization, or tensor-value serialization.

The API may parse Python syntax as data to measure AST budgets. It must not
evaluate the AST.

## Contract

- API module: `src/tuc/frontend/bounded_source_buffer.py`
- Example: `examples/bounded_source_buffer_api.py`
- Schema: `schemas/bounded_source_buffer_api_report.v0.schema.json`
- Golden: `tests/golden/frontend/bounded_source_buffer_api_report.json`
- Documentation: `docs/BOUNDED_SOURCE_BUFFER_API.md`
- RFC path: `rfcs/0259-bounded-source-buffer-api.md`
- Source Ingestion Sandbox Implementation: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`
- Source Ingestion Sandbox RFC: `rfcs/0260-source-ingestion-sandbox-implementation.md`

## Acceptance Criteria

- The API is execution-free and source-free at the report boundary.
- The report is schema-versioned and fail-closed.
- Accepted records contain digests and bounded metadata only.
- Rejected cases expose source-free reason codes only.
- `direct_source_ingestion`, `source_to_compute_graph`, `source_to_hac_ir`, and
  `source_to_runtime_plan` remain false.
- Real Triton First Slice Plan binds the report by digest while remaining
  non-admitting.
