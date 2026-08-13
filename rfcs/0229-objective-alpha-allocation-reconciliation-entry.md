# RFC 0229: Objective Alpha Allocation Reconciliation Entry

- Status: accepted-for-prototype
- Created: 2026-06-26
- Phase: Alpha / Delta

## Summary

Expose Runtime Allocation Reconciliation as a fixed digest-only entry in the
Objective Alpha Public Proof Bundle.

This RFC does not add allocator behavior, memory pools, device allocation,
runtime handles, memory addresses, pointers, or native memory-management claims.

## Motivation

Runtime Memory Planning Gate already verifies Allocation Admission, Allocation
Receipt, and Allocation Reconciliation before allocator behavior can be accepted.
The public bundle should expose the final reconciliation artifact directly so a
reviewer can see that admitted allocation requests and dry-run receipts are bound
without unpacking gate internals.

## Decision

Add one fixed bundle entry:

- Evidence ID: `runtime_allocation_reconciliation`
- Entry point: `python examples/runtime_allocation_reconciliation.py`
- Artifact kind: `schema_versioned_allocation_reconciliation_report`
- Raw output policy: `digest_only`

The bundle records only a SHA-256 digest of the reconciliation report plus fixed
entry metadata. The underlying report remains governed by
`schemas/runtime_allocation_reconciliation_report.v0.schema.json`.

## Security Boundary

The bundle remains metadata-only. It must not contain raw tensor values,
tensor-value digests, runtime handles, allocator handles, allocation handles,
memory addresses, pointers, device identifiers, host paths, command lines,
environment variables, generated code, backend artifacts, plugin entrypoints,
dynamic-library paths, raw benchmark samples, or native allocation claims.

The schema keeps fixed entry IDs, fixed entry points, fixed artifact kinds,
`additionalProperties: false`, and exact entry count checks.

## Consequences

- The top-level Objective Alpha review artifact now exposes the final
  allocation admission-to-receipt consistency proof.
- Memory-planning evidence becomes easier to review without opening real memory
  allocation or handle surfaces.
- Native allocator behavior, memory pools, device allocation, aliasing, and
  runtime handles remain blocked claims.