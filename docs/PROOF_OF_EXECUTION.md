# Proof Of Execution

Proof of Execution is the first Objective Alpha proof that TUC can move from
runtime planning into controlled execution.

The proof compiles a graph, inspects the runtime plan, executes the graph
through Runtime Executor v0, emits an execution trace, and compares the result
against an independent reference result.

## Contract

- Example: `examples/proof_of_execution.py`
- Proof golden: `tests/golden/proofs/proof_of_execution.txt`
- Trace golden: `tests/golden/execution_traces/proof_of_execution.txt`
- Executor: [Runtime Executor v0](RUNTIME_EXECUTOR.md)
- Tests: `tests/test_proof_of_execution.py`

## What It Proves

- TUC can compile a graph into HAC-IR and a runtime plan.
- Runtime placement remains visible before execution.
- Execution uses a trusted in-process reference executor.
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
