# Runtime Evidence Gate Matrix Coverage

Runtime Evidence Gate Matrix Coverage v0 is a data-only audit report for the
Matrix graph/artifact bindings that Runtime Evidence Gate treats as
merge-relevant.

It answers a narrow review question:

```text
Does the current Runtime Evidence Matrix still point at the exact evidence
artifacts that Runtime Evidence Gate accepts for backend-equivalence, HS-IR
alignment, and portfolio coverage?
```

## Contract

- Report schema:
  `schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json`
- Report schema version:
  `tuc.runtime_evidence_gate_matrix_coverage_report.v0`
- Evidence contract:
  `runtime_evidence_gate_matrix_coverage.data_only.v0`
- Example: `examples/runtime_evidence_gate_matrix_coverage.py`
- Golden:
  `tests/golden/proofs/runtime_evidence_gate_matrix_coverage_report.json`
- CI-facing consumer: `examples/runtime_evidence_gate.py`

## Current Bindings

The current audit covers four gate-required Matrix bindings:

- `runtime_backend_equivalence_matrix`
- `runtime_vector_backend_equivalence_matrix`
- `runtime_mixed_backend_equivalence_matrix`
- `runtime_backend_equivalence_portfolio_matrix`

The mixed backend-equivalence binding requires both
`runtime_backend_equivalence_mixed` and `runtime_hs_ir_plan_alignment_mixed`.

Each binding records:

- expected graph ID
- expected graph family
- expected source boundary
- required artifact kinds
- expected artifact IDs
- observed artifact IDs
- coverage status
- derived issues

Runtime Evidence Gate fails closed if the audit does not pass.

## Security Boundary

The audit compares bounded identifiers already present in
Runtime Evidence Matrix records. It does not resolve artifact IDs to paths,
scan the repository, load reports by filename, execute generated artifacts,
discover plugins, import backend modules, access devices, run JIT code, spawn
subprocesses, touch the network, load dynamic libraries, or authorize native
execution.

It does not serialize tensor values, runtime handles, host paths, command
lines, device identifiers, backend artifacts, generated code, source text, or
raw benchmark output.

## Review Meaning

This report is not an additional proof of numeric correctness. It is a
reviewable guardrail that makes Runtime Evidence Gate's Matrix dependency
explicit and deterministic.
