# RFC 0109: Runtime Output Manifest v0

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
  - [Runtime Output Manifest](../docs/RUNTIME_OUTPUT_MANIFEST.md)
  - [Runtime Tensor Store Evidence](../docs/RUNTIME_TENSOR_STORE_EVIDENCE.md)
  - [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
  - `schemas/runtime_output_manifest_report.v0.schema.json`

## Summary

Add Runtime Output Manifest v0 as a schema-versioned, data-only review artifact
for terminal graph outputs produced by Runtime Executor v0.

## Motivation

Runtime Executor v0 can execute a graph and return values. Runtime Tensor Store
Evidence proves that internal value records exist and remain read-only, but it
tracks every runtime value, including inputs and intermediates.

TUC also needs a smaller output-facing evidence boundary: which terminal graph
outputs were produced, which operation produced them, and whether their runtime
records obey the output metadata contract. This boundary is useful for proof
review, future API return contracts, and later allocator or artifact work
without serializing tensor contents.

## Decision

Runtime Output Manifest v0:

- derives terminal outputs from graph structure
- treats terminal outputs as produced tensors not consumed by later operations
- records expected output shape, dtype, value role, producer kind, and producer id
- records actual terminal output metadata from Runtime Tensor Store records
- requires output records to be read-only
- omits raw tensor values by policy
- emits a metadata-only digest
- exposes `assert_runtime_output_manifest`
- is included in Runtime Evidence Gate

The report schema is:

```text
schemas/runtime_output_manifest_report.v0.schema.json
```

## Non-Goals

- user-defined API aliases
- tensor-value serialization
- tensor-content hashing
- native performance claims
- device buffer ownership
- memory allocation or aliasing
- external backend artifact execution
- plugin discovery

## Security Boundary

Runtime Output Manifest is metadata only. It must not include tensor values,
host paths, device identifiers, generated code, commands, environment
variables, plugin entrypoints, network locations, raw benchmark output, or JIT
artifacts.

The manifest derives output identity from an already constructed `ComputeGraph`
and an already produced `RuntimeExecutionResult`. It does not parse source,
load files, discover backends, execute plugins, or authorize native artifacts.

## Acceptance Criteria

- Runtime Output Manifest report schema exists and fails closed on object shape.
- Proof-of-execution emits deterministic output manifest golden evidence.
- Runtime Evidence Gate requires a passing output manifest.
- Negative tests cover forged issues, mutable records, raw-value inclusion, and
  provenance mismatches.
- Documentation links the manifest to Runtime Executor and Runtime Evidence
  Gate.
