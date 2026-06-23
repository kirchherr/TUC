# RFC 0203: Runtime Allocation Reconciliation

Status: Accepted

## Context

TUC now has data-only Runtime Allocation Admission and Runtime Allocation Receipt artifacts. Admission proves that requested allocations fit the declared memory budget. Receipt records deterministic dry-run allocation offsets without exposing runtime handles or memory addresses.

The next secure-by-design step is a reconciliation artifact that proves both sources describe the same ledger before any real allocator, memory pool, or backend runtime is introduced.

## Decision

Add Runtime Allocation Reconciliation v0 with:

- schema `schemas/runtime_allocation_reconciliation_report.v0.schema.json`;
- example `examples/runtime_allocation_reconciliation.py`;
- golden `tests/golden/runtime_allocation_reconciliation/current_report.json`;
- contract `runtime_allocation_reconciliation.data_only.v0`;
- policy `allocation_reconciliation.no_handles.no_pointers.contiguous_offsets.v0`.

The artifact checks Admission-to-Receipt bindings, source metadata digests, counts, byte totals, per-row request and slot identity, memory-domain and budget identity, and contiguous per-domain receipt offsets.

## Security Boundary

The artifact is data-only. It explicitly blocks runtime handles, allocator handles, memory addresses, device pointers, backend artifacts, generated code, dynamic imports, dynamic libraries, subprocesses, network access, host paths, and raw timing samples.

## Consequences

Future allocator prototypes must pass through a stable reconciliation policy before they can claim execution readiness. This keeps the project practical while preserving the Universal Compute research claim: hardware-independent evidence first, hardware-specific implementation later.
