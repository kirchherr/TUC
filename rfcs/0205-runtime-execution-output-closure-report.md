# RFC 0205: Runtime Execution Output Closure Report

Status: Accepted

## Context

RFC 0204 closed the public output boundary by adding Output Contract and Runtime
Public Output Bundle links to Runtime Execution Receipt and Runtime Execution
Evidence Bundle. Reviewers still needed a compact audit artifact that showed
those links agree without inspecting nested reports manually.

## Decision

Add Runtime Execution Output Closure Report v0:

- `src/tuc/runtime/execution_output_closure.py`
- `examples/runtime_execution_output_closure.py`
- `schemas/runtime_execution_output_closure_report.v0.schema.json`
- `tests/golden/runtime_execution_output_closure/proof_of_execution.json`
- `tests/golden/runtime_execution_output_closure/multi_output_execution.json`
- `tests/golden/runtime_execution_output_closure/proof_of_softmax.json`
- [Runtime Execution Output Closure](../docs/RUNTIME_EXECUTION_OUTPUT_CLOSURE.md)

Runtime Evidence Gate now requires the report to pass and verifies that it is
bound to the Output Contract, Runtime Public Output Bundle, Runtime Execution
Receipt, and Runtime Execution Evidence Bundle evaluated by the same gate
invocation.

## Security Boundary

The report is data-only and fail-closed. It compares metadata digests, contract
IDs, item counts, pass/fail flags, and raw-value policy. It does not serialize
raw tensor values, source text, paths, commands, generated artifacts, backend
binaries, device identifiers, URLs, environment variables, or plugin entry
points.

## Consequences

The public-output closure is now directly reviewable and CI-facing. A stale or
forged receipt/bundle public-output link fails as an explicit output-closure
issue instead of being hidden inside nested evidence. The same report contract is
reused for the multi-output fixture through RFC 0207 and the softmax proof
fixture through RFC 0208.
