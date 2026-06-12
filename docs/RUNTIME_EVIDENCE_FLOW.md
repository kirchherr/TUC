# Runtime Evidence Flow

Runtime Evidence Flow explains how TUC turns trusted prototype execution into
reviewable metadata without serializing raw tensor values or approving external
execution surfaces.

The current flow is:

```text
execute_graph
  -> RuntimeTensorStore
  -> Runtime Tensor Store Evidence
  -> Runtime Input Manifest
  -> Runtime Output Manifest
  -> Runtime Output Contract
  -> Runtime Public Output Bundle
  -> Runtime Reference Correctness
  -> Runtime Execution Receipt
  -> Runtime Execution Evidence Bundle
  -> Runtime Backend Equivalence
  -> Runtime Evidence Gate
```

## What Runs

`execute_graph(graph, partition_plan, inputs)` runs already-compiled graphs
through the fixed trusted in-process Runtime Executor registry.

Runtime Executor v0 does not discover plugins, import backend modules, access
devices, load dynamic libraries, spawn subprocesses, run JIT code, execute
generated artifacts, or touch the network.

## What Is Stored

Runtime Executor stores accepted values in `RuntimeValueRecord` objects inside
`RuntimeTensorStore`.

Each record keeps:

- tensor name
- copied read-only NumPy value
- declared shape
- dtype
- value role
- producer kind and producer ID
- planned backend
- planned memory domain
- planned layout
- placement source

For external inputs, placement source is `external_input_boundary` with
`external_input`, `host_ram`, and `row_major`.

For computed values, placement source is `partition_plan`, and planned backend,
memory domain, and layout are copied from the accepted runtime assignment.

These fields describe planned logical placement only. They are not device
handles, allocation handles, physical addresses, stream IDs, or proof of native
device residency.

## What Is Public

Internal tensor names and public output names are separated.

`RuntimeOutputContract` maps public aliases to terminal graph tensors.
`RuntimePublicOutputBundle` resolves those public aliases against trusted
runtime records while keeping review artifacts metadata-only.

## What Is Hashed

Runtime evidence digests cover metadata only:

- graph names
- contracts
- schema versions
- tensor names
- shapes
- dtypes
- producer metadata
- planned placement metadata
- item counts
- raw-value omission policy

Tensor contents are not serialized and are not hashed in review artifacts.

`Runtime Backend Equivalence` compares terminal outputs across two trusted
runtime executions, including current `reference-cpu` versus `systolic-sim`,
`reference-cpu` versus `vector-sim`, and mixed `reference-cpu` versus
`systolic-sim` plus `vector-sim` proof slices, but serializes only comparison
metadata and output omission status. It does not hash tensor contents.

## What Is Never Serialized

Runtime evidence does not serialize:

- raw tensor values
- tensor-value digests
- runtime handles
- device identifiers
- host paths
- environment variables
- commands
- generated code
- plugin entrypoints
- backend artifacts
- raw benchmark samples

## Gates

`Runtime Evidence Gate` checks that the current evidence set is complete and
that linked evidence reports agree on graph names, contracts, metadata digests,
item counts, pass status, and raw-value policy.

`Runtime Memory Planning Gate` separately checks Buffer Lifetime, Allocation
Plan, Memory Budget, and Allocation Request Manifest evidence before allocator
behavior can be accepted.

`Runtime Backend Equivalence` is required by Runtime Evidence Gate for the
systolic, vector, and mixed accelerator proof slices. It demonstrates that
distinct backend placements can preserve observable output semantics before
stronger portability or performance claims are made.

Together, the gates keep the core proof visible:

```text
Intent -> Plan -> Execute -> Correct -> Reviewable Evidence
```
