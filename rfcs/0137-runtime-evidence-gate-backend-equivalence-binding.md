# RFC 0137: Runtime Evidence Gate Backend Equivalence Binding

## Status

Accepted.

## Context

Runtime Backend Equivalence v0 proves a practical runtime slice: the same
hardware-independent graph runs as a `reference-cpu` baseline and as a
`systolic-sim` candidate placement while preserving terminal output semantics.

As a standalone report, it is useful review evidence. For merge confidence it
must also be part of the CI-facing Runtime Evidence Gate.

## Decision

Runtime Evidence Gate now requires Runtime Backend Equivalence evidence.

The gate builds `examples/runtime_backend_equivalence.py` evidence by default
and fails closed unless:

- the report passes
- graph name is `runtime_backend_equivalence`
- baseline run ID is `reference_cpu`
- candidate run ID is `systolic_sim`
- baseline planned backend sequence is `reference-cpu, reference-cpu`
- candidate planned backend sequence is `systolic-sim, reference-cpu`
- every comparison is `matched`
- raw value policy remains `omitted_by_policy`

The gate golden remains:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

## Security Boundary

The gate does not serialize tensor values and does not introduce backend plugin
discovery, device access, dynamic imports, generated-artifact execution, JIT,
subprocesses, network access, or native performance claims.

It composes existing trusted in-process Runtime Executor evidence and checks
only metadata fields that are already bounded by Runtime Backend Equivalence
validation.

## Consequences

Backend Equivalence becomes part of the merge-facing proof surface, not just an
optional example.

This strengthens the practical Universal Compute claim while preserving the
same secure-by-design runtime boundary.
