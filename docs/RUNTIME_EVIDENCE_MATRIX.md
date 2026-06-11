# Runtime Evidence Matrix

Runtime Evidence Matrix v0 is a data-only review report that inventories which
proof and runtime evidence exists for each accepted graph fixture.

It does not scan the repository, inspect host paths, execute examples, import
backend code, or approve native performance claims. The report only serializes
explicitly provided evidence identifiers.

## Contract

- Report schema: `schemas/runtime_evidence_matrix_report.v0.schema.json`
- Report schema version: `tuc.runtime_evidence_matrix_report.v0`
- Evidence contract: `runtime_evidence_matrix.data_only.v0`
- API: `build_runtime_evidence_matrix_report(matrix_id, graphs)`
- Current matrix API: `build_current_runtime_evidence_matrix_report()`
- Dump API: `dump_runtime_evidence_matrix_report(report)`
- Example: `examples/runtime_evidence_matrix.py`
- Golden: `tests/golden/proofs/runtime_evidence_matrix_report.json`
- CI gate: `examples/runtime_evidence_gate.py`

## Required Evidence Kinds

A graph is runtime-evidence complete only when it has:

- `hac_ir_golden`
- `runtime_plan_golden`
- `compiler_decision_golden`
- `execution_readiness_golden`
- `execution_trace_golden`
- `reference_correctness`

Additional evidence, such as `proof_report_golden` and
`frontend_intake_golden`, can be listed without changing completeness.

## Current Meaning

The current matrix is complete across every accepted graph fixture:

- `proof_of_abstraction`, `proof_of_reduction`, `proof_of_softmax`, and
  `triton_metadata_mvp_families` are complete across the required runtime
  evidence kinds.
- `proof_of_execution` is complete across HAC-IR, runtime-plan,
  compiler-decision, readiness, trace, and reference-correctness evidence.
- `proof_of_systolic_execution` is complete across HAC-IR, runtime-plan,
  compiler-decision, readiness, trace, and reference-correctness evidence.

Future graph fixtures must either make every required evidence kind present or
show missing evidence as explicit matrix issues.

The CI-facing [Runtime Evidence Gate](RUNTIME_EVIDENCE_GATE.md) requires this
matrix to be complete before runtime executor conformance can count as passing
merge evidence.

## Security Boundary

The report rejects path-like artifact IDs, known execution-surface identifiers,
unknown artifact kinds, duplicate graph IDs, duplicate artifact kinds per graph,
unsupported source boundaries, and forged issue lists.

It keeps the following surfaces blocked:

- backend plugin discovery
- device access
- dynamic imports
- dynamic library loading
- generated artifact execution
- JIT execution
- network access
- subprocess execution

The matrix is therefore a proof inventory, not an execution mechanism.
