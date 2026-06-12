# RFC 0136: Runtime Backend Equivalence Evidence

## Status

Accepted.

## Context

TUC must avoid drifting into only meta-level proof artifacts. The Universal
Compute claim needs practical runtime evidence that a hardware-independent graph
can be executed under distinct placement choices while preserving observable
semantics.

The project already has a trusted Runtime Executor, `reference-cpu`,
`systolic-sim`, Runtime Tensor Store Evidence, and Runtime Evidence Gate
coverage. The next practical step is an explicit equivalence artifact comparing
two placements of the same graph.

## Decision

Add Runtime Backend Equivalence v0 as a schema-versioned, data-only evidence
report.

Schema coverage is in:

```text
schemas/runtime_backend_equivalence_report.v0.schema.json
```

The deterministic example is:

```text
examples/runtime_backend_equivalence.py
```

The golden report is:

```text
tests/golden/runtime_backend_equivalence/current_report.json
```

## Security Boundary

The report may compare arrays inside the trusted in-process Runtime Executor,
but serialized evidence remains metadata-only.

It must not serialize raw tensor values, tensor-value digests, runtime handles,
device identifiers, host paths, backend artifacts, commands, generated code,
plugin entrypoints, raw benchmark samples, or native execution claims.

## Consequences

TUC gains a practical proof slice showing that the same compute graph can run as
a `reference-cpu` baseline and as a `systolic-sim` placement while producing the
same terminal output metadata and matched output status.

This strengthens the hardware-independent interface claim without turning the
report into a benchmark or opening plugin/device execution surfaces.
