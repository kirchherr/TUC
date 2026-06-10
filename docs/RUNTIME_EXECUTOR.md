# Runtime Executor v0

Runtime Executor v0 is TUC's first practical execution path.

It executes an already-compiled `ComputeGraph` with an already-built
`PartitionPlan` through trusted in-process reference kernels and emits a
deterministic execution trace.

It is not a backend plugin system.

## Contract

- Executor contract: `runtime_executor.trusted_reference.v0`
- API: `execute_graph(graph, partition_plan, inputs)`
- Trace API: `dump_execution_trace(trace)`
- Trusted executor backend: `trusted-reference-kernel`
- Trace golden: `tests/golden/execution_traces/proof_of_execution.txt`
- Tests: `tests/test_runtime_executor.py`

## Security Boundary

Runtime Executor v0 does not:

- discover backend plugins
- import user modules
- spawn subprocesses
- access devices
- load dynamic libraries
- execute generated artifacts
- run JIT code
- touch the network

Inputs must be a plain mapping of external graph tensor names to NumPy arrays.
Missing inputs, unexpected intermediate tensors, non-plain mappings, partition
plan mismatches, unsupported arity, invalid axes, and output-shape mismatches
fail closed.

## Trace Semantics

The execution trace records:

- operation name
- planned backend from the runtime plan
- actual trusted executor backend
- operation kind
- input and output tensor names
- output shapes
- output dtypes
- execution status

The trace proves controlled execution. It does not make native performance
claims and does not authorize executable external backends.

## Next Boundary

Executable prototype backends should come after this layer. They need a
separate backend executor contract, sandboxing model, negative tests, and
security review before external or generated backend artifacts can run.
