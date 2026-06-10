# RFC 0080: Runtime Executor v0

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Add a trusted in-process Runtime Executor v0 and a `proof_of_execution` example.

## Motivation

TUC has strong metadata, planning, and proof-review artifacts. The next useful
step is practical execution without opening arbitrary backend execution.

## Decision

Add:

- `execute_graph(graph, partition_plan, inputs)`
- `RuntimeExecutionTrace`
- `RuntimeExecutionStep`
- `RuntimeExecutionResult`
- `dump_execution_trace(trace)`
- executor contract `runtime_executor.trusted_backend.v0`
- fixed trusted registry `trusted_runtime_executor_registry.v0`
- trusted prototype executors `linear-sim` and `reference-cpu`
- example `examples/proof_of_execution.py`
- proof golden `tests/golden/proofs/proof_of_execution.txt`
- execution-trace golden `tests/golden/execution_traces/proof_of_execution.txt`

Runtime Executor v0 executes only through fixed trusted in-process prototype
executors. It records the planned backend separately from the actual executor
backend.

## Security Model

Runtime Executor v0 does not discover plugins, import user modules, spawn
subprocesses, access devices, load dynamic libraries, run JIT code, touch the
network, or execute generated artifacts.

Inputs must be explicit NumPy arrays in a plain mapping. Unexpected inputs,
missing inputs, partition-plan mismatches, unsupported arity, invalid axes, and
output-shape mismatches fail closed.

Plans that name an executor outside the trusted registry fail closed. Plans that
ask a trusted executor to run an unsupported operation kind also fail closed.

## Consequences

- TUC becomes practical again: it can compile, plan, execute, trace, and verify.
- The execution proof remains deterministic and reviewable.
- Executable prototype backends can be added later behind a separate executor
  API and sandboxing/security review.
- No native performance claim is introduced.

## References

- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Proof Of Execution](../docs/PROOF_OF_EXECUTION.md)
- `examples/proof_of_execution.py`
- `tests/golden/execution_traces/proof_of_execution.txt`
- `tests/golden/proofs/proof_of_execution.txt`
