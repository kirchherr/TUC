# Runtime Allocation Plan

Runtime Allocation Plan v0 is a data-only report for planned allocation slots
derived from Runtime Buffer Lifetime evidence.

Schema:
`schemas/runtime_allocation_plan_report.v0.schema.json`

Golden:
`tests/golden/runtime_allocation_plan/current_report.json`

Example:

```bash
python examples/runtime_allocation_plan.py
```

## What It Records

For every produced tensor lifetime, the report records:

- tensor-to-slot binding
- producer operation and operation index
- first live index and last use index
- required bytes
- memory domain
- layout
- dtype and shape

For every planned slot, the report records:

- slot id
- source reuse group id
- reserved bytes
- memory domain
- layout
- dtype and shape
- tensor names assigned to the slot
- whether the slot is exclusive or reused
- whether assigned live ranges are non-overlapping

The report also records `allocation_metadata_digest`, a deterministic digest
over allocation metadata used by Runtime Memory Budget and Runtime Memory
Planning Gate binding checks.

## Why It Exists

Runtime Buffer Lifetime v0 proves which produced tensors are live when. Runtime
Allocation Plan v0 turns that evidence into explicit, reviewable slot bindings
before TUC adds memory pools, device allocation, in-place semantics, or real
allocator behavior.

The source Buffer Lifetime metadata digest binds an allocation plan to the
lifetime evidence from which its slots were derived. This prevents stale
allocation evidence from being accepted for a different lifetime report.

The goal is to make allocation intent inspectable without pretending that TUC
already owns host or device memory.

## Security Boundary

The report is data-only. It consumes a bounded `RuntimeBufferLifetimeReport`,
validates bounded fields, derives all issues, and serializes deterministic JSON.

It does not allocate memory, execute kernels, discover plugins, import backend
modules, load dynamic libraries, spawn subprocesses outside the example
process, access devices, touch the network, execute generated artifacts, run
JIT code, read host paths, read environment variables, load benchmark output,
or authorize executable backend surfaces.

## Current Limitations

- Slots are planned evidence, not live memory handles.
- Reuse is allowed only when inherited lifetime groups are exact-shape,
  exact-dtype, exact-layout, exact-domain, and non-overlapping.
- No buffer pool, alias analysis, synchronization, stream overlap, or device
  allocation is modeled.
- `total_reserved_bytes` is an evidence number, not a runtime allocation result.
- In-place operations remain future work.
