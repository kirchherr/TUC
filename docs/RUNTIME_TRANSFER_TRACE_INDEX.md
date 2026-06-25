# Runtime Transfer Trace Index v0

Runtime Transfer Trace Index v0 links planned runtime-transfer evidence to
concrete runtime producer and consumer trace steps.

This keeps transfer review aligned with observed execution order without
claiming that TUC has performed a native device transfer, created an allocation
handle, accessed a device, or measured real transfer latency.

## Contract

- Schema:
  `schemas/runtime_transfer_trace_index_report.v0.schema.json`
- Example: `examples/runtime_transfer_trace_index.py`
- Golden:
  `tests/golden/runtime_transfer_trace_index/current_report.json`
- Contract: `runtime_transfer_trace_index.data_only.v0`
- Scope: `planned_transfer_trace_alignment_only`
- Trace materialization policy:
  `transfer_not_materialized_as_runtime_step`
- Execution policy: `does_not_execute_transfers`
- Cost claim: `planning_estimate_not_measurement`
- Residency claim: `not_physical_residency_evidence`
- Raw value policy: `omitted_by_policy`

## What It Records

For each planned transfer, the trace index records:

- transfer ID and tensor name;
- producer and consumer operation names;
- producer and consumer operation kinds;
- producer and consumer trace-step indexes;
- producer and consumer planned/executor backends;
- producer output tensors and consumer input tensors;
- source and target memory domains;
- source and target layouts;
- planned byte count and deterministic planning-cost estimates;
- source transfer status and trace alignment status.

The current golden indexes the systolic backend-equivalence candidate slice:

```text
projection step 0
  systolic-sim / blocked / device_sram
  produces projection

planned transfer
  projection device_sram -> host_ram
  transfer_not_materialized_as_runtime_step

activation step 1
  reference-cpu / row_major / host_ram
  consumes projection
```

Runtime Evidence Matrix and Runtime Evidence Gate now require this index as
`runtime_transfer_trace_index_systolic` for the systolic backend-equivalence
proof slice.

## What It Proves

- the planned transfer edge is aligned to an observed producer-consumer runtime
  edge;
- the producer step precedes the consumer step;
- trace backend placement agrees with Runtime Transfer Evidence;
- transfer planning is visible at the execution-review boundary.

## What It Does Not Prove

- real device transfer execution;
- physical memory residency;
- allocation handles, stream behavior, memory addresses, or device pointers;
- native performance, bandwidth, cache behavior, or vendor-library parity;
- tensor contents or tensor-value digests.

## Security Boundary

The report remains metadata-only. It must not serialize tensor contents,
tensor-value digests, runtime handles, allocation handles, device identifiers,
host paths, commands, environment variables, backend artifacts, generated code,
plugin entrypoints, or executable surfaces.

The report fails closed when the execution trace does not match the graph,
producer, consumer, tensor edge, backend placement, or operation order recorded
by Runtime Transfer Evidence.
