# Runtime Evidence Flow

Runtime Evidence Flow explains how TUC turns trusted prototype execution into
reviewable metadata without serializing raw tensor values or approving external
execution surfaces.

For the shortest end-to-end reading path, see
[Minimal TUC Walkthrough](MINIMAL_TUC_WALKTHROUGH.md).

The current flow is:

```text
execute_graph
  -> RuntimeTensorStore
  -> Runtime HS-IR Plan Alignment
  -> Runtime Tensor Store Evidence
  -> Runtime Input Manifest
  -> Runtime Output Manifest
  -> Runtime Output Contract
  -> Runtime Public Output Bundle
  -> Runtime Reference Correctness
  -> Runtime Execution Receipt
  -> Runtime Execution Evidence Bundle
  -> Runtime Execution Output Closure
  -> Runtime Evidence Replay Verifier
  -> Runtime Backend Equivalence
  -> Runtime Transfer Evidence
  -> Runtime Transfer Trace Index
  -> Runtime Transfer Trace Replay Verifier
  -> Runtime Layout Conversion Evidence
  -> Runtime Layout Conversion Trace Index
  -> Runtime Layout Conversion Trace Replay Verifier
  -> Runtime Backend Equivalence Layout Binding
  -> Runtime Planning Explanation
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

`Runtime HS-IR Plan Alignment` compares HS-IR backend/layout metadata,
`PartitionPlan` assignments, and runtime trace steps for the mixed accelerator
slice. It serializes only bounded identifiers, counts, layout names, backend
names, trusted-executor statuses, and metadata digests.

`Runtime Planning Explanation` summarizes accepted `PartitionPlan` assignment
reasons, backend sequence, fallback count, candidate-score visibility, and
movement bytes. Runtime Evidence Gate binds it to both the systolic fallback
backend-equivalence candidate plan and the mixed no-fallback accelerator
candidate plan by exact Matrix artifact IDs.

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
Plan, Memory Budget, Allocation Request Manifest, Allocation Admission, and
Allocation Receipt evidence before allocator behavior can be accepted.

`Runtime Backend Equivalence` is required by Runtime Evidence Gate for the
systolic, vector, and mixed accelerator proof slices. It demonstrates that
distinct backend placements can preserve observable output semantics before
stronger portability or performance claims are made.

The proof class is described in
[Proof Of Backend Equivalence](PROOF_OF_BACKEND_EQUIVALENCE.md), including its
non-claims and review checklist. The canonical entrypoint is
`examples/proof_of_backend_equivalence.py`.

`Runtime HS-IR Plan Alignment` is the current bridge between backend-specific
IR facts and practical runtime execution evidence. It makes HS-IR drift from
the accepted plan or trace visible as deterministic JSON.

`Runtime Planning Explanation` is the current bridge between accepted
partition decisions and reviewer-facing planning rationale. It makes fallback
and movement accounting visible before richer planning behavior can count as
gated evidence.

`Runtime Transfer Evidence` records planned cross-domain transfer edges from
accepted `PartitionPlan` data as deterministic review evidence. It keeps
transfer bytes and planning-cost estimates visible while preserving the
`planning_estimate_not_measurement` and
`not_physical_residency_evidence` boundaries. See
[RUNTIME_TRANSFER_EVIDENCE.md](RUNTIME_TRANSFER_EVIDENCE.md),
`schemas/runtime_transfer_evidence_report.v0.schema.json`, and
`examples/runtime_transfer_evidence.py`.

`Runtime Transfer Trace Index` links those planned transfer records to
concrete producer and consumer `RuntimeExecutionTrace` step indexes. It keeps
transfer review aligned with execution order while preserving the
`transfer_not_materialized_as_runtime_step` boundary. Runtime Evidence Gate
requires it for the systolic backend-equivalence proof slice. See
[RUNTIME_TRANSFER_TRACE_INDEX.md](RUNTIME_TRANSFER_TRACE_INDEX.md),
`schemas/runtime_transfer_trace_index_report.v0.schema.json`, and
`examples/runtime_transfer_trace_index.py`.

`Runtime Transfer Trace Replay Verifier` replay-checks serialized Transfer
Evidence and Transfer Trace Index reports by metadata digest only. It binds the
planned transfer metadata to the trace-index projection while preserving the
`transfer_not_materialized_as_runtime_step` boundary. See
[RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md](RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md),
`schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json`, and
`examples/runtime_transfer_trace_replay_verifier.py`.

`Runtime Layout Conversion Evidence` is the current optional bridge between
planned layout-conversion edges and reviewer-facing layout-transition evidence.
It records planned logical layout transitions from an accepted `PartitionPlan`
without executing converters, allocating memory, or claiming physical device
residency. See
[RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md](RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md)
and `examples/runtime_layout_conversion_evidence.py`.

`Runtime Layout Conversion Trace Index` links those planned conversion records
to concrete producer and consumer `RuntimeExecutionTrace` step indexes. It keeps
layout-conversion review aligned with execution order while preserving the
`conversion_not_materialized_as_runtime_step` boundary. See
[RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX.md](RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX.md),
`schemas/runtime_layout_conversion_trace_index_report.v0.schema.json`, and
`examples/runtime_layout_conversion_trace_index.py`.

`Runtime Layout Conversion Trace Replay Verifier` replay-checks serialized
Layout Conversion Evidence and Trace Index reports by metadata digest only. See
[RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER.md](RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER.md),
`schemas/runtime_layout_conversion_trace_replay_verifier_report.v0.schema.json`, and
`examples/runtime_layout_conversion_trace_replay_verifier.py`.

`Runtime Backend Equivalence Layout Binding` binds the mixed Runtime Backend
Equivalence report to the verified Layout Conversion Trace Replay Verifier by
metadata digest. It makes the mixed proof slice carry both terminal-output
semantics and layout-transition evidence for the same graph. See
[RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md](RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md),
`schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json`, and
`examples/runtime_backend_equivalence_layout_binding.py`.

`Runtime Evidence Replay Verifier` replays serialized Runtime Execution Evidence
Bundle and Runtime Execution Output Closure reports by metadata digest only. See
[RUNTIME_EVIDENCE_REPLAY_VERIFIER.md](RUNTIME_EVIDENCE_REPLAY_VERIFIER.md) and
`examples/runtime_evidence_replay_verifier.py`.

Together, the gates keep the core proof visible:

```text
Intent -> Plan -> Execute -> Correct -> Reviewable Evidence
```
