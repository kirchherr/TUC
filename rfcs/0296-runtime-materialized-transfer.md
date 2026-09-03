# RFC 0296: Runtime Materialized Transfer

- Status: Accepted
- Scope: Trusted prototype runtime
- Decision date: 2026-09-02

## Context

TUC already records planned cross-domain transfers, aligns them to producer and
consumer trace steps, replay-checks their metadata, and binds that evidence to
Backend Equivalence. Those accepted artifacts intentionally say
`transfer_not_materialized_as_runtime_step`.

RFC 0295 added an opt-in runtime path for one real simulator layout conversion.
The next practical gap is the domain edge itself: no owned consumer buffer is
created to represent the planned movement from `device_sram` to `host_ram`.

## Decision

Add `execute_graph_with_materialized_data_movement()` as a separate opt-in
runtime path. It materializes supported layout conversions and then executes
one fixed trusted simulator transfer primitive:

```text
device_sram -> host_ram
layout_ready_then_domain_copy
```

The implementation must:

1. preflight all transfer and conversion edges before any graph kernel runs;
2. bind every edge to graph producer, consumer, assignments, layouts, shape,
   dtype, and planned bytes;
3. require an exact conversion edge when source and target layouts differ;
4. limit v0 to `device_sram -> host_ram` and 2,000,000 logical elements;
5. perform a new contiguous in-process NumPy copy;
6. reject aliasing and require exact finite logical values;
7. make the copied consumer input read-only;
8. emit a typed transfer execution step;
9. preserve all existing executor paths and legacy evidence unchanged.

Add a closed metadata-only report that binds the executed transfer trace to the
materialized layout report, candidate output metadata, and passing Backend
Equivalence. The contract is fixed by
`schemas/runtime_materialized_transfer_report.v0.schema.json` and
`tests/golden/runtime_materialized_transfer/current_report.json`.

## Byte Semantics

`RuntimeTransferEdge.bytes_moved` remains the graph-level planning size based
on the declared tensor dtype. The report separately records the internal
runtime copy size. For the current `(2, 2)` `float32` projection these are 16
planned bytes and 32 `float64` runtime bytes.

No timing from the copy is measured or accepted as performance evidence.

## Compatibility

`execute_graph()` remains the default. Its Transfer Evidence, Trace Index,
Replay Verifier, Backend Equivalence Transfer Binding, Runtime Evidence
Matrix, and Runtime Evidence Gate retain their historical non-materialized
meaning.

`execute_graph_with_materialized_layouts()` also remains layout-only. Promotion
of the new path into either existing API or the general Runtime Evidence Gate
requires a separate migration decision.

## Security

The primitive is fixed in-repository code and admits no external executors,
plugins, artifacts, paths, commands, devices, dynamic libraries, subprocesses,
JIT, network, pointers, or allocation handles. All plan relationships and
resource limits are validated before values are copied or kernels run.

The public report contains metadata digests and bounded identifiers only. It
omits tensor contents, tensor-value digests, handles, addresses, device IDs,
source, generated code, and native artifacts.

## Alternatives Rejected

- Reinterpret existing Transfer Trace Evidence as execution: rejected because
  it would make an accepted non-materialized claim false.
- Change `execute_graph()` directly: rejected because it would silently alter
  stable trace and golden semantics.
- Use a view or shared array: rejected because it would not prove an owned
  transfer buffer and could permit mutation through aliasing.
- Add native DMA or device APIs: rejected because TUC has not admitted their
  trust, lifecycle, synchronization, or residency surfaces.
- Support every memory-domain pair immediately: rejected to keep the first
  executable transfer claim bounded and reviewable.

## Consequences

TUC gains a practical end-to-end data-movement proof. One plan now causes a
real blocked-layout transformation, a real distinct buffer copy, trusted
consumer execution, and reference-equivalent terminal semantics.

The proof remains simulator-only. Memory-domain names describe the accepted
plan and execution record, not observed physical hardware residency.
