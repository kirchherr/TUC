# Runtime Materialized Allocation

## Status

Runtime Materialized Allocation v0 is an implemented, opt-in trusted simulator
proof. It turns the accepted Buffer Lifetime, Allocation Plan, Memory Budget,
Request Manifest, Admission, Receipt, and Reconciliation chain into a bounded
in-process slot arena and executes one exact-match reuse decision.

Decision: `rfcs/0297-runtime-materialized-allocation.md`.

## Claim

TUC now proves that one accepted allocation plan can control persistent runtime
storage for produced values:

```text
canonical memory-planning evidence
  -> preallocate slot_001, slot_002, slot_003 once
  -> write left_tmp into slot_001 generation 1
  -> release left_tmp at its proven final use
  -> write right_tmp into slot_001 generation 2
  -> retain terminal output snapshots only
  -> reference correctness PASS
```

The same private NumPy slot storage backs both `left_tmp` and `right_tmp` at
different, non-overlapping lifetimes. No storage identity, pointer, address, or
runtime handle enters the public trace or report.

## Opt-In API

```python
execute_graph_with_materialized_allocations(
    graph,
    partition_plan,
    inputs,
    prerequisites,
)
```

`prerequisites` contains the complete reviewed memory-planning chain. The
default `execute_graph()` path and the separate materialized layout and transfer
paths remain unchanged.

## Complete Preflight

Before input copying, slot allocation, or the first graph kernel, v0:

- validates the graph against the fixed trusted executor registry;
- requires passing Allocation Plan, Memory Budget, Request Manifest,
  Admission, Receipt, and Reconciliation reports;
- rebuilds the complete chain and requires byte-identical canonical reports;
- binds every produced tensor to producer index, lifetime, slot, shape, dtype,
  memory domain, layout, and planned bytes;
- accepts only transfer-free `host_ram`, `row_major`, `float32` proof slices;
- requires at least one planned exact-match reuse slot;
- limits execution to 256 slots, 4,096 bindings, 2,000,000 elements per slot,
  and 128 MiB of internal persistent slot storage;
- validates all input names, shapes, `float64` dtypes, element counts, and finite
  values before persistent storage is allocated.

Any stale digest, forged report, unsupported placement, missing reuse decision,
oversized storage request, malformed input, or non-finite kernel result fails
closed.

## Execution Semantics

The fixed policy is `preallocate_write_release_reuse`:

1. allocate exactly one private `float64` NumPy array per planned slot;
2. execute a trusted reference kernel;
3. copy its finite result into the assigned slot and verify exact equality;
4. expose only a read-only view to downstream trusted kernels;
5. release the tensor exactly at its proven `last_use_index`;
6. permit a later slot generation only after that release;
7. copy terminal outputs into immutable result snapshots;
8. release all remaining arena values and require an empty arena.

The current proof has four produced tensors and three persistent slots. The
graph-level `float32` plan reserves 192 bytes. The prototype executor uses
`float64`, so its persistent arena reserves 384 bytes instead of 512 bytes for
four independent persistent runtime buffers, demonstrating 128 bytes of actual
slot-reuse savings.

Trusted kernels still create temporary result arrays before the verified slot
copy. Terminal evidence also retains two immutable output snapshots. Both are
explicitly excluded from the allocator memory claim.

## Evidence

- allocator execution: `src/tuc/runtime/allocation_executor.py`;
- report binding: `src/tuc/runtime/materialized_allocation.py`;
- entry point: `examples/runtime_materialized_allocation.py`;
- schema: `schemas/runtime_materialized_allocation_report.v0.schema.json`;
- golden: `tests/golden/runtime_materialized_allocation/current_report.json`;
- tests: `tests/test_runtime_materialized_allocation.py`.

Run:

```bash
python examples/runtime_materialized_allocation.py
```

The closed report binds all planning prerequisites, the runtime operation trace,
the allocation execution trace, terminal output metadata, and Reference
Correctness by SHA-256 metadata digests.

## Security Boundary

The allocator is fixed trusted project code. It does not discover allocators or
plugins, invoke external allocation APIs, access devices, map files or memory,
load dynamic libraries, run generated artifacts, use JIT or subprocesses,
access a network, or create an unbounded pool.

The report omits tensor contents, tensor-value digests, storage identities,
pointers, addresses, handles, device identifiers, paths, commands, source,
generated code, and backend artifacts.

## Non-Claims

This proof does not establish:

- native malloc/free, device allocation, NUMA placement, or physical residency;
- allocator plugins, memory pools, handles, pointers, or mapped memory;
- direct kernel output into a planned slot;
- zero-copy execution or total process high-water memory reduction;
- allocation latency, throughput, fragmentation, energy, or performance parity;
- allocation for transfer staging, blocked layouts, devices, or arbitrary
  dtypes.

The next allocator expansion must model transfer staging and layout-specific
storage explicitly before mixed-domain allocation can be materialized.
