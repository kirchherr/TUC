# RFC 0135: Runtime Evidence Matrix Tensor Store Evidence

## Status

Accepted.

## Context

Runtime Tensor Store Evidence now records metadata-only runtime value records,
including planned backend, memory domain, layout, and placement source. That
evidence connects trusted execution results back to runtime planning decisions
without serializing tensor values or exposing runtime handles.

The curated Runtime Evidence Matrix previously required HAC-IR, runtime-plan,
compiler-decision, readiness, trace, input-manifest, output-contract,
public-output-bundle, reference-correctness, and execution-receipt evidence, but
did not require tensor-store evidence as a graph-level artifact kind.

## Decision

Add `tensor_store_evidence` to the Runtime Evidence Matrix supported and
required artifact kinds.

This makes tensor-store placement metadata a required review evidence category
for every accepted graph. The matrix remains an evidence inventory: artifact
identifiers are explicit review IDs, not implicit filesystem paths. Standalone
JSON goldens are added for executable runtime slices that can produce concrete
Runtime Tensor Store Evidence reports.

Matrix schema coverage remains in:

```text
schemas/runtime_evidence_matrix_report.v0.schema.json
```

The curated matrix golden remains:

```text
tests/golden/proofs/runtime_evidence_matrix_report.json
```

## Security Boundary

Tensor-store evidence is metadata-only. It does not serialize raw tensor values,
runtime handles, device identifiers, host paths, backend artifacts, commands,
generated code, plugin entrypoints, raw benchmark samples, or native execution
claims.

## Consequences

Every accepted runtime proof graph must now inventory tensor-store evidence
before the Runtime Evidence Matrix can be complete.

The systolic proof can explicitly show that `systolic-sim` produced planned
`device_sram` and `blocked` value-record metadata while execution still remains
inside the trusted in-process Runtime Executor.
