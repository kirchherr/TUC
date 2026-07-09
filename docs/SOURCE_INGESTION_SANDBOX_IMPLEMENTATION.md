# Source Ingestion Sandbox Implementation

Source Ingestion Sandbox Implementation v0 is the first concrete wrapper around
Bounded Source Buffer API for the future `direct_source_ingestion` slice.

It is implemented, but it remains non-admitting:

```text
sandbox_status = implemented_non_admitting
direct_source_ingestion = false
source_to_intent_plain_data = false
source_to_compute_graph = false
source_to_hac_ir = false
source_to_runtime_plan = false
```

Run it with:

```bash
python examples/source_ingestion_sandbox_implementation.py
```

## Scope

The sandbox accepts the same narrow inputs as the bounded source buffer:

- caller-provided source text as untrusted in-memory data;
- a report-safe source name;
- a declared shape profile.

The sandbox emits only source-free metadata results. Accepted cases include a
bounded source-buffer record digest. Rejected cases include only a source digest,
a report-safe source name, and a source-free reason code.

It does not emit Source Intent plain data, Source Intent payloads, ComputeGraph,
TLIR, HAC-IR, HS-IR, runtime plans, Python function objects, generated artifacts,
backend artifacts, host paths, commands, device identifiers, runtime handles, or
raw source text.

## First Slice Role

This closes the `source_ingestion_sandbox_implementation` prerequisite in the
Real Triton First Slice Plan. The remaining blockers are:

- parser fuzz and negative corpus for the admitting slice;
- source-free diagnostics admission tests;
- Source Intent plain-data output goldens;
- CI replay for the admitted slice;
- maintainer security review approval.

## Security Boundary

The sandbox parses syntax as data only through `src/tuc/frontend/bounded_source_buffer.py`.
It does not import packages, evaluate decorators, inspect function objects, run
Triton JIT, access devices, discover plugins, spawn subprocesses, touch the
network, load dynamic libraries, execute native backends, produce compiler
artifacts, or authorize source-to-HAC-IR or source-to-runtime-plan shortcuts.

The public report binds the Bounded Source Buffer API report by digest and keeps
all outputs metadata-only and source-free.

## Contract

- API module: `src/tuc/frontend/source_ingestion_sandbox.py`
- Example: `examples/source_ingestion_sandbox_implementation.py`
- Schema: `schemas/source_ingestion_sandbox_implementation_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_sandbox_implementation_report.json`
- Tests: `tests/test_source_ingestion_sandbox_implementation.py`
- RFC: `rfcs/0260-source-ingestion-sandbox-implementation.md`
- First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
- Bounded Source Buffer API: [Bounded Source Buffer API](BOUNDED_SOURCE_BUFFER_API.md)