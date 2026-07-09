# RFC 0265: Source Ingestion Maintainer Security Review Packet

## Status

Accepted as non-admitting review evidence.

## Context

TUC now has the first source-ingestion admission prerequisites in place:
bounded source buffers, a non-admitting sandbox boundary, negative parser fuzz
coverage, source-free diagnostics, plain-data Source Intent goldens, read-only
CI replay, and a data-only first-slice plan.

The next step must not fake a maintainer security approval. A machine-generated
artifact may prepare the review packet, but only a real maintainer review can
satisfy `maintainer_security_review_approval`.

## Decision

Add `source_ingestion_maintainer_security_review_packet` as a digest-only,
source-free review packet for the first `direct_source_ingestion` slice.

The packet:

- binds the current source-ingestion RFC, buffer, sandbox, fuzz, diagnostics,
  golden, CI replay, and first-slice plan reports by digest;
- records `approval_status = not_approved`;
- keeps `direct_source_ingestion = false`;
- keeps `source_ingestion_admission_ready = false`;
- keeps `maintainer_security_review_approval` as remaining external evidence.

## Non-Goals

This RFC does not authorize source ingestion implementation, default parser
enablement, source-to-ComputeGraph lowering, source-to-HAC-IR lowering,
source-to-runtime-plan lowering, package import, plugin discovery, Triton JIT,
device access, generated artifacts, native backend execution, or performance
claims.

## Artifacts

- Module: `src/tuc/frontend/source_ingestion_maintainer_review.py`
- Example: `examples/source_ingestion_maintainer_security_review_packet.py`
- Schema: `schemas/source_ingestion_maintainer_security_review_packet_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_maintainer_security_review_packet_report.json`
- Tests: `tests/test_source_ingestion_maintainer_security_review_packet.py`
- Doc: `docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md`

## Consequences

The first source-ingestion slice becomes easier to review without becoming
admitting. TUC can show exactly which evidence a maintainer must inspect, while
the compiler continues to fail closed until an explicit security approval
exists outside the generated packet.
