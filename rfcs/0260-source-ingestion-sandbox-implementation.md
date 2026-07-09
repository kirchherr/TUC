# RFC 0260: Source Ingestion Sandbox Implementation

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `source_ingestion_sandbox_implementation` as an execution-free,
non-admitting sandbox wrapper around the Bounded Source Buffer API.

## Motivation

The Real Triton First Slice Plan needs a concrete source-ingestion boundary
before any admitting source-to-Intent slice can be considered. The first
implementation must prove that source text can be handled as untrusted bounded
data without opening imports, decorators, JIT execution, generated artifacts,
backend artifacts, direct graph construction, or runtime planning.

## Decision

Create `src/tuc/frontend/source_ingestion_sandbox.py` and
`examples/source_ingestion_sandbox_implementation.py` with schema
`schemas/source_ingestion_sandbox_implementation_report.v0.schema.json`, golden
`tests/golden/frontend/source_ingestion_sandbox_implementation_report.json`, and
documentation at `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`.

The sandbox:

- wraps `bound_source_buffer`;
- returns accepted metadata-only results with bounded source-buffer record
  digests;
- returns rejected results with source-free reason codes;
- binds the Bounded Source Buffer API report by digest;
- keeps `direct_source_ingestion = false`;
- keeps `source_to_intent_plain_data = false`;
- keeps source-to-ComputeGraph, source-to-HAC-IR, and source-to-runtime-plan
  paths blocked.

## Security Boundary

This RFC does not authorize source-to-Intent output, source-to-ComputeGraph,
source-to-HAC-IR, source-to-runtime-plan, package import, plugin discovery,
Triton JIT execution, decorator evaluation, device access, generated artifact
execution, native backend execution, dynamic library loading, subprocesses,
network access, runtime handle serialization, raw tensor values, host path
exposure, commands, or raw source text serialization.

The public report is metadata-only and source-free.

## Contract

- API module: `src/tuc/frontend/source_ingestion_sandbox.py`
- Example: `examples/source_ingestion_sandbox_implementation.py`
- Schema: `schemas/source_ingestion_sandbox_implementation_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_sandbox_implementation_report.json`
- Documentation: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`
- RFC path: `rfcs/0260-source-ingestion-sandbox-implementation.md`

## Acceptance Criteria

- The sandbox report is schema-versioned and fail-closed.
- The sandbox binds Bounded Source Buffer API evidence by digest.
- Accepted sandbox results are metadata-only and source-free.
- Rejected sandbox results return only source-free reason codes.
- `direct_source_ingestion`, Source Intent output, graph output, HAC-IR output,
  and runtime-plan output remain false.
- Tests cover API behavior, drift, digest stability, source leakage, schema
  closure, and documentation links.