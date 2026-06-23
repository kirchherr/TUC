# RFC 0202: Runtime Allocation Receipt

- Status: Accepted
- Date: 2026-06-23

## Summary

Add Runtime Allocation Receipt v0 as data-only allocator dry-run evidence after
Runtime Allocation Admission and before any memory-pool, device-allocation,
runtime-handle, or real allocator behavior.

## Motivation

Runtime Allocation Admission proves that future allocator requests are admitted
by current Memory Budget evidence. The next practical step is to prove that
those admitted requests can become deterministic allocation ledger entries
without introducing pointers, handles, device access, plugin discovery, or
allocator execution.

## Design

The receipt surface consists of:

- `src/tuc/runtime/allocation_receipt.py` for immutable data objects, derived
  issues, deterministic metadata digests, and stable JSON rendering;
- `examples/runtime_allocation_receipt.py` for deterministic emission;
- `schemas/runtime_allocation_receipt_report.v0.schema.json` for fail-closed
  shape validation;
- `docs/RUNTIME_ALLOCATION_RECEIPT.md` for review semantics and security
  boundary;
- `tests/golden/runtime_allocation_receipt/current_report.json` for stable
  evidence;
- `tests/test_runtime_allocation_receipt.py` for contract, schema, and
  negative checks.

Runtime Memory Planning Gate must require Allocation Receipt before allocator,
memory-pool, device-allocation, aliasing, or runtime-handle behavior can count
as accepted runtime evidence.

## Security

The receipt is data-only and uses `dry_run_only` allocation mode. It contains
no runtime handles, pointers, host paths, device IDs, backend artifacts, plugin
entrypoints, dynamic imports, subprocesses, JIT surfaces, or raw benchmark
outputs. The deterministic offset is not an address and cannot authorize memory
access.

## Non-Goals

- No real allocator.
- No memory pool.
- No device allocation.
- No pointer, handle, address, or executable artifact.
- No native performance or allocation-efficiency claim.
