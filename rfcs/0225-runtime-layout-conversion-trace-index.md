# RFC 0225: Runtime Layout Conversion Trace Index

## Status

Accepted for prototype evidence.

## Context

Runtime Layout Conversion Evidence makes planned `blocked -> row_major`
transitions visible, and Runtime Execution Trace records trusted prototype
operation execution. Reviewers still need one explicit bridge between those two
facts:

```text
producer step
  -> planned layout conversion edge
  -> consumer step
```

Without that bridge, a layout transition can be known from the plan but remain
less obvious in the execution-review story.

## Decision

Add Runtime Layout Conversion Trace Index v0 as a deterministic, metadata-only
artifact:

- schema:
  `schemas/runtime_layout_conversion_trace_index_report.v0.schema.json`
- example: `examples/runtime_layout_conversion_trace_index.py`
- golden:
  `tests/golden/runtime_layout_conversion_trace_index/current_report.json`
- contract: `runtime_layout_conversion_trace_index.data_only.v0`

The report binds a passing Runtime Layout Conversion Evidence report to a
Runtime Execution Trace by digest and records, per conversion, the producer
step index, consumer step index, operation kinds, planned/executor backends,
layouts, memory domains, planned byte count, and planner reason.

## Security Boundary

The trace index does not execute conversions and does not introduce converter
plugins, generated code, dynamic imports, subprocesses, allocation handles,
runtime handles, device identifiers, paths, or tensor values.

The trace materialization policy is:

```text
conversion_not_materialized_as_runtime_step
```

This is intentional. The artifact shows where a conversion is required in the
logical runtime trace without claiming an executable converter path.

## Acceptance Criteria

- The report passes with exactly one current mixed-backend conversion.
- The conversion aligns `projection` step 0 to `normalize` step 1.
- The producer backend is `systolic-sim`.
- The consumer backend is `vector-sim`.
- The source layout is `blocked`.
- The target layout is `row_major`.
- The report binds both source layout-conversion evidence and execution trace by
  SHA-256 digest.
- CI runs the example and tests the golden report.

## Non-Claims

This RFC does not claim:

- physical memory residency;
- real layout conversion execution;
- native device transfer;
- native performance;
- hardware certification;
- vendor compiler replacement.
