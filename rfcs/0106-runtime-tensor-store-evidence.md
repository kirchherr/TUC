# RFC 0106: Runtime Tensor Store Evidence v0

Status: Accepted

## Summary

Add a schema-versioned Runtime Tensor Store Evidence report that audits internal
Runtime Value Records without serializing tensor values.

## Motivation

Runtime Tensor Store v0 introduced an internal value-record boundary. The next
step is to make that boundary reviewable in CI and proof artifacts while
preserving secure-by-design diagnostics.

The evidence report proves record coverage, role assignment, shape agreement,
Runtime Executor dtype agreement, read-only value storage, and absence of
unexpected records. It deliberately does not expose tensor contents.

## Scope

This RFC adds:

- `schemas/runtime_tensor_store_evidence_report.v0.schema.json`
- `runtime_tensor_store_evidence.data_only.v0`
- `examples/runtime_tensor_store_evidence.py`
- deterministic golden evidence for `proof_of_execution`
- tests for golden stability, derived issues, schema shape, fail-closed schema
  behavior, and raw-value omission

## Non-Goals

This RFC does not add:

- tensor-value serialization
- tensor-value hashing
- device buffers
- memory pools
- aliasing semantics
- native backend execution
- plugin discovery
- benchmark or native-performance evidence

## Security Boundary

The report is metadata only. The schema blocks host paths, device identifiers,
commands, generated code, plugin entrypoints, raw tensor values, benchmark
samples, and executable backend surfaces.

The report's metadata digest is over record metadata only and never includes
tensor bytes.

## Acceptance Criteria

- The current proof-of-execution emits passing Runtime Tensor Store Evidence.
- The report schema is fail-closed with `additionalProperties: false`.
- Raw tensor values are omitted by policy.
- Read-only record status is included.
- Evidence issues are derived from expected graph records and observed runtime
  value records.
- The report remains separate from HAC-IR semantics and native-performance
  claims.
