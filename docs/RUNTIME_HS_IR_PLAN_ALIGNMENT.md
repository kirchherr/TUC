# Runtime HS-IR Plan Alignment

Runtime HS-IR Plan Alignment v0 is a schema-versioned, data-only evidence
report that binds HS-IR backend/layout decisions to the accepted
`PartitionPlan` and the observed `RuntimeExecutionTrace`.

It exists to make the practical execution path inspectable:

```text
HS-IR operation facts -> PartitionPlan assignment -> Runtime trace step
```

## Contract

- Report schema:
  `schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json`
- Report schema version:
  `tuc.runtime_hs_ir_plan_alignment_report.v0`
- Evidence contract:
  `runtime_hs_ir_plan_alignment.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Trusted executor registry: `trusted_runtime_executor_registry.v0`
- Raw value policy: `omitted_by_policy`
- Example: `examples/runtime_hs_ir_plan_alignment.py`
- Golden:
  `tests/golden/runtime_hs_ir_plan_alignment/mixed_report.json`

## Current Slice

The current deterministic slice uses the mixed accelerator graph:

```text
runtime_mixed_backend_equivalence
```

It checks four operations:

- `projection`: `matmul` on `systolic-sim`, producing `blocked`
- `normalize`: `softmax` on `vector-sim`, producing `row_major`
- `sum_rows`: `reduction` on `vector-sim`, producing `row_major`
- `activation`: `elementwise` on `vector-sim`, producing `row_major`

The accepted backend sequence is:

```text
systolic-sim -> vector-sim -> vector-sim -> vector-sim
```

The report records the single current layout conversion as metadata:

```text
blocked -> row_major, 24 bytes
```

## What It Checks

The report fails closed when any of these bindings drift:

- HS-IR graph name, PartitionPlan graph name, and execution trace graph name.
- HS-IR backend sequence and PartitionPlan backend sequence.
- PartitionPlan backend sequence and execution trace backend sequence.
- HS-IR runtime-transfer summary counts and PartitionPlan movement totals.
- Per-operation produced layouts in HS-IR and PartitionPlan.
- Per-operation trusted executor support for the assigned backend and operation
  kind.

The report also derives all issues from the reported values. Review code cannot
silently erase a failing issue list and still construct a valid report.

## Security Boundary

Runtime HS-IR Plan Alignment is metadata only. It does not include tensor
values, tensor-value digests, runtime handles, host paths, device identifiers,
commands, environment variables, generated code, plugin entrypoints, backend
artifacts, raw timing samples, raw benchmark output, or source text.

It does not execute code, discover plugins, import backend modules, access
devices, spawn subprocesses, touch the network, run JIT code, load dynamic
libraries, read manifests, resolve paths, or authorize native execution.

The report is built only from already validated in-memory HS-IR,
`PartitionPlan`, and `RuntimeExecutionResult` objects.

## Review Meaning

This evidence does not prove native performance. It proves that the current
runtime execution path is internally aligned: the hardware-specific IR layer,
the runtime plan, and the trusted execution trace all describe the same
operation/backend/layout decisions.

That makes future backend and performance work harder to fake: if HS-IR,
planning, or execution drifts, reviewers get a deterministic JSON failure
instead of a narrative claim.
