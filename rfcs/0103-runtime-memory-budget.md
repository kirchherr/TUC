# RFC 0103: Runtime Memory Budget v0

Status: Accepted

## Summary

Add Runtime Memory Budget v0 as a data-only report that checks Runtime
Allocation Plan evidence against explicit memory-domain budgets.

## Motivation

TUC now has buffer lifetime evidence and allocation-slot evidence. Before real
memory pools or device allocators are added, the runtime needs an inspectable
resource budget boundary. Otherwise a future allocator could grow from implicit
capacity assumptions instead of reviewable limits.

## Scope

This RFC adds:

- `src/tuc/runtime/memory_budget.py`
- `examples/runtime_memory_budget.py`
- `schemas/runtime_memory_budget_report.v0.schema.json`
- `tests/golden/runtime_memory_budget/current_report.json`
- tests for passing evidence, missing budgets, exceeded budgets, derived
  issues, fail-closed schema shape, and deterministic example output

## Non-Goals

This RFC does not add:

- real memory allocation
- host or device capacity discovery
- memory pools
- device allocation
- alias analysis
- synchronization or stream overlap
- executable backend discovery
- performance claims

## Security Boundary

Runtime Memory Budget v0 consumes an existing
`RuntimeAllocationPlanReport` plus explicit budget data. It derives usages and
issues, then emits bounded deterministic JSON.

It does not execute kernels, import backend modules, load dynamic libraries,
spawn subprocesses outside the example process, read host paths, read
environment variables, query devices, touch the network, execute generated
artifacts, or authorize executable backend surfaces.

## Acceptance Criteria

- The memory budget report schema is fail-closed.
- The current report has deterministic golden evidence.
- Every issue is derived by the report constructor.
- Used memory domains without budgets fail closed.
- Reserved-byte and peak-live-byte budget overruns fail closed.
- Runtime Memory Budget remains downstream of Runtime Allocation Plan and does
  not modify HAC-IR semantics.
