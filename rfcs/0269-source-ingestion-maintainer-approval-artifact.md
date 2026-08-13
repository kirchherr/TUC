# RFC 0269: Source Ingestion Maintainer Approval Artifact

Status: accepted

## Summary

Add a fail-closed maintainer approval artifact for the future first
`direct_source_ingestion` slice.

## Motivation

TUC now has approval criteria and a maintainer-review packet for the first
source-ingestion slice. The remaining external approval must be represented as a
separate state so maintainers and gates can distinguish:

- criteria are defined;
- review evidence is ready;
- external approval is absent;
- a future external approval has been supplied.

Without a separate artifact, the Admission Gate can say approval is missing but
cannot bind that missing state as reviewable evidence.

## Decision

Add Source Ingestion Maintainer Approval Artifact v0:

- module: `src/tuc/frontend/source_ingestion_maintainer_approval.py`
- example: `examples/source_ingestion_maintainer_approval_artifact.py`
- schema: `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`
- golden: `tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json`
- tests: `tests/test_source_ingestion_maintainer_approval_artifact.py`
- doc: `docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md`

The artifact binds the Source Ingestion Maintainer Security Review Packet by
digest, requires that the packet contains Source Ingestion Approval Criteria,
and records `status = external_approval_not_supplied`,
`approval_status = not_approved`, `approval_artifact_present = false`, and
`source_ingestion_admission_ready = false`.

The Source Ingestion Admission Gate binds this artifact and remains fail-closed.

## Non-Goals

- No parser approval.
- No maintainer approval grant.
- No direct source ingestion.
- No source-to-ComputeGraph output.
- No source-to-HAC-IR output.
- No source-to-runtime-plan output.
- No package import, plugin discovery, JIT, device access, subprocess,
  dynamic-library, generated-artifact, or native-backend execution.

## Security Notes

The artifact must not serialize source text, Source Intent payloads, tensor
values, runtime handles, host paths, commands, device identifiers, plugin
entrypoints, generated code, backend artifacts, native benchmark output, or
executable artifacts.
