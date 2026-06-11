# Proof Of Execution

Proof of Execution is the first Objective Alpha proof that TUC can move from
runtime planning into controlled execution.

The proof compiles a graph, inspects the runtime plan, executes the graph
through Runtime Executor v0, emits a pre-execution readiness report, emits an
execution trace, emits data-only output evidence, and compares the result
against an independent reference result.

## Contract

- Example: `examples/proof_of_execution.py`
- Proof golden: `tests/golden/proofs/proof_of_execution.txt`
- Readiness golden: `tests/golden/execution_readiness/proof_of_execution.txt`
- Trace golden: `tests/golden/execution_traces/proof_of_execution.txt`
- Executor: [Runtime Executor v0](RUNTIME_EXECUTOR.md)
- Tests: `tests/test_proof_of_execution.py`

## What It Proves

- TUC can compile a graph into HAC-IR and a runtime plan.
- Runtime placement remains visible before execution.
- Runtime execution is gated by trusted backend executor contracts before the
  first operation runs.
- Runtime operation semantics are checked before any trusted reference kernel
  runs.
- Runtime tensor values are checked against shape, dtype, and finite-value
  contracts at input and output boundaries.
- Terminal graph outputs are captured in Runtime Output Manifest evidence
  without serializing raw tensor values.
- Execution uses fixed trusted in-process prototype executors.
- The execution trace records planned backend and actual executor separately.
- The final result matches an independent reference calculation.

## What It Does Not Prove

- native backend speed
- native backend correctness
- generated artifact safety
- plugin sandboxing
- direct device execution
- Triton JIT execution

Those remain future work behind separate security gates.
