# RFC 0266: Source Ingestion Admission Gate

## Status

Accepted as fail-closed admission-gate evidence.

## Context

The Source Ingestion Maintainer Security Review Packet collects the current
non-admitting evidence for the first `direct_source_ingestion` slice, but it is
not an approval. TUC needs a machine-checkable gate that makes this boundary
explicit: review evidence may be ready, while admission remains denied until an
external maintainer security approval exists.

## Decision

Add `source_ingestion_admission_gate` as a digest-only, source-free report that
binds the maintainer-review packet and records:

- `admitted = false`;
- `approval_artifact_present = false`;
- `approval_status = not_approved`;
- `source_ingestion_admission_ready = false`;
- `direct_source_ingestion = false`;
- `maintainer_security_review_approval` as required external evidence.

## Non-Goals

This RFC does not authorize source ingestion implementation, default parser
enablement, source-to-ComputeGraph lowering, source-to-HAC-IR lowering,
source-to-runtime-plan lowering, package import, plugin discovery, Triton JIT,
device access, generated artifacts, native backend execution, or performance
claims.

## Artifacts

- Module: `src/tuc/frontend/source_ingestion_admission_gate.py`
- Example: `examples/source_ingestion_admission_gate.py`
- Schema: `schemas/source_ingestion_admission_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_admission_gate_report.json`
- Tests: `tests/test_source_ingestion_admission_gate.py`
- Doc: `docs/SOURCE_INGESTION_ADMISSION_GATE.md`
- Maintainer Approval Artifact Doc: `docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md`
- Maintainer Approval Artifact Example: `examples/source_ingestion_maintainer_approval_artifact.py`
- Maintainer Approval Artifact Schema: `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`

## Consequences

The first source-ingestion slice now has an explicit gate between prepared
review evidence and future admission. A future approval must change a dedicated
external-evidence path rather than silently flipping parser or runtime flags.
