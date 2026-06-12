# RFC 0128: Runtime Execution Receipt Gate Binding

## Status

Accepted.

## Context

Runtime Execution Receipt v0 links runtime evidence reports by metadata digest.
Runtime Evidence Gate also checks those evidence reports independently.

Without an explicit binding check, a receipt can be internally valid while not
matching the specific evidence reports evaluated by the same gate invocation.
That creates an avoidable review gap: the gate would know that a receipt passes
and that reports pass, but not that the receipt links to those reports.

## Decision

Runtime Evidence Gate must verify that Runtime Execution Receipt links match
the evidence reports already evaluated by the gate.

For each linked evidence kind, the gate compares:

- graph name
- evidence contract
- metadata digest
- item count
- pass status
- raw-value policy

The binding check covers:

- `tensor_store_evidence`
- `input_manifest`
- `output_manifest`
- `reference_correctness`

## Security Boundary

The binding check is metadata-only. It does not load artifact files, inspect
host paths, serialize tensor values, execute generated artifacts, import
plugins, load dynamic libraries, touch devices, run JIT code, spawn
subprocesses, or access the network.

## Consequences

Runtime Evidence Gate now rejects forged or stale receipts that have valid
receipt shape but do not correspond to the current gate evidence reports.

The gate output includes:

```text
runtime_execution_receipt_binding = "verified"
```
