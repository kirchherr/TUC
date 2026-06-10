# RFC 0084: Runtime Tensor Value Contract

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Enforce Runtime Executor v0 tensor value contracts for trusted prototype
execution.

## Motivation

Runtime Backend Executor contracts already name:

```text
runtime_executor.numpy_float64_inputs.v0
runtime_executor.declared_shape_float64_output.v0
```

Those contracts must be executable checks, not documentation-only labels.
Runtime execution should fail closed before a backend sees malformed tensor
values or before an invalid result can enter the execution trace.

## Decision

Runtime Executor v0 now validates:

- external inputs are plain NumPy arrays
- input tensor names match external graph tensor names exactly
- input shapes match declared `TensorRef` shapes
- input dtype is `float64`
- input values are finite
- operation output shapes match declared output `TensorRef` shapes
- operation output dtype is `float64`
- operation output values are finite

Negative tests cover:

- input shape mismatch
- non-`float64` input dtype
- non-finite input value
- non-finite output value

## Security Model

This RFC does not add source parsing, backend discovery, plugin loading,
dynamic imports, dynamic libraries, subprocesses, generated-artifact execution,
JIT execution, device access, network access, host-path reads, or environment
inspection.

The validation operates only on already-provided in-memory NumPy arrays and
already-validated in-memory graph metadata.

## Consequences

- Runtime execution fails earlier for malformed tensor values.
- Trusted prototype backends cannot silently accept dtype, shape, or non-finite
  value drift.
- Execution traces remain evidence of values that passed the runtime tensor
  contract, not merely values accepted by NumPy broadcasting or promotion.
- Future executable backend proposals inherit a concrete tensor value boundary.

## References

- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Proof Of Execution](../docs/PROOF_OF_EXECUTION.md)
- [Security Baseline](../docs/SECURITY_BASELINE.md)
- `src/tuc/runtime/executor.py`
- `tests/test_runtime_executor.py`
