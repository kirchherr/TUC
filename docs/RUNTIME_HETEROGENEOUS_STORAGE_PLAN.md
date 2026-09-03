# Runtime Heterogeneous Storage Plan

## Status

Runtime Heterogeneous Storage Plan v0 is an implemented data-only proof. It
extends logical buffer lifetimes with explicit physical layout sizing,
layout-conversion staging, transfer-target staging, and conservative slot
reuse across a deterministic runtime event timeline.

Decision: `rfcs/0298-runtime-heterogeneous-storage-plan.md`.

## Claim

TUC can derive a bounded storage plan for one heterogeneous simulator graph
before allocation or execution:

```text
produced value in source layout
  -> layout-conversion staging
  -> transfer-target staging
  -> consumer execution
```

Every storage object has an explicit domain, layout, logical shape, physical
shape, byte count, first-live event, last-use event, role, and reusable slot.

## Event Model

Each graph operation owns four ordered events:

1. `layout_conversion`
2. `transfer`
3. `consumer_execution`
4. `output_produced`

One final `graph_end` event retains terminal outputs. Copy boundaries are
inclusive: the source and destination are both live at the conversion or
transfer event. This prevents a planner from reusing source storage before the
copy has completed.

## Layout-Specific Sizing

The v0 sizing policy is deliberately closed:

- `row_major`: physical shape equals logical shape;
- `blocked`: rank-2 tensors use fixed 2x2 tiles and pad each dimension upward.

The proof graph uses a logical `float32` 3x3 tensor:

```text
logical shape       = [3, 3]
logical elements    = 9
logical bytes       = 36
blocked shape       = [2, 2, 2, 2]
physical elements   = 16
padding elements    = 7
physical bytes      = 64
```

Unknown, vector, column-major, arbitrary blocked, and externally described
layouts fail closed because TUC does not yet have enough stride, tile, and
alignment semantics to size them honestly.

## Storage Roles

- `produced_value`: storage in the producer assignment's domain and layout;
- `layout_staging`: target-layout storage created before transfer or consume;
- `transfer_target_staging`: target-domain storage retained through consumer
  execution.

Slots are shared only when role, domain, layout, dtype, physical shape, tile
shape, and byte size match and all lifetimes are strictly non-overlapping.
Cross-role reuse is intentionally blocked in v0.

The two-slice 3x3 proof derives eight storage lifetimes and five slots. Three
slots are reused: one blocked produced-value slot, one source-domain layout
staging slot, and one target-domain transfer staging slot. The plan reserves
208 physical bytes instead of the 344 bytes required without reuse.

## Evidence Binding

The report binds canonical metadata from:

- Runtime Buffer Lifetime;
- Runtime Transfer Evidence;
- Runtime Layout Conversion Evidence;
- both source evidence projections of `PartitionPlan`.

Transfer Evidence and Layout Conversion Evidence currently hash different
closed projections of the same `PartitionPlan`. The new report preserves and
labels both digests separately. It does not imply that differently scoped
digests should be equal.

Evidence surfaces:

- planner: `src/tuc/runtime/heterogeneous_storage_plan.py`;
- example: `examples/runtime_heterogeneous_storage_plan.py`;
- schema: `schemas/runtime_heterogeneous_storage_plan_report.v0.schema.json`;
- golden: `tests/golden/runtime_heterogeneous_storage_plan/current_report.json`;
- tests: `tests/test_runtime_heterogeneous_storage_plan.py`.

Run:

```bash
python examples/runtime_heterogeneous_storage_plan.py
```

## Security Boundary

The planner accepts only validated in-memory `ComputeGraph` and
`PartitionPlan` objects. It allocates no runtime slot, touches no tensor value,
and executes no backend. Counts, text fields, tensor shapes, physical element
counts, reserved bytes, and serialized report bytes are bounded.

Runtime allocation, external allocator calls, allocator discovery, and memory
mapping are explicit blocked surfaces in addition to the standard trusted
executor restrictions.

The closed report omits tensor contents, tensor-value digests, runtime storage
identities, pointers, addresses, handles, device identifiers, paths, commands,
source, generated code, and backend artifacts.

## Non-Claims

This proof does not establish:

- runtime allocation or transfer execution;
- physical device residency, DMA, synchronization, or zero-copy behavior;
- arbitrary layouts, strides, alignment, bank conflicts, or fragmentation;
- allocator handles, plugins, pools, or native memory APIs;
- measured memory use, latency, bandwidth, energy, or performance parity.

The next execution step may consume this plan only through a separate RFC that
preserves complete preflight, hard resource limits, role isolation, and the
current simulator-only claim boundary.
