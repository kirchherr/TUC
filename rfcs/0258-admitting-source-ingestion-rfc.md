# RFC 0258: Admitting Source Ingestion RFC Report

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `admitting_source_ingestion_rfc` as a requirements-only RFC report for the
first possible admitting `direct_source_ingestion` slice.

## Motivation

The Real Triton First Slice Plan identifies `direct_source_ingestion` as the
first candidate target surface, but it must not become admitting without an
explicit RFC boundary. This RFC report supplies that boundary as data-only
evidence while keeping implementation and admission blocked.

## Decision

Create `examples/admitting_source_ingestion_rfc.py` with schema
`schemas/admitting_source_ingestion_rfc_report.v0.schema.json`, golden
`tests/golden/frontend/admitting_source_ingestion_rfc_report.json`, and
documentation at `docs/ADMITTING_SOURCE_INGESTION_RFC.md`.

The report records:

- the target surface: `direct_source_ingestion`;
- the target slice: `bounded_source_buffer_to_source_intent_plain_data`;
- allowed inputs and outputs;
- denied compiler and execution outputs;
- remaining diagnostics, golden, replay, and maintainer review evidence;
- blocked claims and blocked execution surfaces.

## Security Boundary

This RFC does not authorize source ingestion implementation, package import,
plugin discovery, Triton JIT execution, device access, generated artifact
execution, native backend execution, source-to-HAC-IR shortcuts,
source-to-runtime-plan shortcuts, backend artifact loading, runtime handle
serialization, raw tensor values, raw source text, host path exposure,
commands, subprocesses, dynamic libraries, or network access.

The report is digest-only and source-free.

## Contract

- Example: `examples/admitting_source_ingestion_rfc.py`
- Schema: `schemas/admitting_source_ingestion_rfc_report.v0.schema.json`
- Golden: `tests/golden/frontend/admitting_source_ingestion_rfc_report.json`
- Documentation: `docs/ADMITTING_SOURCE_INGESTION_RFC.md`
- RFC path: `rfcs/0258-admitting-source-ingestion-rfc.md`
- Source Ingestion Sandbox Implementation: `docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md`
- Source Ingestion Sandbox RFC: `rfcs/0260-source-ingestion-sandbox-implementation.md`
- Parser Fuzz Negative Corpus: `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`
- Parser Fuzz Negative Corpus RFC: `rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md`

## Acceptance Criteria

- The RFC report is schema-versioned and fail-closed.
- `admitted` remains false.
- `implementation_status` remains `not_implemented`.
- `source_ingestion_admission_ready` remains false.
- Denied outputs include graph, IR, runtime-plan, generated-artifact, Python
  object, and backend-artifact surfaces.
- Tests cover drift, digest stability, source leakage, schema closure, and
  documentation links.
