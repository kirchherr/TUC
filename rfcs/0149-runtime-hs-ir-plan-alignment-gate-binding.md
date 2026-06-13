# RFC 0149: Runtime HS-IR Plan Alignment Gate Binding

## Status

Accepted.

## Context

RFC 0148 introduced Runtime HS-IR Plan Alignment as a deterministic data-only
report. That proved HS-IR backend/layout facts, the accepted `PartitionPlan`,
and the observed `RuntimeExecutionTrace` agree for the mixed accelerator proof
slice.

The report still needed to become merge-relevant. If it remained only a
standalone example, HS-IR/runtime-plan drift could be missed by the CI-facing
Runtime Evidence Gate.

## Decision

Add `runtime_hs_ir_plan_alignment` as a Runtime Evidence Matrix artifact kind.

The `runtime_mixed_backend_equivalence` graph now requires both:

```text
backend_equivalence
runtime_hs_ir_plan_alignment
```

The accepted artifact IDs are:

```text
runtime_backend_equivalence_mixed
runtime_hs_ir_plan_alignment_mixed
```

Runtime Evidence Gate now:

- builds `examples/runtime_hs_ir_plan_alignment.py`
- requires the report to pass
- binds the report graph to `runtime_mixed_backend_equivalence`
- compares its backend sequence with the mixed accelerator candidate run
- checks the exact Matrix artifact ID through Runtime Evidence Gate Matrix
  Coverage

## Security Boundary

This binding does not add parser behavior, plugin discovery, dynamic imports,
device access, native execution, JIT execution, generated artifact execution,
filesystem path resolution, network access, subprocess execution, raw tensor
serialization, raw timing samples, or benchmark output.

It compares bounded identifiers, backend sequences, step counts, pass status,
raw-value policy, and Matrix artifact IDs already present in typed in-memory
reports.

## Consequences

The mixed accelerator proof slice is now accepted only when its backend
equivalence evidence and HS-IR/runtime-plan alignment evidence are both present
and exact. Future changes to mixed accelerator planning, HS-IR lowering,
runtime trace construction, or Runtime Evidence Matrix coverage must update the
alignment report, Matrix entry, Gate binding, coverage golden, and docs
together.
