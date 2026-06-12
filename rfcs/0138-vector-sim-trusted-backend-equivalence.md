# RFC 0138: Vector Simulator Trusted Backend Equivalence

## Status

Accepted.

## Context

TUC must avoid making one accelerator family the implicit center of the
Universal Compute proof. Runtime Backend Equivalence already compares a
`reference-cpu` baseline with a `systolic-sim` candidate for matrix-oriented
placement.

That is useful, but it leaves vector-style operation families underrepresented
in practical backend-equivalence evidence.

## Decision

Add `VectorSimulatorBackend` as a trusted in-process prototype backend named
`vector-sim`.

`vector-sim` supports:

- `elementwise`
- `reduction`
- `softmax`

It rejects:

- `matmul`

The trusted Runtime Executor registry includes `vector-sim`, and Runtime
Executor Conformance checks both its supported execution cases and its
unsupported `matmul` rejection.

Add `examples/runtime_vector_backend_equivalence.py` as a data-only practical
equivalence fixture. It compiles and executes the same neutral
`softmax -> reduction -> elementwise` graph twice:

- baseline: `reference-cpu`, `reference-cpu`, `reference-cpu`
- candidate: `vector-sim`, `vector-sim`, `vector-sim`

The deterministic golden is:

```text
tests/golden/runtime_backend_equivalence/vector_sim_report.json
```

## Security Boundary

`vector-sim` is not an external backend plugin and does not authorize native
execution.

It does not add plugin discovery, dynamic imports, dynamic library loading,
device access, subprocess execution, network access, JIT execution, generated
artifact execution, host-path reads, command capture, raw benchmark loading, or
serialized tensor values.

The equivalence report may compare trusted in-memory arrays inside Runtime
Executor v0, but review evidence serializes only bounded metadata, status,
shapes, dtypes, backend sequences, tolerance policy, and raw-value omission
policy.

## Consequences

TUC now has practical equivalence evidence for two non-CPU trusted accelerator
families:

- matrix-oriented `systolic-sim`
- vector-oriented `vector-sim`

This broadens the Universal Compute proof while keeping backend execution
inside the same secure-by-design prototype boundary.
