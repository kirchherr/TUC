# RFC 0142: Runtime Evidence Gate Equivalence Matrix Binding

## Status

Accepted.

## Context

Runtime Evidence Matrix now inventories Backend Equivalence fixtures with
graph-scoped `backend_equivalence` requirements. Runtime Evidence Gate also
checks the actual Backend Equivalence reports for the systolic, vector, and
mixed accelerator proof slices.

Without an explicit binding between those two surfaces, a report could pass
while the Matrix no longer inventories the same graph correctly.

## Decision

Runtime Evidence Gate now binds each checked Backend Equivalence report to its
Runtime Evidence Matrix graph entry.

For each report, the gate verifies:

- matrix graph ID matches the report graph name
- graph family is `backend_equivalence`
- source boundary is `runtime_backend_equivalence`
- required artifact kinds are exactly `backend_equivalence`
- the graph is runtime-evidence complete
- the graph lists the `backend_equivalence` artifact kind

The gate reports matrix coverage with deterministic output lines:

```text
runtime_backend_equivalence_matrix = "covered"
runtime_vector_backend_equivalence_matrix = "covered"
runtime_mixed_backend_equivalence_matrix = "covered"
```

## Security Boundary

This binding is metadata-only. It does not scan files, resolve artifact IDs to
paths, import modules, discover backends, execute examples, access devices,
spawn subprocesses, touch the network, run JIT code, load dynamic libraries, or
authorize native execution.

It compares bounded in-memory report objects and Matrix entries that already
passed closed-enum validation.

## Consequences

Backend Equivalence evidence must now be both correct as a report and present
in the curated runtime proof inventory before it can pass the CI-facing Runtime
Evidence Gate.

This keeps runtime evidence complete, reviewable, and less likely to drift as
new proof slices are added.
