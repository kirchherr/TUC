# Real Triton First Slice Plan

Real Triton First Slice Plan v0 is the data-only plan for the first possible
admitting Real Triton integration slice.

It does not admit Real Triton integration. The current report keeps:

```text
admitted = false
source_ingestion_admission_ready = false
admission_status = blocked
```

Run it with:

```bash
python examples/real_triton_first_slice_plan.py
```

## What It Binds

The plan binds five current artifacts by SHA-256 metadata digest:

- Real Triton Integration Admission Gate.
- Real Triton Surface Gate Completion.
- Source Ingestion Quarantine Gate.
- Source-To-Intent Research Source Runtime Smoke.
- Source-To-Intent Research Kernel Ingress Proof Bundle.

## Meaning

The plan identifies `direct_source_ingestion` as the first candidate surface
for a future admitting slice, but records the missing admission evidence before
that can happen.

The remaining Real Triton surfaces stay blocked:

- frontend package import;
- plugin discovery;
- Triton JIT execution;
- device access;
- generated artifact execution;
- native backend execution.

## Missing Admission Evidence

Before `direct_source_ingestion` can become admitting, TUC still requires:

- an admitting source-ingestion RFC;
- sandbox implementation evidence;
- bounded source-buffer API evidence;
- fuzz and negative-test corpus for the admitting slice;
- source-free diagnostics admission tests;
- source-to-Intent plain-data output goldens;
- CI replay for the admitted slice;
- maintainer security review approval.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, or authorize source-to-HAC-IR or source-to-runtime-plan
shortcuts.

## Contract

- Example: `examples/real_triton_first_slice_plan.py`
- Schema: `schemas/real_triton_first_slice_plan_report.v0.schema.json`
- Golden: `tests/golden/frontend/real_triton_first_slice_plan_report.json`
- Tests: `tests/test_real_triton_first_slice_plan.py`
- RFC: `rfcs/0257-real-triton-first-slice-plan.md`
- Admission Gate: [Real Triton Integration Admission Gate](REAL_TRITON_INTEGRATION_ADMISSION_GATE.md)
- Surface Gate Completion: [Real Triton Surface Gate Completion](REAL_TRITON_SURFACE_GATE_COMPLETION.md)
