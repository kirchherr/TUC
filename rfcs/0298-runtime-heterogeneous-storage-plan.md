# RFC 0298: Runtime Heterogeneous Storage Plan

- Status: Accepted
- Date: 2026-09-03
- Owners: TUC maintainers

## Summary

Add a data-only runtime report that derives physical storage requirements,
transfer-staging lifetimes, and conservative reusable slots from a validated
`ComputeGraph` and `PartitionPlan`.

## Motivation

Runtime Materialized Allocation proves real slot reuse for an all-host,
row-major slice. Runtime Materialized Layout Conversion and Runtime
Materialized Transfer prove one mixed-domain conversion and copy. Joining
those paths without first modeling staging lifetimes and physical layout sizes
would undercount memory and could permit premature reuse at a copy boundary.

The roadmap therefore requires an explicit planning layer before any
mixed-domain allocator execution is admitted.

## Decision

Runtime Heterogeneous Storage Plan v0:

1. validates Buffer Lifetime, Transfer Evidence, and Layout Conversion
   Evidence before deriving storage;
2. uses four ordered events per operation plus `graph_end`;
3. models produced values, layout staging, and transfer-target staging as
   separate storage roles;
4. keeps copy source and destination lifetimes overlapping at conversion and
   transfer events;
5. sizes `row_major` storage by logical shape;
6. sizes rank-2 `blocked` storage using fixed 2x2 tiles and explicit padding;
7. shares slots only across identical role, domain, layout, dtype, physical
   shape, tile shape, and byte size with strictly non-overlapping lifetimes;
8. records per-domain peak live physical bytes and reserved slot bytes;
9. emits a closed, bounded, metadata-only report.

The public contract is closed by
`schemas/runtime_heterogeneous_storage_plan_report.v0.schema.json`.

The report binds Transfer Evidence and Layout Conversion Evidence plan digests
as separate fields because those accepted artifacts hash different scoped
projections. No equality claim is made across those projections.

## Proof Slice

The canonical graph contains two sequential 3x3 `matmul -> relu` slices:

```text
systolic-sim / device_sram / blocked
  -> layout staging / device_sram / row_major
  -> transfer staging / host_ram / row_major
  -> reference-cpu consumer
```

For each blocked 3x3 value, physical 2x2 tiling creates 16 elements from nine
logical elements. The two slices do not overlap, allowing one slot to be reused
within each of the three storage roles.

## Security

- The planner is pure project code and does not call an allocator or backend.
- Unsupported layouts and incomplete movement relationships fail closed.
- Source evidence is rebuilt through existing validated report builders.
- Tensor dimensions, physical elements, lifetime/slot counts, reserved bytes,
  metadata fields, and output size are bounded.
- Reuse requires exact storage-contract equality and strict lifetime
  separation.
- External artifacts, plugins, dynamic loading, JIT, subprocesses, devices,
  files, network access, pointers, addresses, and handles remain blocked.
- Raw tensor values and tensor-value digests are not serialized.

## Alternatives Rejected

### Reuse logical byte counts for blocked storage

Rejected because a 3x3 logical tensor occupies a padded 4x4 physical tile
surface under the trusted 2x2 blocked representation.

### Treat conversion and transfer as zero-duration annotations

Rejected because source and destination buffers must coexist at copy
boundaries. Zero-duration modeling can hide unsafe early reuse.

### Reuse slots across staging roles

Rejected for v0. Role isolation is conservative and keeps future materialized
execution easier to audit.

### Materialize mixed-domain allocation immediately

Rejected until this data-only model is accepted and explicit promotion
criteria bind it to allocation execution.

## Consequences

TUC gains the missing physical memory model between heterogeneous planning and
materialized allocation. The report remains simulator planning evidence and
does not prove native memory allocation, device residency, transfer timing, or
performance.
