# Runtime Tensor Store

Runtime Tensor Store v0 is an internal Runtime Executor boundary for accepted
tensor values.

It introduces `RuntimeValueRecord` objects so the executor does not pass raw
mutable tensor dictionaries through the execution path.

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

External inputs are copied into read-only records before execution starts.
Computed outputs are copied into read-only records before later operations or
`RuntimeExecutionResult` can observe them.

## Security Boundary

Runtime Tensor Store v0 is not a memory allocator, cache, device buffer manager,
aliasing model, or persistence layer.

It does not allocate device memory, discover plugins, import backend modules,
load dynamic libraries, spawn subprocesses, access devices, touch the network,
execute generated artifacts, run JIT code, read host paths, read environment
variables, or authorize executable backend surfaces.

## Current Limitations

- It stores NumPy `float64` values only, matching Runtime Executor v0.
- It is internal to trusted in-process prototype execution.
- It does not model buffer reuse, aliasing, streams, pools, or device placement.
- Runtime Allocation Plan and Runtime Memory Budget remain the review surfaces
  for future allocator work.
