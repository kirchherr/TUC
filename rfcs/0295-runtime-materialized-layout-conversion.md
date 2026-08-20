# RFC 0295: Runtime Materialized Layout Conversion

- Status: Accepted
- Scope: Trusted prototype runtime
- Decision date: 2026-08-20

## Context

TUC already records planned layout transitions, binds them to producer and
consumer trace indexes, replay-checks their metadata, and connects them to
Backend Equivalence. Those artifacts intentionally preserve the
`conversion_not_materialized_as_runtime_step` boundary.

The remaining simulator-level gap is practical: no runtime path changes a
buffer representation before the consumer executes. Replacing the existing
executor behavior in place would invalidate the meaning of accepted legacy
evidence. Opening an external converter or native backend surface would be
premature and materially increase attack surface.

## Decision

Add an opt-in trusted runtime API,
`execute_graph_with_materialized_layouts()`, backed by one fixed in-process
converter:

```text
blocked rank-2 tensor -> fixed padded 2 x 2 tiled storage -> row-major tensor
```

The converter:

1. preflights every planned conversion before any graph kernel executes;
2. accepts only `blocked -> row_major`, rank 2, and the fixed `2 x 2` tile;
3. checks tensor, producer, consumer, layout, graph dtype, shape, and planned
   byte linkage;
4. bounds physical storage before allocation;
5. packs into an independent contiguous blocked buffer;
6. unpacks into an independent contiguous row-major buffer;
7. requires exact logical-value equality;
8. marks the consumer input read-only;
9. emits a typed conversion trace step.

Add a metadata-only report that binds the accepted plan and conversion trace to
a passing Runtime Backend Equivalence report. The binding verifies candidate
backend sequence, output names and metadata digest, operation trace count, and
tensor record count, and records a digest of the materialized trace itself. The
schema and golden fix the current mixed simulator proof contract:
`schemas/runtime_materialized_layout_conversion_report.v0.schema.json` and
`tests/golden/runtime_materialized_layout_conversion/current_report.json`.

## Byte Semantics

`LayoutConversionCost.bytes_converted` remains a graph-level planning estimate
based on the tensor's declared dtype. Runtime buffer accounting is separate.
The current graph declares `float32`, while the trusted prototype executor uses
`float64`. The report therefore records planned bytes, logical runtime bytes,
physical runtime bytes, padding, and temporary storage independently.

## Compatibility

`execute_graph()` is unchanged. Existing Layout Conversion Evidence, Trace
Index, Replay Verifier, Backend Equivalence Layout Binding, Runtime Evidence
Matrix, and Runtime Evidence Gate artifacts keep their historical non-
materialized meaning.

The new proof is additive and opt-in. A future default-path or gate promotion
requires a new RFC and migration plan.

## Security

The implementation admits no external code, plugins, artifacts, paths,
commands, dynamic loading, devices, subprocesses, JIT, or network access. All
plan relationships are validated before runtime kernels execute. Physical
element count is bounded before the padded buffer is allocated. Inputs and
outputs must be finite NumPy `float64` arrays with exact declared shapes.

The public report is closed-schema metadata and omits raw values, runtime
handles, device identifiers, source, generated code, and native artifacts.

## Alternatives Rejected

- Change `execute_graph()` directly: rejected because accepted evidence would
  silently change meaning.
- Treat planned metadata as materialized execution: rejected because it would
  overclaim what the runtime performed.
- Add an executable backend plugin converter: rejected because TUC has not
  admitted that trust surface.
- Add native or device conversion now: rejected because no native execution,
  residency, ABI, or security evidence exists yet.
- Support arbitrary layouts and tile shapes: rejected to preserve a bounded,
  reviewable first proof.

## Consequences

TUC gains a practical heterogeneous runtime proof in which a planned layout
edge causes a real simulator buffer transformation and terminal semantics remain
equivalent. It also gains explicit accounting for the graph/runtime dtype
difference.

The proof remains simulator-only. The producer's canonical Tensor Store value
is logical NumPy data; the converter reconstructs the planned blocked
representation at the boundary. Native device-produced layouts remain future
work.
