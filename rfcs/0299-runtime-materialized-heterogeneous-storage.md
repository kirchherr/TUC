# RFC 0299: Runtime Materialized Heterogeneous Storage

- Status: Accepted
- Date: 2026-09-04
- Owners: TUC maintainers

## Summary

Add a separate opt-in trusted simulator executor that binds Runtime
Heterogeneous Storage Plan v0 to actual bounded storage for produced values,
layout staging, and transfer-target staging.

## Motivation

RFC 0298 establishes physical layout sizes, movement-boundary lifetimes, and
conservative reusable slots as data-only evidence. The earlier materialized
proofs execute allocation, layout conversion, or transfer independently, but
none demonstrates that the joined heterogeneous plan governs all of those
storage roles during one execution.

The roadmap therefore needs one bounded vertical proof before considering any
default-path promotion, native allocator, or device-residency claim.

## Decision

Runtime Materialized Heterogeneous Storage v0:

1. remains a separate opt-in API and leaves `execute_graph()` unchanged;
2. rebuilds the supplied storage plan and requires byte-identical canonical
   evidence before input copying, slot allocation, or kernel execution;
3. preallocates exactly one private in-process NumPy array per planned slot;
4. materializes produced values, layout staging, and transfer-target staging
   through the plan's exact storage ids, roles, events, and slot generations;
5. writes rank-2 blocked values into fixed 2x2 padded physical storage and
   independently verifies zero padding and logical recovery;
6. performs layout conversion before a distinct transfer-target copy;
7. releases each storage generation at its planned final-use event;
8. permits slot reuse only after the previous generation's recorded release;
9. retains only external inputs and immutable terminal output snapshots;
10. binds the run to Reference Correctness, Backend Equivalence, Materialized
    Layout Conversion, and Materialized Transfer;
11. emits a closed, bounded, metadata-only report.

The public contract is closed by
`schemas/runtime_materialized_heterogeneous_storage_report.v0.schema.json`.

## Proof Slice

The canonical graph contains two sequential 3x3 `matmul -> relu` slices:

```text
systolic-sim / simulated device_sram / blocked
  -> layout staging / simulated device_sram / row_major
  -> transfer staging / simulated host_ram / row_major
  -> reference-cpu consumer
```

Eight lifetimes execute through five slots. The produced-blocked,
layout-staging, and transfer-target slots each receive a second generation
only after the first slice releases its matching storage role. Both terminal
outputs remain in exclusive slots until graph end.

The plan reserves 208 `float32` bytes instead of 344 bytes without reuse. The
private `float64` simulator arena reserves 416 bytes instead of 688 bytes,
executing three reuse events and saving 272 runtime bytes. These are persistent
slot-capacity facts, not total-process memory or performance measurements.

## Security

- The complete graph, input, and canonical-plan preflight finishes before the
  first slot allocation or kernel execution.
- The executor uses only fixed trusted project backend functions and fixed
  layout/copy operations.
- Per-slot and aggregate input storage are bounded to 32 MiB, in addition to
  the existing graph, physical-element, lifetime, slot, and report limits.
- Unsupported dtypes, layouts, tile shapes, incomplete staging chains, stale
  evidence, forged sources, early reuse, and non-finite values fail closed.
- Reuse requires exact plan identity and an observed predecessor release.
- Plugins, device access, external allocators, memory mapping, dynamic loading,
  JIT, subprocesses, generated artifacts, network access, addresses, handles,
  and unbounded pools remain blocked.
- Raw values, tensor-value digests, object identities, storage identities,
  pointers, addresses, handles, paths, commands, and artifacts are not
  serialized.

## Alternatives Rejected

### Join earlier materialized reports without one executor

Rejected because independent proofs do not show that a single canonical plan
controls storage ordering, lifetime release, and reuse during one run.

### Trust the caller-supplied storage plan after shallow validation

Rejected because stale or forged evidence could alter slot sizes, source
relationships, or reuse timing. The plan is rebuilt and compared canonically.

### Reuse one logical row-major array for all movement stages

Rejected because it would erase physical blocked padding and alias the layout
and transfer boundaries that the proof is intended to execute.

### Promote the path into the default executor

Rejected for v0. Default behavior and central gate semantics require a
separate migration decision after the opt-in evidence has remained stable.

### Call native allocator or device APIs

Rejected because the current claim concerns plan-governed simulator storage,
not physical residency, native execution, or performance.

## Consequences

TUC gains a practical end-to-end bridge from heterogeneous storage planning to
bounded materialized execution. The result strengthens the universal-compute
research claim by showing that neutral intent can retain observable semantics
while one inspectable plan controls different simulated layouts and memory
domains.

The proof remains deliberately bounded. It does not establish native memory
allocation, physical device residency, real transfer timing, arbitrary layout
semantics, or performance parity.
