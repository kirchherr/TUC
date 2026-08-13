# Runtime Allocation Reconciliation v0

Runtime Allocation Reconciliation v0 is the policy layer between Allocation Admission and any future allocator implementation. It checks that admitted allocation requests and dry-run allocation receipts describe the same bounded ledger.

This artifact is intentionally data-only. It records identifiers, metadata digests, counts, byte totals, per-domain offsets, and policy status. It does not expose runtime handles, memory addresses, device pointers, backend artifacts, host paths, generated code, subprocesses, network access, or executable allocator hooks.

## Contract

- Schema: `schemas/runtime_allocation_reconciliation_report.v0.schema.json`
- Example: `examples/runtime_allocation_reconciliation.py`
- Golden: `tests/golden/runtime_allocation_reconciliation/current_report.json`
- RFC: `rfcs/0203-runtime-allocation-reconciliation.md`
- Contract: `runtime_allocation_reconciliation.data_only.v0`
- Policy: `allocation_reconciliation.no_handles.no_pointers.contiguous_offsets.v0`

## What It Proves

- every admitted allocation request has a matching dry-run receipt row;
- request, slot, memory-domain, budget, and byte bindings agree;
- receipt rows are contiguous per memory domain;
- total admitted bytes equal total receipted and reconciled bytes;
- the receipt is bound to the same Admission metadata digest;
- the allocator boundary still exposes no runtime handles or memory addresses.

## What It Does Not Prove

This is not a real allocator and does not reserve memory. It does not model free lists, alias handles, pooling, fragmentation, compaction, physical placement, device APIs, or backend-specific memory commands. Those must enter later as separate, reviewed artifacts with their own evidence gates.
