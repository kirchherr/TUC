# RFC 0114: Runtime Public Output Bundle v0

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Public Output Bundle](../docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
  - [Runtime Output Contract](../docs/RUNTIME_OUTPUT_CONTRACT.md)
  - [Runtime Tensor Store](../docs/RUNTIME_TENSOR_STORE.md)
  - `schemas/runtime_public_output_bundle_report.v0.schema.json`
  - `examples/runtime_public_output_bundle.py`

## Summary

Add Runtime Public Output Bundle v0 as the practical runtime boundary that maps
explicit public output names to read-only in-memory runtime values while keeping
serialized evidence metadata-only.

## Motivation

Runtime Output Contract proves that public names bind to terminal graph tensor
names. That is still not enough for a usable runtime API: callers need a stable
way to request `api_row_sums` and receive the actual runtime value without
learning graph-internal terminal tensor names.

TUC needs this layer before higher-level frontend return semantics can be
credible. It must remain secure-by-design: the runtime may carry values, but the
review artifact must not leak values, source text, paths, devices, generated
code, plugins, subprocesses, or network locations.

## Decision

Runtime Public Output Bundle v0:

- accepts a `RuntimeExecutionResult` and a passing `RuntimeOutputContractReport`
- requires the execution graph name to match the output contract graph name
- resolves each public output to an internal `RuntimeValueRecord`
- copies each resolved NumPy value and marks it read-only
- exposes a read-only public-name mapping for runtime callers
- emits a deterministic metadata-only report
- includes shape, dtype, producer kind, producer id, value role, backing tensor
  name, value contract, record contract, and read-only status
- omits tensor values by policy

The report schema is:

```text
schemas/runtime_public_output_bundle_report.v0.schema.json
```

## Non-Goals

- tensor-value serialization
- tensor-content hashing
- positional tuple return semantics
- user-defined output transformations
- native backend correctness claims
- native performance claims
- generated artifact execution
- plugin discovery or artifact loading

## Security Boundary

The bundle object is a runtime object and may hold read-only in-memory tensor
values. Its report is evidence and must stay metadata-only.

The builder rejects failed output contracts and graph-name mismatches. Public
names, tensor names, producer ids, dtype strings, and report metadata are bounded
safe identifiers. The report schema is fail-closed and has no fields for raw
values, source text, file paths, host paths, generated code, command lines,
device identifiers, plugin entrypoints, network locations, or subprocesses.

## Acceptance Criteria

- A schema-versioned Runtime Public Output Bundle report exists.
- A deterministic example resolves public outputs for the multi-output fixture.
- Golden evidence proves two public outputs with read-only status and without
  raw tensor values.
- Tests cover value resolution, read-only protection, failed contracts,
  graph-name mismatches, raw-value rejection, forbidden names, schema shape, and
  documentation references.
