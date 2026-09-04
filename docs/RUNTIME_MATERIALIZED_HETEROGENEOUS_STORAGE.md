# Runtime Materialized Heterogeneous Storage

## Status

Runtime Materialized Heterogeneous Storage v0 is an implemented, opt-in
trusted simulator proof. It binds the accepted Runtime Heterogeneous Storage
Plan to bounded in-process storage and executes produced, layout-staging, and
transfer-target lifetimes through the exact planned slots and events.

Decision: `rfcs/0299-runtime-materialized-heterogeneous-storage.md`.

## Claim

TUC now proves that one canonical mixed-domain storage plan can govern actual
simulator storage across a heterogeneous execution slice:

```text
ComputeGraph + PartitionPlan
  -> canonical heterogeneous storage plan
  -> complete preflight before allocation
  -> five private preallocated slots
  -> blocked producer storage with verified zero padding
  -> row-major layout-staging storage
  -> distinct transfer-target storage
  -> trusted consumer execution
  -> exact planned releases and three post-release reuses
  -> terminal output snapshots
  -> Reference Correctness + Backend Equivalence PASS
```

The proof turns all eight planned lifetimes into real writes and releases. The
three role-isolated slots used by the first `matmul -> relu` slice are reused
by the second slice only after their previous generations have reached the
planned final-use event.

## Opt-In API

```python
execute_graph_with_materialized_heterogeneous_storage(
    graph,
    partition_plan,
    inputs,
    storage_plan,
)
```

The caller supplies the reviewed storage plan. The executor rebuilds that plan
and requires byte-identical canonical evidence before allocating a slot. The
default `execute_graph()` path and the earlier opt-in layout, transfer, and
allocation paths remain unchanged.

## Complete Preflight

Before input copying, slot allocation, or the first graph kernel, v0:

- validates the graph against the fixed trusted executor registry;
- validates every input name, shape, dtype, element count, and finite value;
- rebuilds Runtime Heterogeneous Storage Plan and requires exact canonical
  equality;
- binds each lifetime to its slot, role, domain, layout, physical shape, byte
  count, first-live event, and last-use event;
- requires the complete produced -> layout-staging -> transfer-target chain for
  each moving tensor;
- accepts only `float32` plans represented internally by bounded `float64`
  arrays, `row_major`, and fixed rank-2 2x2 `blocked` storage;
- rejects any slot whose runtime storage exceeds 32 MiB and any input set whose
  copied storage exceeds 32 MiB;
- applies the existing bounded graph, lifetime, slot, physical-element, and
  metadata-report limits.

Stale evidence, missing staging, forged source relationships, unsupported
layouts, early slot reuse, malformed inputs, or non-finite results fail closed.

## Execution Semantics

The fixed policy is `canonical_plan_preallocate_write_release_reuse`:

1. allocate exactly one private NumPy `float64` array per planned slot;
2. execute only fixed trusted simulator backend functions;
3. write each producer result into its planned physical representation;
4. require all padded cells in 2x2 blocked storage to remain zero;
5. materialize row-major layout staging from the exact blocked source;
6. copy into distinct transfer-target staging before consumer execution;
7. expose read-only logical views to downstream trusted kernels;
8. release each storage generation at its exact planned final-use event;
9. allow reuse only after the previous generation has been released;
10. retain only external inputs and immutable terminal output snapshots;
11. require an empty slot arena at graph end.

The canonical proof contains two sequential 3x3 `matmul -> relu` slices. Its
eight lifetimes use five slots and execute three reuse events. The `float32`
plan reserves 208 bytes instead of 344 unreused bytes. The prototype's private
`float64` arena reserves 416 bytes instead of 688 unreused bytes, demonstrating
272 bytes of executed slot-reuse savings.

For each 3x3 systolic result, the logical nine elements occupy a padded 4x4
surface represented as physical shape `(2, 2, 2, 2)`: 64 planned `float32`
bytes and 128 simulator `float64` bytes. Planned and runtime byte domains are
reported separately.

Trusted kernels still create temporary NumPy results before verified slot
writes. External input copies and immutable terminal output snapshots also
remain outside the persistent-slot memory claim.

## Evidence

- executor: `src/tuc/runtime/heterogeneous_storage_executor.py`;
- report binding: `src/tuc/runtime/materialized_heterogeneous_storage.py`;
- entry point: `examples/runtime_materialized_heterogeneous_storage.py`;
- schema:
  `schemas/runtime_materialized_heterogeneous_storage_report.v0.schema.json`;
- golden:
  `tests/golden/runtime_materialized_heterogeneous_storage/current_report.json`;
- tests: `tests/test_runtime_materialized_heterogeneous_storage.py`.

Run:

```bash
python examples/runtime_materialized_heterogeneous_storage.py
```

The closed report binds the canonical storage-plan digest, storage execution
trace, terminal output metadata, Reference Correctness, Backend Equivalence,
Materialized Layout Conversion, and Materialized Transfer.

## Security Boundary

The slot arena and all transformations are fixed trusted project code. The
path does not discover allocators or backend plugins, call device allocation
APIs, access devices, map files or memory, expose addresses or runtime handles,
load dynamic libraries, execute generated artifacts, use JIT or subprocesses,
access a network, or create an unbounded pool.

The public trace and report omit tensor contents, tensor-value digests, storage
identities, object identities, pointers, addresses, handles, device
identifiers, host paths, commands, source, generated code, and backend
artifacts.

## Non-Claims

This proof does not establish:

- physical `device_sram` or `host_ram` residency;
- native device allocation, transfer, layout conversion, or kernel execution;
- allocator or backend plugins, memory mapping, handles, or pointers;
- direct kernel writes into planned storage or zero-copy execution;
- total process high-water memory, fragmentation, latency, throughput, energy,
  or native performance parity;
- arbitrary layouts, tiles, strides, dtypes, shapes, or graph families.

Default-path or Runtime Evidence Gate promotion requires a separate migration
decision with unchanged security and claim boundaries.
