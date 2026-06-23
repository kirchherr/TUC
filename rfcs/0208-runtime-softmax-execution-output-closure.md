# RFC 0208: Runtime Softmax Execution Output Closure

Status: Accepted

## Context

Runtime Execution Output Closure v0 covers the proof-of-execution fixture and
a multi-output runtime fixture. The Objective Alpha ladder also includes a
`matmul -> softmax` proof that preserves nonlinear softmax intent through
HAC-IR, runtime planning, trusted execution, and reference correctness.

## Decision

Add a softmax Runtime Execution Output Closure fixture:

- `examples/runtime_softmax_execution_output_closure.py`
- `tests/golden/runtime_execution_output_closure/proof_of_softmax.json`
- `tests/test_runtime_softmax_execution_output_closure.py`

The fixture binds the public alias `public_probabilities` to the terminal
`probabilities` tensor through Runtime Output Contract, Runtime Public Output
Bundle, Runtime Execution Receipt, Runtime Execution Evidence Bundle, and
Runtime Execution Output Closure.

## Security Boundary

The fixture uses only trusted in-repository proof and runtime builders. It does
not serialize tensor values, source text, host paths, commands, backend
artifacts, device identifiers, timing samples, runtime handles, URLs, or plugin
entry points.

## Consequences

Output closure now covers a nonlinear softmax proof path in addition to the
single-output execution proof and the two-public-output fixture. This expands
operation-family evidence for the Universal Compute claim without adding native
performance, broad source parsing, vendor replacement, device-access, or
generated-artifact execution claims.
