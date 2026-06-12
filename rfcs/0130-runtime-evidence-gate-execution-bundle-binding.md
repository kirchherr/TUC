# RFC 0130: Runtime Evidence Gate Execution Bundle Binding

## Status

Accepted.

## Context

Runtime Execution Evidence Bundle v0 packages one execution's metadata-only
runtime evidence reports and execution receipt for review. Runtime Evidence
Gate already verifies those reports independently and binds the receipt to the
same gate invocation.

Without a bundle binding check, a passing bundle could be coherent internally
but not correspond to the reports evaluated by the gate.

## Decision

Runtime Evidence Gate verifies Runtime Execution Evidence Bundle v0 when it
builds the CI-facing gate report.

The gate checks:

- the bundle passes
- embedded report graph names match the reports evaluated by the gate
- embedded report contracts match the reports evaluated by the gate
- embedded report metadata digests match the reports evaluated by the gate
- embedded report item counts match the reports evaluated by the gate
- embedded report pass status and raw-value policy match the reports evaluated
  by the gate
- embedded Runtime Execution Receipt metadata digest matches the receipt
  evaluated by the gate

The bundle remains a derived review artifact. It is not required for Runtime
Evidence Matrix completeness.

## Security Boundary

The binding check is metadata-only. It does not load artifact files, inspect
host paths, serialize tensor values, execute generated artifacts, import
plugins, load dynamic libraries, touch devices, run JIT code, spawn
subprocesses, or access the network.

## Consequences

Runtime Evidence Gate now rejects stale or forged execution evidence bundles
even when the bundle is internally coherent.

The gate output includes:

```text
runtime_execution_evidence_bundle = "passed"
runtime_execution_evidence_bundle_binding = "verified"
```
