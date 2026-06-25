# Runtime Layout Conversion Trace Index v0

Runtime Layout Conversion Trace Index v0 links planned layout-conversion
evidence to concrete runtime producer and consumer trace steps.

This keeps layout conversion reviewable without pretending that TUC already has
a real converter, runtime allocation, device transfer, or physical residency
proof.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_trace_index_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_trace_index.py`
- Golden:
  `tests/golden/runtime_layout_conversion_trace_index/current_report.json`
- RFC: `rfcs/0225-runtime-layout-conversion-trace-index.md`
- Contract: `runtime_layout_conversion_trace_index.data_only.v0`
- Scope: `planned_conversion_trace_alignment_only`
- Trace materialization policy:
  `conversion_not_materialized_as_runtime_step`
- Execution policy: `does_not_execute_conversions`
- Raw value policy: `omitted_by_policy`

## What It Records

For each planned conversion, the trace index records:

- conversion ID and tensor name;
- producer and consumer operation names;
- producer and consumer operation kinds;
- producer and consumer trace-step indexes;
- producer and consumer planned/executor backends;
- producer output tensors and consumer input tensors;
- source and target layouts;
- source and target memory domains;
- planned byte count and planner reason.

The current golden indexes the mixed backend-equivalence slice:

```text
projection step 0
  systolic-sim / blocked / device_sram
  produces projection

planned conversion
  projection blocked -> row_major
  conversion_not_materialized_as_runtime_step

normalize step 1
  vector-sim / row_major / device_sram
  consumes projection
```

## Matrix And Gate Binding

The current Runtime Evidence Matrix requires this report as
`runtime_layout_conversion_trace_index_mixed` on the
`runtime_mixed_backend_equivalence` graph, alongside Backend Equivalence,
Runtime Planning Explanation, Runtime HS-IR Plan Alignment, and Runtime Layout
Conversion Evidence.

Runtime Evidence Gate accepts the report only when it is bound to the same graph,
partition-plan digest, layout-conversion evidence digest, conversion count, and
mixed candidate trace-step count evaluated by the gate invocation. Runtime
Evidence Gate Matrix Coverage also audits the exact
`runtime_layout_conversion_trace_index_mixed` artifact ID.

## What It Proves

- the planned layout transition is aligned to an observed producer-consumer
  runtime edge;
- the producer step precedes the consumer step;
- trace backend placement agrees with the layout-conversion evidence;
- layout conversion is visible at the execution-review boundary.

## What It Does Not Prove

- real layout converter execution;
- native device transfer;
- physical memory residency;
- allocation handles, stream behavior, or device pointers;
- native performance, cache behavior, tensor-core use, or vendor-library parity.

## Security Boundary

The report remains metadata-only. It must not serialize tensor contents,
tensor-value digests, runtime handles, allocation handles, device identifiers,
host paths, commands, environment variables, backend artifacts, generated code,
plugin entrypoints, or executable surfaces.

The report fails closed when the execution trace does not match the graph,
producer, consumer, tensor edge, backend placement, or operation order recorded
by Runtime Layout Conversion Evidence.
