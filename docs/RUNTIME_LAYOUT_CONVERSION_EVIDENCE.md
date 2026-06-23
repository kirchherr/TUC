# Runtime Layout Conversion Evidence v0

Runtime Layout Conversion Evidence v0 records explicit planned layout
transitions from an accepted `PartitionPlan`.

This is a data-only evidence artifact. It does not perform layout conversion,
does not execute native code, does not allocate memory, and does not prove
physical device residency.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_evidence_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_evidence.py`
- Golden:
  `tests/golden/runtime_layout_conversion_evidence/current_report.json`
- RFC: `rfcs/0212-runtime-layout-conversion-evidence.md`
- Contract: `runtime_layout_conversion_evidence.data_only.v0`
- Scope: `planned_logical_layout_only`
- Execution policy: `does_not_execute_conversions`
- Residency claim status: `not_physical_residency_evidence`

## What It Records

For each planned transition, the report records:

- conversion ID;
- tensor name;
- source and target operations;
- source and target backend names;
- source and target memory domains;
- source and target layouts;
- planned byte count;
- planner reason;
- source value-record ID and consumer input ID.

The first current golden records the `blocked -> row_major` transition between
the `systolic-sim` projection and the `vector-sim` consumer in the mixed
backend-equivalence proof slice.

## What It Proves

- layout transitions are visible in review artifacts instead of hidden inside a
  backend;
- transition records are bound to an accepted `PartitionPlan` digest;
- producer, consumer, source layout, target layout, and byte count agree with
  the compute graph and plan;
- the report remains metadata-only and value-free.

## What It Does Not Prove

- real layout-converter execution;
- native device execution;
- physical memory residency;
- allocation handles, memory addresses, stream behavior, or device pointers;
- native performance, cache behavior, tensor-core use, or vendor-library
  parity.

## Security Boundary

The report must not contain raw tensor values, tensor-value digests, runtime
handles, allocation handles, device identifiers, host paths, command lines,
environment variables, backend artifacts, generated code, plugin entrypoints,
raw benchmark samples, or executable surfaces.

Unknown layouts, mismatched producers, mismatched consumer inputs, stale byte
counts, and hidden backend-local transitions must fail closed before this
artifact can become required Runtime Evidence Matrix or Runtime Evidence Gate
evidence.
