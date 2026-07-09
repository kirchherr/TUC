# RFC 0262: Source-Free Diagnostics Admission Tests

- Status: Accepted
- Date: 2026-07-09
- Area: Real Triton integration

## Summary

Add `source_free_diagnostics_admission_tests` as source-free, data-only
evidence for the future admitting source-to-Intent parser slice.

## Motivation

The Parser Fuzz Negative Corpus proves which malformed, unsupported, unsafe, or
hardware-specific source cases a future admitting parser must reject. The next
safe step is to prove that the diagnostics for those rejections stay
source-free, bounded, reason-code based, and reviewable before any parser is
allowed to emit Source Intent plain data.

## Decision

Create `src/tuc/frontend/source_free_diagnostics_admission.py` and
`examples/source_free_diagnostics_admission_tests.py` with schema
`schemas/source_free_diagnostics_admission_tests_report.v0.schema.json`, golden
`tests/golden/frontend/source_free_diagnostics_admission_tests_report.json`,
and documentation at `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`.

The report records one public diagnostic metadata record per parser negative
corpus case. Public records contain only source digests, diagnostic classes,
diagnostic codes, reason codes, message template IDs, bounded byte counts, and
explicit false flags for Source Intent, graph, HAC-IR, and runtime-plan output.

The report binds Parser Fuzz Negative Corpus For Admitting Slice evidence by
digest and removes `source_free_diagnostics_admission_tests` from the remaining
admission blockers while keeping source ingestion blocked.

## Security Boundary

This RFC does not authorize parser admission, Source Intent output,
source-to-ComputeGraph, source-to-HAC-IR, source-to-runtime-plan, package import,
plugin discovery, Triton JIT execution, decorator evaluation, device access,
generated artifact execution, native backend execution, dynamic library loading,
subprocesses, network access, runtime handle serialization, raw tensor values,
host path exposure, commands, source locations, source excerpts, or raw source
text serialization.

The public report is digest-only and source-free.

## Contract

- API module: `src/tuc/frontend/source_free_diagnostics_admission.py`
- Example: `examples/source_free_diagnostics_admission_tests.py`
- Schema: `schemas/source_free_diagnostics_admission_tests_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_free_diagnostics_admission_tests_report.json`
- Documentation: `docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md`
- RFC path: `rfcs/0262-source-free-diagnostics-admission-tests.md`

## Acceptance Criteria

- The diagnostics report is schema-versioned and fail-closed.
- The report binds Parser Fuzz Negative Corpus evidence by digest.
- Public diagnostics serialize only source digests, diagnostic classes,
  diagnostic codes, reason codes, message template IDs, and bounded counts.
- Diagnostic class, reason-code, and message-template coverage are complete.
- Source Intent plain data, graph output, HAC-IR output, and runtime-plan output
  remain false.
- Tests cover diagnostics behavior, drift, digest stability, source leakage,
  schema closure, and documentation links.
