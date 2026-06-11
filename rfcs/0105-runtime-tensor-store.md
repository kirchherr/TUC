# RFC 0105: Runtime Tensor Store v0

Status: Accepted

## Summary

Introduce Runtime Tensor Store v0 as an internal Runtime Executor boundary that
stores accepted tensor values as read-only `RuntimeValueRecord` objects.

## Motivation

Runtime Executor v0 previously passed a mutable mapping of tensor names to NumPy
arrays through execution. That was sufficient for the first proof, but future
runtime memory work needs a clearer value identity boundary before allocator,
aliasing, or device-buffer concepts enter the runtime.

## Scope

This RFC adds:

- `RuntimeValueRecord`
- `RuntimeTensorStore`
- copied read-only input records
- copied read-only computed output records
- tests for input-copy isolation, read-only outputs, shape rejection, and
  duplicate tensor-name rejection

## Non-Goals

This RFC does not add:

- real memory allocation
- device buffers
- memory pools
- alias analysis
- stream or synchronization semantics
- serialization of tensor values
- executable backend discovery

## Security Boundary

Runtime Tensor Store v0 remains inside Runtime Executor v0. It validates names,
declared shape, `float64` dtype, finite values, and record roles.

It does not execute kernels by itself, import backend modules, load dynamic
libraries, spawn subprocesses, read host paths, read environment variables,
query devices, touch the network, execute generated artifacts, or authorize
external executable backend surfaces.

## Acceptance Criteria

- Runtime Executor keeps public `RuntimeExecutionResult.values` compatibility.
- Accepted inputs are copied before execution.
- Stored values are read-only.
- Duplicate tensor records fail closed.
- Shape, dtype, non-finite values, and unsupported roles fail closed.
- Tensor Store remains internal and does not modify HAC-IR semantics.
