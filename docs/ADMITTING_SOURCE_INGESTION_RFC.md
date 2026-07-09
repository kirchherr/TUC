# Admitting Source Ingestion RFC

Admitting Source Ingestion RFC v0 is a requirements-only review artifact for
the first possible `direct_source_ingestion` admitting slice.

It does not implement source ingestion and does not admit source ingestion. The
current report keeps:

```text
admitted = false
implementation_status = not_implemented
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/admitting_source_ingestion_rfc.py
```

## Scope

The candidate target slice is:

```text
bounded_source_buffer_to_source_intent_plain_data
```

Allowed outputs remain limited to Source Intent plain data, sanitized
diagnostics, and metadata digests. The RFC denies direct output of
`ComputeGraph`, HAC-IR, HS-IR, runtime plans, generated artifacts, Python
function objects, and backend artifacts.

## Remaining Evidence

Before source ingestion can become admitting, TUC still requires:

- source-ingestion sandbox implementation evidence;
- bounded source-buffer API evidence;
- parser fuzz and negative corpus for the admitting slice;
- source-free diagnostics admission tests;
- Source Intent plain-data output goldens;
- CI replay for the admitted slice;
- maintainer security review approval.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, produce HAC-IR, produce runtime plans, or authorize
compiler shortcuts from source.

## Contract

- Example: `examples/admitting_source_ingestion_rfc.py`
- Schema: `schemas/admitting_source_ingestion_rfc_report.v0.schema.json`
- Golden: `tests/golden/frontend/admitting_source_ingestion_rfc_report.json`
- Tests: `tests/test_admitting_source_ingestion_rfc.py`
- RFC: `rfcs/0258-admitting-source-ingestion-rfc.md`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
