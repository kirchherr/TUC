# Runtime Tensor Store

Runtime Tensor Store v0 is an internal Runtime Executor boundary for accepted
tensor values.

It introduces `RuntimeValueRecord` objects so the executor does not pass raw
mutable tensor dictionaries through the execution path.

Review evidence for the current record boundary is documented in
[`RUNTIME_TENSOR_STORE_EVIDENCE.md`](RUNTIME_TENSOR_STORE_EVIDENCE.md).

## Contract

- Tensor store contract: `runtime_tensor_store.internal.v0`
- Value record contract: `runtime_value_record.internal.v0`
- Value roles: `input`, `computed`
- Runtime owner: `Runtime Executor v0`

## What It Records

Each `RuntimeValueRecord` records:

- tensor name
- copied read-only value
- declared shape
- dtype
- value role
- producer kind, either `external_input` or `operation`
- producer identifier, either the external tensor name or producer operation name

External inputs are copied into read-only records before execution starts.
Their producer is recorded as `external_input/<tensor_name>`.
Computed outputs are copied into read-only records before later operations or
`RuntimeExecutionResult` can observe them. Their producer is recorded as
`operation/<operation_name>`.

## Security Boundary

Runtime Tensor Store v0 is not a memory allocator, cache, device buffer manager,
aliasing model, or persistence layer.

It does not allocate device memory, discover plugins, import backend modules,
load dynamic libraries, spawn subprocesses, access devices, touch the network,
execute generated artifacts, run JIT code, read host paths, read environment
variables, or authorize executable backend surfaces.

Runtime Tensor Store Evidence follows the same boundary: it serializes record
metadata and producer provenance only, and omits tensor values by policy.

Runtime Output Manifest uses the same internal records for terminal graph
outputs only. It documents the output-facing proof boundary separately in
[`RUNTIME_OUTPUT_MANIFEST.md`](RUNTIME_OUTPUT_MANIFEST.md).

The accepted producer-provenance design note is
[`RFC 0108: Runtime Value Provenance v0`](../rfcs/0108-runtime-value-provenance.md).

## Current Limitations

- It stores NumPy `float64` values only, matching Runtime Executor v0.
- It is internal to trusted in-process prototype execution.
- It does not model buffer reuse, aliasing, streams, pools, or device placement.
- Runtime Allocation Plan and Runtime Memory Budget remain the review surfaces
  for future allocator work.
