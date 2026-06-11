# RFC 0108: Runtime Value Provenance v0

Status: Accepted

## Summary

Extend internal Runtime Value Records with data-only producer provenance.

Each `RuntimeValueRecord` now records:

- `producer_kind`
- `producer_id`

External inputs use `external_input/<tensor_name>`. Computed values use
`operation/<operation_name>`.

## Motivation

Runtime Tensor Store v0 introduced immutable internal records for runtime
values. The next useful boundary is knowing where each value came from without
exposing tensor contents.

Producer provenance supports debugging, Runtime Tensor Store Evidence, future
memory planning, and future aliasing review without changing HAC-IR semantics
or introducing executable backend surfaces.

## Scope

This RFC adds:

- producer provenance fields to `RuntimeValueRecord`
- fail-closed validation for invalid input or computed provenance
- producer provenance in Runtime Tensor Store Evidence
- schema coverage in `schemas/runtime_tensor_store_evidence_report.v0.schema.json`
- golden evidence updates for `proof_of_execution`

## Non-Goals

This RFC does not add:

- tensor-value serialization
- tensor-value hashing
- alias analysis
- in-place update semantics
- device-buffer tracking
- backend plugin discovery
- native executable backend artifacts

## Security Boundary

Runtime value provenance is metadata-only. It uses safe identifiers already
available in the graph and execution path. It does not read host paths, access
devices, import modules, spawn subprocesses, touch the network, execute
generated artifacts, run JIT code, or inspect tensor contents.

## Acceptance Criteria

- External input records identify their external tensor source.
- Computed records identify their producer operation.
- Invalid input and computed provenance fail closed.
- Runtime Tensor Store Evidence includes producer metadata and still omits raw
  tensor values by policy.
- Existing proof graphs continue to execute unchanged.
