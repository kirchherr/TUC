# RFC 0261: Parser Fuzz Negative Corpus For Admitting Slice

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `parser_fuzz_negative_corpus_for_admitting_slice` as a source-free,
data-only negative/fuzz corpus for the future admitting source-to-Intent slice.

## Motivation

The Source Ingestion Sandbox proves TUC can handle source text as bounded,
untrusted data, but a future admitting parser still needs explicit negative
coverage before it may produce Source Intent plain data. The next safe step is
to define the rejection corpus first, while parser output remains closed.

## Decision

Create `src/tuc/frontend/parser_fuzz_negative_corpus.py` and
`examples/parser_fuzz_negative_corpus_for_admitting_slice.py` with schema
`schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json`,
golden `tests/golden/frontend/parser_fuzz_negative_corpus_for_admitting_slice_report.json`,
and documentation at `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`.

The corpus records deterministic private seeds by digest only. It covers:

- malformed syntax;
- resource-budget overflow;
- invalid shape profiles;
- unsafe execution surfaces;
- hardware-specific source hints;
- unsupported parser semantics.

The report binds Source Ingestion Sandbox Implementation evidence by digest and
keeps Source Intent, graph, HAC-IR, and runtime-plan outputs blocked.

## Security Boundary

This RFC does not authorize parser admission, Source Intent output,
source-to-ComputeGraph, source-to-HAC-IR, source-to-runtime-plan, package import,
plugin discovery, Triton JIT execution, decorator evaluation, device access,
generated artifact execution, native backend execution, dynamic library loading,
subprocesses, network access, runtime handle serialization, raw tensor values,
host path exposure, commands, or raw source text serialization.

The public report is digest-only and source-free.

## Contract

- API module: `src/tuc/frontend/parser_fuzz_negative_corpus.py`
- Example: `examples/parser_fuzz_negative_corpus_for_admitting_slice.py`
- Schema: `schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json`
- Golden: `tests/golden/frontend/parser_fuzz_negative_corpus_for_admitting_slice_report.json`
- Documentation: `docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md`
- RFC path: `rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md`

## Acceptance Criteria

- The corpus report is schema-versioned and fail-closed.
- The report binds Source Ingestion Sandbox Implementation evidence by digest.
- Public evidence serializes only source digests, counts, rejection categories,
  reason codes, and sandbox metadata.
- Rejection category and mutation-family coverage are complete.
- Source Intent plain data, graph output, HAC-IR output, and runtime-plan output
  remain false.
- Tests cover corpus behavior, drift, digest stability, source leakage, schema
  closure, and documentation links.