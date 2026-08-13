# RFC 0201: Runtime Allocation Admission

Status: Accepted

## Summary

Add Runtime Allocation Admission v0 as data-only evidence between Runtime
Allocation Request Manifest and future allocator behavior.

## Motivation

Runtime Allocation Request Manifest names future allocator requests, but request
metadata alone should not imply that allocator behavior is safe to add. TUC needs
a separate admission artifact that proves each request is accepted only by the
current memory-budget evidence, remains digest-bound to the request manifest, and
continues to omit runtime handles.

## Design

Add:

- `src/tuc/runtime/allocation_admission.py` for the report model;
- `examples/runtime_allocation_admission.py` for deterministic emission;
- `schemas/runtime_allocation_admission_report.v0.schema.json` for fail-closed shape;
- `docs/RUNTIME_ALLOCATION_ADMISSION.md` for the review contract;
- `tests/golden/runtime_allocation_admission/current_report.json` for stable evidence;
- `tests/test_runtime_allocation_admission.py` for contract, schema, and negative checks.

Runtime Memory Planning Gate must require Allocation Admission before allocator,
memory-pool, device-allocation, runtime-handle, or aliasing behavior can count as
accepted runtime-planning evidence.

## Security

The report is data-only. It does not allocate memory, expose pointers, create
runtime handles, discover plugins, access devices, load dynamic libraries, spawn
subprocesses, read host paths, ingest benchmark output, or execute generated
artifacts.

## Consequences

Future allocator work has a reviewable admission contract. A passing admission
report proves metadata consistency and budget admission only; it does not prove
native allocator behavior, device allocation, or performance.
