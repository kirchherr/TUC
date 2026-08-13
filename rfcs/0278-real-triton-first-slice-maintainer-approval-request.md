# RFC 0278: Real Triton First Slice Maintainer Approval Request

## Status

Accepted.

## Context

The Real Triton first-slice admission readiness gate proves that current
repository evidence is bound and still blocked on external maintainer security
review approval. The next practical step is a compact handoff artifact that a
reviewer can inspect without opening any source-ingestion surface.

## Decision

Add a source-free Real Triton First Slice Maintainer Approval Request report:

- Example: `examples/real_triton_first_slice_maintainer_approval_request.py`
- Schema: `schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json`
- Golden: `tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json`
- Doc: `docs/REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST.md`
- Tests: `tests/test_real_triton_first_slice_maintainer_approval_request.py`

The request binds the admission readiness gate, maintainer review packet,
missing approval artifact, and source-ingestion admission gate by digest. It
records `request_status = ready_for_external_review` and
`approval_status = not_approved`.

## Non-Goals

This RFC does not approve source ingestion, implement a parser, execute Triton
source, run JIT code, access devices, import frontend packages, discover
plugins, emit generated artifacts, claim native performance parity, or replace
vendor compiler stacks.

## Security

The artifact is data-only, digest-only, source-free, and fail-closed. It is not
an approval artifact and must preserve:

- `approval_request_is_approval = false`
- `approval_artifact_present = false`
- `admission_ready = false`
- `admitted = false`
- `surface_opened = false`

The request must not serialize source text, Source Intent payloads, raw tensor
values, runtime handles, host paths, device identifiers, command lines, backend
artifacts, raw benchmark data, or generated code.
