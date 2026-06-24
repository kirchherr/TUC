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
- Second-slice golden:
  `tests/golden/runtime_layout_conversion_evidence/second_slice_report.json`
- RFC: `rfcs/0212-runtime-layout-conversion-evidence.md`
- Contract: `runtime_layout_conversion_evidence.data_only.v0`
- Scope: `planned_logical_layout_only`
- Execution policy: `does_not_execute_conversions`
- Residency claim status: `not_physical_residency_evidence`
- Gate-readiness schema:
  `schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json`
- Digest-binding schema:
  `schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json`

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

The second-slice golden records an independent `blocked -> row_major`
transition between `score_projection` and `reduce_scores` in the
`runtime_layout_conversion_reduction_slice` graph.

## Matrix Inventory

Runtime Evidence Matrix v0 inventories this report as
`runtime_layout_conversion_evidence_mixed` on the
`runtime_mixed_backend_equivalence` graph. It is optional review evidence for
now: the mixed graph's required artifact kinds remain `backend_equivalence`,
`runtime_planning_explanation`, and `runtime_hs_ir_plan_alignment` until layout
conversion evidence is stable enough to become gate-required evidence.

[Runtime Layout Conversion Gate Readiness](RUNTIME_LAYOUT_CONVERSION_GATE_READINESS.md)
now records that the current promotion prerequisites are ready. The final
readiness blocker is satisfied by
[Runtime Layout Conversion Digest Binding](RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING.md),
which connects the layout-conversion metadata digest to HS-IR alignment and
Tensor Store record metadata for the mixed slice.

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
