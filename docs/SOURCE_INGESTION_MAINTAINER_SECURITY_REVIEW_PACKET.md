# Source Ingestion Maintainer Security Review Packet

Source Ingestion Maintainer Security Review Packet v0 prepares the first
`direct_source_ingestion` slice for human maintainer review.

It is not an approval and does not admit source ingestion. The current report
keeps:

```text
approval_status = not_approved
direct_source_ingestion = false
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/source_ingestion_maintainer_security_review_packet.py
```

## What It Binds

The packet binds eight source-free artifacts by SHA-256 metadata digest:

- Admitting Source Ingestion RFC.
- Bounded Source Buffer API.
- Source Ingestion Sandbox Implementation.
- Parser Fuzz Negative Corpus For Admitting Slice.
- Source-Free Diagnostics Admission Tests.
- Source-To-Intent Plain-Data Output Golden For Admitted Slice.
- CI Replay For Admitted Slice.
- Real Triton First Slice Plan.

## Meaning

This artifact turns the source-ingestion admission work into a reviewable
packet without changing the admission boundary. It proves that the current
evidence is collected, deterministic, source-free, and ready for a maintainer
security review, but it records no maintainer decision.

Before `direct_source_ingestion` can become admitting, TUC still requires:

- maintainer security review approval.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, or authorize source-to-ComputeGraph, source-to-HAC-IR, or
source-to-runtime-plan shortcuts.

## Contract

- Module: `src/tuc/frontend/source_ingestion_maintainer_review.py`
- Example: `examples/source_ingestion_maintainer_security_review_packet.py`
- Schema: `schemas/source_ingestion_maintainer_security_review_packet_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_maintainer_security_review_packet_report.json`
- Tests: `tests/test_source_ingestion_maintainer_security_review_packet.py`
- RFC: `rfcs/0265-source-ingestion-maintainer-security-review-packet.md`
- Admitting Source Ingestion RFC: `docs/ADMITTING_SOURCE_INGESTION_RFC.md`
- Real Triton First Slice Plan: `docs/REAL_TRITON_FIRST_SLICE_PLAN.md`
