# RFC 0212: Runtime Layout Conversion Evidence

## Status

Accepted

## Summary

Add a data-only Runtime Layout Conversion Evidence v0 artifact that records
explicit planned layout transitions before TUC accepts any runtime layout
converter, native allocation behavior, or real device-residency claim.

This RFC does not implement layout conversion. It defines the proof boundary for
making layout transitions reviewable.

## Motivation

TUC already records planned layouts, produced layouts, movement accounting, and
layout-conversion costs in runtime plans and related evidence. That is enough
to explain why a plan is accepted, but it is not yet a standalone proof that a
layout transition was explicitly traced from producer to consumer.

Without explicit layout-conversion evidence, future backend work could hide a
hardware-specific layout transformation inside a backend, allocator, or native
adapter. That would weaken the Universal Compute claim and create a leaky
abstraction boundary.

## Goals

- Make every accepted layout transition visible as typed, bounded, data-only
  evidence.
- Preserve HAC-IR as compute intent and keep layout-transition facts in runtime
  or HS-IR evidence.
- Bind each transition to the accepted `PartitionPlan`, runtime value metadata,
  and HS-IR plan alignment where applicable.
- Fail closed on unknown layouts, missing plan edges, impossible transitions,
  or raw-value leakage.
- Keep the artifact independent of native devices, allocation handles, plugin
  execution, and generated-code execution.

## Non-Goals

- Implement a real layout converter.
- Add native device execution.
- Prove physical memory residency.
- Add allocation handles, device pointers, streams, kernels, or memory pools.
- Optimize layout choices.
- Claim native performance parity.
- Add a source parser shortcut or backend plugin execution path.

## Proposal

Introduce `RuntimeLayoutConversionEvidence` report v0 with schema
`schemas/runtime_layout_conversion_evidence_report.v0.schema.json`.

Each report contains:

- `schema_version`
- `graph_name`
- `evidence_contract`
- `source_partition_plan_digest`
- `conversion_scope`
- `execution_policy`
- `residency_claim_status`
- bounded `conversions`
- `conversion_metadata_digest`
- `raw_value_policy`
- `passed` and derived `issues`

Each conversion record contains only data such as:

- `conversion_id`
- `tensor_name`
- `source_operation`
- `target_operation`
- `from_backend`
- `to_backend`
- `from_memory_domain`
- `to_memory_domain`
- `from_layout`
- `to_layout`
- `planned_bytes`
- `planner_reason`
- `source_value_record_id`
- `consumer_input_id`
- `conversion_status`

Future HS-IR and Runtime Tensor Store digest bindings remain deferred until this
optional report is stable across another proof slice.

The artifact must not contain tensor values, tensor-value digests, runtime
handles, allocation handles, device identifiers, host paths, command lines,
environment variables, backend binaries, generated code, or plugin entrypoints.

## Invariants

- Layout names must come from the accepted layout vocabulary.
- Memory-domain names must come from the accepted memory-domain vocabulary.
- Every conversion record must correspond to an explicit `PartitionPlan`
  transfer or layout-conversion edge.
- Backend-local hidden conversions do not count as evidence.
- Conversion evidence is about planned logical layout, not physical residency.
- A backend that produces a layout another backend cannot consume must either
  produce an explicit conversion record or be rejected by planning.
- Record counts, string lengths, and metadata sizes must be bounded.

## Alternatives Considered

- Hide layout conversion inside backend execution.
  - Rejected because it makes leaky abstraction and wrong-code failures harder
    to review.
- Treat produced layout as enough evidence.
  - Rejected because produced layout explains a backend output, but not the
    transition required by a downstream consumer.
- Add a native converter first.
  - Rejected because native execution would expand the attack surface before
    the evidence contract is clear.

## Compatibility

This RFC adds report generation only. Existing runtime plans, tensor
store evidence, backend equivalence evidence, and HS-IR plan alignment remain
valid. It does not add a runtime layout converter.

The v0 implementation enters as optional inventory first. It should be bound
into Runtime Evidence Matrix and Runtime Evidence Gate only after schema,
goldens, and negative tests remain stable across another proof slice.

## Testing

The v0 implementation adds:

- schema validation for valid conversion evidence;
- golden report for a known planned layout transition;
- negative tests for unknown layouts;
- negative tests for missing `PartitionPlan` conversion edges;
- negative tests for raw tensor values or value digests;
- negative tests for device identifiers, handles, host paths, commands,
  generated code, and plugin entrypoints;
- Runtime Evidence Matrix inventory later, once the report becomes required evidence;
- Runtime Evidence Gate binding to exact artifact IDs.

## Open Questions

- Should the public name be `RuntimeLayoutConversionEvidence` or
  `RuntimeLayoutTransitionEvidence`?
- Should conversion evidence be required for all produced-layout changes or
  only for changes crossing backend or memory-domain boundaries?
- Should no-op layout preservation records be emitted, or should only actual
  transitions appear?
- Which existing graph should become the first required golden fixture?
