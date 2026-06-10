# Runtime Executor v0

Runtime Executor v0 is TUC's first practical execution path.

It executes an already-compiled `ComputeGraph` with an already-built
`PartitionPlan` through a fixed trusted in-process backend executor registry
and emits a deterministic execution trace.

It is not a backend plugin system.

## Contract

- Executor contract: `runtime_executor.trusted_backend.v0`
- Executor registry: `trusted_runtime_executor_registry.v0`
- API: `execute_graph(graph, partition_plan, inputs)`
- Trace API: `dump_execution_trace(trace)`
- Trusted prototype executors: `linear-sim`, `reference-cpu`
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

If a runtime plan names a backend that is not in the trusted registry, execution
fails closed. If a trusted executor is asked to execute an unsupported operation
kind, execution also fails closed.

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

The trace proves controlled execution by named trusted prototype executors. It
does not make native performance claims and does not authorize executable
external backends.

## Next Boundary

Executable prototype backends should come after this layer. They need a
separate backend executor contract, sandboxing model, negative tests, and
security review before external or generated backend artifacts can run.
