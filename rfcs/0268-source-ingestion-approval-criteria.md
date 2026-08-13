# RFC 0268: Source Ingestion Approval Criteria

Status: accepted

## Summary

Define a data-only approval-criteria artifact for the future first
`direct_source_ingestion` slice.

## Motivation

TUC is moving toward realistic Triton/source ingestion, but that surface must
remain closed until a maintainer can review fixed, objective criteria. Without a
separate criteria artifact, a later approval decision could become informal or
depend on reviewer memory instead of machine-checkable evidence.

## Decision

Add Source Ingestion Approval Criteria v0:

- module: `src/tuc/frontend/source_ingestion_approval_criteria.py`
- example: `examples/source_ingestion_approval_criteria.py`
- schema: `schemas/source_ingestion_approval_criteria_report.v0.schema.json`
- golden: `tests/golden/frontend/source_ingestion_approval_criteria_report.json`
- tests: `tests/test_source_ingestion_approval_criteria.py`
- doc: `docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md`

The artifact is criteria-only and source-free. It records
`criteria_status = criteria_defined_not_approved`,
`approval_status = not_approved`, `admitted = false`, and
`source_ingestion_admission_ready = false`.

The Source Ingestion Maintainer Security Review Packet binds this artifact by
digest before the Source Ingestion Admission Gate can consider an external
maintainer approval.

## Non-Goals

- No parser approval.
- No direct source ingestion.
- No source-to-ComputeGraph output.
- No source-to-HAC-IR output.
- No source-to-runtime-plan output.
- No package import, plugin discovery, JIT, device access, subprocess,
  dynamic-library, generated-artifact, or native-backend execution.
- No production compiler or native performance claim.

## Security Notes

The artifact must not serialize source text, Source Intent payloads, tensor
values, runtime handles, host paths, commands, device identifiers, plugin
entrypoints, generated code, backend artifacts, native benchmark output, or
executable artifacts.
