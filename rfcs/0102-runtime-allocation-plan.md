# RFC 0102: Runtime Allocation Plan v0

Status: Accepted

## Summary

Add Runtime Allocation Plan v0 as a data-only evidence layer that maps produced
tensor lifetimes to planned allocation slots.

## Motivation

Runtime Buffer Lifetime v0 shows when produced tensor buffers are live. The next
practical runtime step is to turn those lifetime facts into explicit slot
bindings so future allocator work starts from reviewable evidence instead of an
implicit memory model.

## Scope

This RFC adds:

- `src/tuc/runtime/allocation.py`
- `examples/runtime_allocation_plan.py`
- `schemas/runtime_allocation_plan_report.v0.schema.json`
- `tests/golden/runtime_allocation_plan/current_report.json`
- tests for derived issues, fail-closed schema shape, forbidden execution
  surface names, and deterministic example output

## Non-Goals

This RFC does not add:

- real memory allocation
- memory pools
- device allocation
- in-place operation semantics
- alias analysis
- stream overlap or synchronization
- executable backend discovery
- benchmark or performance claims

## Security Boundary

Runtime Allocation Plan v0 is data-only. It consumes a
`RuntimeBufferLifetimeReport`, derives bindings and slots, derives all issues,
and emits bounded deterministic JSON.

It does not execute kernels, import backend modules, load dynamic libraries,
spawn subprocesses outside the example process, read host paths, read
environment variables, access devices, touch the network, execute generated
artifacts, or authorize executable backend surfaces.

## Acceptance Criteria

- The allocation report schema is fail-closed.
- The current report has deterministic golden evidence.
- Every allocation issue is derived by the report constructor.
- Reused slots require non-overlapping live ranges.
- Reserved bytes must not exceed total tensor bytes.
- Runtime Allocation Plan remains downstream of Runtime Buffer Lifetime and does
  not modify HAC-IR semantics.
