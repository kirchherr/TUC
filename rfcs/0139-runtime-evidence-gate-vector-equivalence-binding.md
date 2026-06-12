# RFC 0139: Runtime Evidence Gate Vector Equivalence Binding

## Status

Accepted.

## Context

`vector-sim` adds a second non-CPU trusted accelerator family to the practical
Runtime Backend Equivalence proof surface. As standalone evidence, it shows that
the vector-oriented `softmax -> reduction -> elementwise` graph preserves
terminal output semantics against a `reference-cpu` baseline.

For TUC's Universal Compute claim, this evidence should be merge-relevant in
the same way as the existing `systolic-sim` backend equivalence fixture.

## Decision

Runtime Evidence Gate now requires Runtime Vector Backend Equivalence evidence.

The gate builds `examples/runtime_vector_backend_equivalence.py` evidence by
default and fails closed unless:

- the report passes
- graph name is `runtime_vector_backend_equivalence`
- baseline run ID is `reference_cpu`
- candidate run ID is `vector_sim`
- baseline planned backend sequence is
  `reference-cpu, reference-cpu, reference-cpu`
- candidate planned backend sequence is `vector-sim, vector-sim, vector-sim`
- every comparison is `matched`
- raw value policy remains `omitted_by_policy`

The gate golden remains:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

## Security Boundary

The gate does not serialize tensor values and does not introduce backend plugin
discovery, device access, dynamic imports, generated-artifact execution, JIT,
subprocesses, network access, native execution, or native performance claims.

It composes existing trusted in-process Runtime Executor evidence and checks
only bounded metadata fields already validated by Runtime Backend Equivalence.

## Consequences

The vector proof slice is now part of the CI-facing runtime evidence boundary.

TUC's practical proof no longer depends on only one non-CPU accelerator family:
the gate now binds both matrix-oriented `systolic-sim` and vector-oriented
`vector-sim` equivalence evidence.
