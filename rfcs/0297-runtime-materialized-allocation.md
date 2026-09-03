# RFC 0297: Runtime Materialized Allocation

- Status: Accepted
- Scope: Trusted prototype runtime
- Decision date: 2026-09-03

## Context

TUC already has deterministic evidence for produced-value lifetimes, exact-match
reuse groups, tensor-to-slot allocation bindings, memory-domain budgets,
allocation requests, budget admission, dry-run receipts, and reconciliation.
The Runtime Memory Planning Gate makes this chain merge-relevant, but no
persistent runtime slot has yet been allocated or reused.

RFCs 0295 and 0296 established the pattern for practical opt-in execution:
preserve accepted non-materialized evidence, add a bounded trusted primitive,
preflight the full plan before kernels run, and publish only closed metadata.

## Decision

Add `execute_graph_with_materialized_allocations()` as a separate opt-in path.
It accepts a `RuntimeAllocationExecutionPrerequisites` object containing the
complete memory-planning evidence chain and executes a fixed private NumPy slot
arena.

The implementation must:

1. rebuild and byte-compare every prerequisite report before allocation;
2. validate all input metadata and finite values before allocating slots;
3. accept only transfer-free `host_ram`, `row_major`, `float32` plans in v0;
4. require at least one planned exact-match reuse slot;
5. enforce slot, binding, element, and internal-byte limits;
6. allocate one private `float64` array per planned slot before graph execution;
7. copy and exactly verify each trusted kernel result in its assigned slot;
8. expose read-only slot views to downstream trusted kernels;
9. release values only at their proven final-use indexes;
10. permit later slot generations only after release;
11. retain only external inputs and immutable terminal output snapshots;
12. require an empty arena and passing Reference Correctness at completion;
13. emit no storage identity, pointer, address, handle, or tensor value.

The public contract is fixed by
`schemas/runtime_materialized_allocation_report.v0.schema.json` and
`tests/golden/runtime_materialized_allocation/current_report.json`.

## Memory Semantics

Allocation Plan bytes remain graph-level `float32` planning bytes. The trusted
prototype executor uses `float64`; therefore internal persistent bytes are
computed and bounded independently.

For the accepted graph:

```text
four independent runtime tensors: 4 * 128 = 512 bytes
three materialized runtime slots:   3 * 128 = 384 bytes
executed persistent-slot saving:                128 bytes
```

Kernel-created temporary results and immutable terminal output snapshots are
excluded from this claim. v0 proves persistent slot placement and reuse, not
total process high-water memory reduction.

## Compatibility

`execute_graph()`, `execute_graph_with_materialized_layouts()`, and
`execute_graph_with_materialized_data_movement()` are unchanged. Existing
Tensor Store, Allocation Receipt, Runtime Evidence Matrix, and Runtime Evidence
Gate artifacts retain their accepted meanings.

The first materialized allocator report remains a standalone opt-in proof.
Promoting it into the central Runtime Evidence Gate requires a separate
readiness and migration decision.

## Security

The allocator is fixed in-repository code and accepts no plugins, external
allocators, native artifacts, paths, commands, devices, dynamic libraries,
subprocesses, JIT, network access, memory mapping, pointers, or handles. The
complete plan and inputs are validated before persistent allocation or kernel
execution.

Only bounded identifiers, shapes, byte counts, generations, lifetime indexes,
statuses, and metadata digests are serialized. Storage identity and values stay
private to the process.

## Alternatives Rejected

- Reinterpret dry-run Allocation Receipts as real allocation: rejected because
  it would invalidate their explicit `dry_run_only` contract.
- Modify `RuntimeTensorStore` to overwrite historical records: rejected because
  it would silently change accepted evidence and expose reused-value ambiguity.
- Serialize `id(array)`, addresses, or opaque handles: rejected because they are
  unstable, leak process details, and create an unnecessary capability surface.
- Claim total memory reduction: rejected because trusted kernels still allocate
  temporary results and output evidence retains immutable snapshots.
- Add device or mixed-domain allocation immediately: rejected because transfer
  staging and layout-specific allocation lifetimes are not yet modeled.

## Consequences

TUC now crosses the allocator boundary in a bounded research slice. A reviewed
allocation plan causes real persistent slot creation, exact writes, lifetime
releases, and a second generation in the same slot while terminal semantics
remain correct.

The result remains a host-process simulator proof, not native allocator or
performance evidence.
