# RFC 0148: Runtime HS-IR Plan Alignment

## Status

Accepted.

## Context

TUC now has executable trusted prototype backends, mixed accelerator
equivalence evidence, and a portfolio-level proof that `systolic-sim` and
`vector-sim` can compose behind the same hardware-independent compute intent.

One gap remained: reviewers could inspect HS-IR, inspect the `PartitionPlan`,
and inspect the runtime trace, but there was no single deterministic artifact
that proved those three layers still agreed on the same operation/backend/layout
choices.

That matters because HS-IR is the first layer where backend-specific facts are
allowed. If HS-IR drifts from the accepted plan or the trusted trace, TUC could
appear to support a portable execution path while the practical proof is really
split across inconsistent evidence.

## Decision

Introduce Runtime HS-IR Plan Alignment v0.

The report is a schema-versioned, data-only evidence artifact with schema:

```text
schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json
```

The deterministic example is:

```text
examples/runtime_hs_ir_plan_alignment.py
```

The deterministic golden is:

```text
tests/golden/runtime_hs_ir_plan_alignment/mixed_report.json
```

The first slice binds the mixed accelerator graph:

```text
runtime_mixed_backend_equivalence
```

It verifies that HS-IR backend assignments, produced layouts, runtime-transfer
summary totals, the accepted `PartitionPlan`, and the
`RuntimeExecutionTrace` agree for:

```text
systolic-sim -> vector-sim -> vector-sim -> vector-sim
```

## Security Boundary

The artifact is metadata only. It does not include raw tensor values,
tensor-value digests, runtime handles, host paths, command lines, device
identifiers, plugin entrypoints, backend artifacts, generated code, source
text, raw benchmark output, or raw timing samples.

It does not discover plugins, import backend modules, load dynamic libraries,
access devices, spawn subprocesses, touch the network, run JIT code, execute
generated artifacts, resolve filesystem paths, or authorize native execution.

The report is derived from already validated in-memory HS-IR, `PartitionPlan`,
and `RuntimeExecutionResult` objects. The issue list is derived from the same
reported values and cannot be forged away.

## Consequences

HS-IR is now connected to practical execution evidence instead of only being a
lowered artifact. Future changes to backend assignment, produced-layout
metadata, runtime transfer summaries, trusted executor support, or trace
construction must keep this alignment report, schema, golden, docs, and tests
consistent.

This strengthens the current runtime proof without adding a parser, plugin
surface, device-access path, native backend path, or performance claim.
