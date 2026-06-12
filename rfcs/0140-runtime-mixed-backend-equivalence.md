# RFC 0140: Runtime Mixed Backend Equivalence

## Status

Accepted.

## Context

TUC already has practical Runtime Backend Equivalence evidence for:

- `reference-cpu` versus matrix-oriented `systolic-sim`
- `reference-cpu` versus vector-oriented `vector-sim`

Those slices prove that separate non-CPU trusted accelerator families can
preserve terminal output semantics for their own operation families. The next
practical Universal Compute step is proving that two accelerator families can
compose in one planned graph without changing compute intent.

## Decision

Add `examples/runtime_mixed_backend_equivalence.py`.

The fixture compiles and executes the same neutral
`matmul -> softmax -> reduction -> elementwise` graph twice:

- baseline: `reference-cpu`, `reference-cpu`, `reference-cpu`, `reference-cpu`
- candidate: `systolic-sim`, `vector-sim`, `vector-sim`, `vector-sim`

The deterministic golden is:

```text
tests/golden/runtime_backend_equivalence/mixed_accelerators.json
```

Runtime Evidence Gate now requires this report and fails closed unless:

- graph name is `runtime_mixed_backend_equivalence`
- baseline run ID is `reference_cpu`
- candidate run ID is `mixed_accelerators`
- baseline planned backend sequence is
  `reference-cpu, reference-cpu, reference-cpu, reference-cpu`
- candidate planned backend sequence is
  `systolic-sim, vector-sim, vector-sim, vector-sim`
- every comparison is `matched`
- raw value policy remains `omitted_by_policy`

## Security Boundary

The mixed fixture remains inside Runtime Executor v0's trusted in-process
reference-kernel boundary.

It does not add plugin discovery, dynamic imports, dynamic library loading,
device access, subprocess execution, network access, JIT execution, generated
artifact execution, native execution, raw benchmark loading, or serialized
tensor values.

The report serializes only bounded metadata, backend sequences, shapes, dtypes,
comparison status, tolerance policy, and raw-value omission policy.

## Consequences

TUC now has merge-facing evidence that a single hardware-independent graph can
be planned across two distinct trusted accelerator families while preserving
terminal output semantics.

This strengthens the Universal Compute proof without making native performance
or real-device residency claims.
