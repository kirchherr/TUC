# RFC 0110: Runtime Reference Correctness v0

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Reference Correctness](../docs/RUNTIME_REFERENCE_CORRECTNESS.md)
  - [Runtime Output Manifest](../docs/RUNTIME_OUTPUT_MANIFEST.md)
  - [Proof Of Execution](../docs/PROOF_OF_EXECUTION.md)
  - [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
  - `schemas/runtime_reference_correctness_report.v0.schema.json`

## Summary

Add Runtime Reference Correctness v0 as a schema-versioned, data-only report
that compares terminal Runtime Executor outputs against independent reference
tensors without serializing either side's tensor values.

## Motivation

Objective Alpha already requires reference correctness. Historically, proof
reports printed concrete result and reference arrays. That is acceptable for
tiny deterministic fixtures, but it is not a secure-by-design boundary for a
future compiler/runtime that may process sensitive model inputs or outputs.

TUC needs reference correctness evidence that can be reviewed, gated, and
digested without logging tensor contents.

## Decision

Runtime Reference Correctness v0:

- derives terminal outputs through Runtime Output Manifest
- accepts an explicit plain-dict mapping from output tensor name to reference
  array
- compares output and reference arrays in memory with bounded tolerances
- emits only metadata: tensor name, shapes, dtypes, tolerances, status, and
  value-omission policy
- rejects non-plain reference mappings
- records missing references, unexpected references, invalid references, and
  mismatches as structured issues
- is included in Runtime Evidence Gate
- replaces raw result/reference sections in `proof_of_execution` with a
  data-only correctness report

The report schema is:

```text
schemas/runtime_reference_correctness_report.v0.schema.json
```

## Non-Goals

- serializing tensor values
- hashing tensor contents
- reporting elementwise differences or max-error magnitudes
- native backend correctness claims
- native performance claims
- external executable backend approval
- plugin discovery or artifact loading

## Security Boundary

The report must not include raw tensor values, host paths, device identifiers,
generated code, commands, environment variables, plugin entrypoints, network
locations, raw benchmark output, JIT artifacts, or native executable artifacts.

The comparison may read arrays in memory to compute `matched` or `mismatched`,
but only data-independent metadata leaves the runtime boundary.

## Acceptance Criteria

- Runtime Reference Correctness report schema exists and fails closed on object
  shape.
- Proof-of-execution emits deterministic reference-correctness golden evidence.
- `proof_of_execution` no longer prints raw result/reference arrays.
- Runtime Evidence Gate requires passing reference correctness.
- Negative tests cover mismatches, missing references, unexpected references,
  invalid references, forged issues, raw-value inclusion, and forbidden
  surface names.
