# Bounded Source Buffer API

Bounded Source Buffer API v0 is the first concrete input-boundary API for a
future admitting `direct_source_ingestion` slice.

It validates caller-provided source text as untrusted data, measures bounded
syntax metadata, binds a declared shape profile by digest, and emits only
metadata records plus source-free rejection reason codes.

It does not admit source ingestion. The current report keeps:

```text
direct_source_ingestion = false
source_to_compute_graph = false
source_to_hac_ir = false
source_to_runtime_plan = false
```

Run it with:

```bash
python examples/bounded_source_buffer_api.py
```

## Scope

The API accepts:

- caller-provided source text as an untrusted in-memory value;
- a report-safe source name;
- a declared shape profile.

The API emits:

- source digest;
- source byte and line counts;
- AST node and depth counts;
- declared shape-profile digest and bounds;
- source-free rejection reason codes.

It does not emit raw source text, Source Intent payloads, ComputeGraph, HAC-IR,
HS-IR, runtime plans, Python function objects, generated artifacts, backend
artifacts, host paths, commands, device identifiers, or runtime handles.

## Security Boundary

The API parses syntax as data only. It does not import packages, evaluate
decorators, inspect function objects, run Triton JIT, access devices, discover
plugins, spawn subprocesses, touch the network, load dynamic libraries, or
produce compiler artifacts.

Rejected buffers return source-free reason codes such as `empty_source`,
`line_budget`, `syntax_error`, and `shape_profile`.

## First Slice Role

This closes only the `bounded_source_buffer_api` prerequisite in the Real
Triton First Slice Plan. Remaining blockers still include sandbox
implementation, parser fuzz and negative corpus, source-free diagnostics
admission tests, Source Intent plain-data output goldens, CI replay, and
maintainer security review approval.

## Contract

- API module: `src/tuc/frontend/bounded_source_buffer.py`
- Example: `examples/bounded_source_buffer_api.py`
- Schema: `schemas/bounded_source_buffer_api_report.v0.schema.json`
- Golden: `tests/golden/frontend/bounded_source_buffer_api_report.json`
- Tests: `tests/test_bounded_source_buffer_api.py`
- RFC: `rfcs/0259-bounded-source-buffer-api.md`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
