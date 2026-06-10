# Runtime Executor v0

Runtime Executor v0 is TUC's first practical execution path.

It executes an already-compiled `ComputeGraph` with an already-built
`PartitionPlan` through a fixed trusted in-process backend executor registry
and emits a deterministic execution trace.

It is not a backend plugin system.

## Contract

- Executor contract: `runtime_executor.trusted_backend.v0`
- Executor registry: `trusted_runtime_executor_registry.v0`
- Trusted backend contract: `runtime_backend_executor.trusted.v0`
- Operation semantic contract: `runtime_executor.operation_semantics.v0`
- Input value contract: `runtime_executor.numpy_float64_inputs.v0`
- Output value contract: `runtime_executor.declared_shape_float64_output.v0`
- API: `execute_graph(graph, partition_plan, inputs)`
- Readiness API: `runtime_execution_readiness_report(graph, partition_plan)`
- Trace API: `dump_execution_trace(trace)`
- Backend contract API: `trusted_runtime_executor_contracts()`
- Trusted prototype executors: `linear-sim`, `reference-cpu`
- Readiness golden:
  `tests/golden/execution_readiness/proof_of_execution.txt`
- MVP readiness golden:
  `tests/golden/execution_readiness/triton_metadata_mvp_families.txt`
- Proof trace golden: `tests/golden/execution_traces/proof_of_execution.txt`
- MVP trace golden:
  `tests/golden/execution_traces/triton_metadata_mvp_families.txt`
- Trusted backend contract golden:
  `tests/golden/runtime_backend_contracts/trusted_runtime_executor_registry.txt`
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
Each input must match the declared tensor shape, use `float64`, and contain only
finite values. Missing inputs, unexpected intermediate tensors, non-plain
mappings, partition plan mismatches, unsupported arity, invalid axes, invalid
operation shape semantics, invalid elementwise kernels, invalid input dtype or
shape, non-finite input values, output-shape mismatches, non-`float64` outputs,
and non-finite output values fail closed.

If a runtime plan names a backend that is not in the trusted registry, execution
fails closed. If a trusted executor is asked to execute an unsupported operation
kind, execution also fails closed.

## Execution Readiness

Before executing any operation, Runtime Executor v0 builds a
`RuntimeExecutionReadinessReport`. This report checks the already-compiled graph
and runtime plan against the trusted backend executor contracts.

The readiness report records:

- graph name
- executor and backend contract ids
- trusted executor registry id
- blocked execution surfaces
- planned backend for each operation
- supported operation families for that backend contract
- fail-closed readiness status

If the runtime plan names an untrusted backend contract or assigns an operation
to a backend contract that does not support its operation family, execution is
rejected before input normalization or kernel execution.

The proof-of-execution graph and the Triton-like MVP metadata graph both have
readiness goldens, so contract gates are validated before their execution
traces are accepted as evidence.

## Operation Semantic Contract

Runtime Executor v0 validates operation semantics before calling any trusted
reference kernel:

- `matmul` requires two rank-2 inputs, one rank-2 output, matching inner
  dimensions, and declared output shape `(m, n)`
- `elementwise` requires one input, one output, matching shapes, and a supported
  reference kernel
- `reduction` requires one input, one output, an explicit in-bounds axis, and a
  declared output shape with that axis removed
- `softmax` requires one input, one output, an explicit in-bounds axis, and a
  declared output shape equal to the input shape

These checks use `TensorRef` metadata only and run as part of execution
readiness. They prevent NumPy broadcasting, implicit reductions, scalar
outputs, or backend-specific shape interpretations from becoming hidden runtime
behavior.

## Tensor Value Contract

Runtime Executor v0 validates tensor values at the runtime boundary:

- external inputs must be plain NumPy arrays
- input names must match external graph tensor names exactly
- input shapes must match the declared `TensorRef` shapes
- input dtype must be `float64`
- input values must be finite
- operation outputs must match the declared output shape
- operation outputs must be `float64`
- operation outputs must be finite

This keeps trusted prototype execution deterministic and prevents hidden dtype,
shape, or non-finite-value drift from becoming backend-specific behavior.

## Trusted Backend Contract

Each in-process prototype executor exposes a `RuntimeBackendExecutorContract`.
The contract is pure data and records:

- backend name
- supported operation families
- execution mode
- input and output contracts
- blocked execution surfaces
- external artifact and device-access policy

For Runtime Executor v0, execution mode is fixed to
`in_process_reference_kernel`. External artifacts and device access are
`forbidden`, and the blocked execution-surface list must match the runtime
executor boundary exactly. A contract that weakens these fields fails closed.

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

Runtime Executor v0 now names the trusted in-process contract, but it still does
not authorize external executable backend artifacts.
