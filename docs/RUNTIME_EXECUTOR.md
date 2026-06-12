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
- Internal tensor store contract: `runtime_tensor_store.internal.v0`
- Internal value record contract: `runtime_value_record.internal.v0`
- Operation semantic contract: `runtime_executor.operation_semantics.v0`
- Input value contract: `runtime_executor.numpy_float64_inputs.v0`
- Output value contract: `runtime_executor.declared_shape_float64_output.v0`
- API: `execute_graph(graph, partition_plan, inputs)`
- Readiness API: `runtime_execution_readiness_report(graph, partition_plan)`
- Trace API: `dump_execution_trace(trace)`
- Backend contract API: `trusted_runtime_executor_contracts()`
- Conformance API: `run_runtime_executor_conformance()`
- Conformance report schema:
  `schemas/runtime_executor_conformance_report.v0.schema.json`
- Conformance golden:
  `tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json`
- Trusted prototype executors: `linear-sim`, `reference-cpu`, `systolic-sim`
- Readiness golden:
  `tests/golden/execution_readiness/proof_of_execution.txt`
- Objective Alpha readiness goldens:
  `tests/golden/execution_readiness/proof_of_abstraction.txt`,
  `tests/golden/execution_readiness/proof_of_reduction.txt`,
  `tests/golden/execution_readiness/proof_of_softmax.txt`
- MVP readiness golden:
  `tests/golden/execution_readiness/triton_metadata_mvp_families.txt`
- Proof trace golden: `tests/golden/execution_traces/proof_of_execution.txt`
- Proof-of-execution independent compiler-contract goldens:
  `tests/golden/hac_ir/proof_of_execution.txt`,
  `tests/golden/runtime_plans/proof_of_execution.txt`,
  `tests/golden/compiler_decisions/proof_of_execution.txt`
- Objective Alpha trace goldens:
  `tests/golden/execution_traces/proof_of_abstraction.txt`,
  `tests/golden/execution_traces/proof_of_reduction.txt`,
  `tests/golden/execution_traces/proof_of_softmax.txt`
- MVP trace golden:
  `tests/golden/execution_traces/triton_metadata_mvp_families.txt`
- Trusted backend contract golden:
  `tests/golden/runtime_backend_contracts/trusted_runtime_executor_registry.txt`
- Tests: `tests/test_runtime_executor.py`
- Conformance tests: `tests/test_runtime_executor_conformance.py`,
  `tests/test_runtime_executor_conformance_schema.py`

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

The Objective Alpha proof graphs, proof-of-execution graph, and Triton-like MVP
metadata graph all have readiness goldens, so contract gates are validated
before their execution traces are accepted as evidence.

## Executor Conformance

Runtime Executor Conformance v0 checks the fixed trusted executor registry
itself. It runs bounded in-memory fixtures for `matmul`, `elementwise`,
`reduction`, and `softmax` against every trusted executor.

The report requires:

- `linear-sim` to execute `matmul` and `reduction`
- `linear-sim` to reject `elementwise` and `softmax`
- `reference-cpu` to execute all MVP operation families
- `systolic-sim` to execute `matmul`
- `systolic-sim` to reject `elementwise`, `reduction`, and `softmax`

`Runtime Backend Equivalence` provides a practical comparison slice across the
same graph executed as a `reference-cpu` baseline and as a `systolic-sim`
candidate placement:

```bash
python examples/runtime_backend_equivalence.py
```

The schema-versioned report is documented in
[Runtime Executor Conformance](RUNTIME_EXECUTOR_CONFORMANCE.md). It keeps
unsupported execution visible as a clean rejection and does not authorize
external backend artifacts.

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

## Graph Topology Contract

Runtime Executor v0 validates the ordered graph before trusted kernels run:

- every produced tensor name must have exactly one producer
- operation inputs may read external inputs or previously produced tensors only
- operation inputs may not read tensors produced by later operations
- operation outputs may not overwrite external inputs

These checks make graph ordering an explicit runtime contract instead of an
accidental Python dictionary lookup. Invalid topology fails during execution
readiness before any operation is executed.

The accepted design note is
[`RFC 0107: Runtime Graph Topology Contract v0`](../rfcs/0107-runtime-graph-topology-contract.md).

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

## Runtime Tensor Store

Runtime Tensor Store v0 is an internal executor boundary. It records every
accepted runtime tensor value as a `RuntimeValueRecord` with:

- tensor name
- immutable copied value
- declared shape
- dtype
- value role, either `input` or `computed`
- producer kind and producer identifier
- planned backend
- planned memory domain
- planned layout
- placement source

External inputs are copied into read-only records before execution starts, and
computed outputs are copied into read-only records before they become visible to
later operations or `RuntimeExecutionResult`. This prevents caller-side input
mutation and accidental output mutation from changing already accepted runtime
evidence. Input records point to their external tensor name; computed records
point to their producer operation name.

Input records use the external input boundary as logical placement. Computed
records copy planned backend, memory domain, and layout from the accepted
`PartitionPlan`. This is planned placement evidence only; it is not device
access, physical residency proof, or allocator behavior.

The tensor store is not a memory allocator, not a cache, not a device buffer
manager, not a runtime-handle registry, and not an aliasing model. It is the
minimum internal value-record surface needed before future runtime memory work
can reason about value identity without passing raw mutable mappings around.

The review artifact for this boundary is
[`RUNTIME_TENSOR_STORE_EVIDENCE.md`](RUNTIME_TENSOR_STORE_EVIDENCE.md). It
serializes record metadata and read-only status, but never tensor values.

## Runtime Input Manifest

Runtime Input Manifest v0 is the data-only review artifact for graph external
inputs. It derives external inputs from the already-compiled graph, then checks
that Runtime Tensor Store records expose those inputs as read-only `input`
values with `external_input` producer provenance.

The schema-versioned report is documented in
[`RUNTIME_INPUT_MANIFEST.md`](RUNTIME_INPUT_MANIFEST.md), with schema at
`schemas/runtime_input_manifest_report.v0.schema.json`. It serializes input
metadata only and omits raw tensor values by policy.

## Runtime Output Manifest

Runtime Output Manifest v0 is the data-only review artifact for terminal graph
outputs. It derives terminal outputs from the already-compiled graph, then
checks that Runtime Tensor Store records expose those outputs as read-only
`computed` values with operation producer provenance.

The schema-versioned report is documented in
[`RUNTIME_OUTPUT_MANIFEST.md`](RUNTIME_OUTPUT_MANIFEST.md), with schema at
`schemas/runtime_output_manifest_report.v0.schema.json`. It serializes output
metadata only and omits raw tensor values by policy.

## Runtime Reference Correctness

Runtime Reference Correctness v0 is the data-only review artifact for comparing
terminal graph outputs against independent reference tensors. It performs the
comparison in memory, but serializes only shapes, dtypes, tolerances, comparison
status, and omitted-value policies.

The schema-versioned report is documented in
[`RUNTIME_REFERENCE_CORRECTNESS.md`](RUNTIME_REFERENCE_CORRECTNESS.md), with
schema at `schemas/runtime_reference_correctness_report.v0.schema.json`.

## Runtime Execution Receipt

Runtime Execution Receipt v0 links one trusted runtime execution to its
metadata-only evidence reports: Runtime Tensor Store Evidence, Runtime Input
Manifest, Runtime Output Manifest, and Runtime Reference Correctness.

The schema-versioned report is documented in
[`RUNTIME_EXECUTION_RECEIPT.md`](RUNTIME_EXECUTION_RECEIPT.md), with schema at
`schemas/runtime_execution_receipt_report.v0.schema.json`. It records graph
names, evidence contracts, metadata digests, item counts, operation trace
metadata, and omitted-value policy, but never tensor values.

## Runtime Execution Evidence Bundle

Runtime Execution Evidence Bundle v0 packages Runtime Tensor Store Evidence,
Runtime Input Manifest, Runtime Output Manifest, Runtime Reference Correctness,
and Runtime Execution Receipt into one metadata-only review report.

The schema-versioned report is documented in
[`RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md`](RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md),
with schema at
`schemas/runtime_execution_evidence_bundle_report.v0.schema.json`. It rechecks
that the embedded receipt links match the embedded evidence reports by graph
name, contract, metadata digest, item count, pass status, and omitted-value
policy.

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
