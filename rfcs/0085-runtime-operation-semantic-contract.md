# RFC 0085: Runtime Operation Semantic Contract

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Enforce concrete MVP operation semantics in Runtime Executor v0 before trusted
reference kernels run.

## Motivation

Runtime Executor v0 already validates backend contracts and tensor value
contracts. It must also validate operation-specific semantics before execution,
so malformed graph metadata cannot rely on NumPy broadcasting, implicit scalar
reductions, or backend-specific interpretation.

## Decision

Runtime Executor v0 now validates these rules during execution readiness:

- `matmul`: two rank-2 inputs, one rank-2 output, matching inner dimensions,
  and declared output shape `(m, n)`
- `elementwise`: one input, one output, matching shapes, and a supported
  reference kernel
- `reduction`: one input, one output, explicit in-bounds axis, non-scalar
  output, and declared output shape with that axis removed
- `softmax`: one input, one output, explicit in-bounds axis, and declared
  output shape equal to input shape

Negative tests cover:

- matmul input dimension mismatch
- elementwise output shape mismatch
- unsupported elementwise kernel
- reduction axis out of bounds
- reduction without axis
- scalar reduction output
- reduction output shape mismatch
- softmax output shape mismatch
- softmax axis out of bounds

## Security Model

This RFC does not add source parsing, backend discovery, plugin loading,
dynamic imports, dynamic libraries, subprocesses, generated-artifact execution,
JIT execution, device access, network access, host-path reads, or environment
inspection.

The validation uses only already-present in-memory `ComputeOperation` and
`TensorRef` metadata.

## Consequences

- Runtime execution rejects malformed MVP operation metadata before kernels run.
- Execution traces remain evidence of operations that passed explicit runtime
  semantics, not merely operations NumPy happened to accept.
- Future executable backend proposals inherit explicit shape and axis rules for
  the MVP operation families.

## References

- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Proof Of Execution](../docs/PROOF_OF_EXECUTION.md)
- [Security Baseline](../docs/SECURITY_BASELINE.md)
- `src/tuc/runtime/executor.py`
- `tests/test_runtime_executor.py`
