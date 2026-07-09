# Source Ingestion Admission Gate

Source Ingestion Admission Gate v0 is the fail-closed admission gate for the
first possible `direct_source_ingestion` slice.

It does not approve or admit source ingestion. The current report keeps:

```text
admitted = false
approval_artifact_present = false
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/source_ingestion_admission_gate.py
```

## What It Binds

The gate binds the Source Ingestion Maintainer Security Review Packet by
SHA-256 metadata digest. The review packet in turn binds the admitted-slice
RFC, bounded source buffer, sandbox, parser fuzz negative corpus, source-free
diagnostics, Source-To-Intent plain-data golden, CI replay, and first-slice
plan evidence.

## Meaning

This gate turns the source-ingestion boundary into an explicit machine-checkable
decision point:

- review evidence is present;
- external maintainer approval is still absent;
- direct source ingestion remains denied;
- source-to-ComputeGraph, source-to-HAC-IR, and source-to-runtime-plan paths
  remain denied.

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

- Module: `src/tuc/frontend/source_ingestion_admission_gate.py`
- Example: `examples/source_ingestion_admission_gate.py`
- Schema: `schemas/source_ingestion_admission_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_admission_gate_report.json`
- Tests: `tests/test_source_ingestion_admission_gate.py`
- RFC: `rfcs/0266-source-ingestion-admission-gate.md`
- Review Packet: [Source Ingestion Maintainer Security Review Packet](SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
- Real Triton First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
