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
- `input_manifest`
- `output_contract`
- `public_output_bundle`
- `reference_correctness`

Additional evidence, such as `proof_report_golden`, `frontend_intake_golden`,
`source_intent_return_semantics`, and `source_intent_runtime_returns`, can be
listed without changing completeness.

For Runtime Executor v0, `reference_correctness` is backed by the
schema-versioned [Runtime Reference Correctness](RUNTIME_REFERENCE_CORRECTNESS.md)
report at `schemas/runtime_reference_correctness_report.v0.schema.json`.
`input_manifest` is backed by the schema-versioned
[Runtime Input Manifest](RUNTIME_INPUT_MANIFEST.md) report at
`schemas/runtime_input_manifest_report.v0.schema.json`.
`output_contract` is backed by the schema-versioned
[Runtime Output Contract](RUNTIME_OUTPUT_CONTRACT.md) report at
`schemas/runtime_output_contract_report.v0.schema.json`.
`public_output_bundle` is backed by the schema-versioned
[Runtime Public Output Bundle](RUNTIME_PUBLIC_OUTPUT_BUNDLE.md) report at
`schemas/runtime_public_output_bundle_report.v0.schema.json`.
`source_intent_runtime_returns` is backed by
[Source Intent Runtime Returns](SOURCE_INTENT_RUNTIME_RETURNS.md) evidence at
`schemas/source_intent_runtime_returns_report.v0.schema.json`.

## Current Meaning

The current matrix is complete across every accepted graph fixture:

- `proof_of_abstraction`, `proof_of_reduction`, `proof_of_softmax`, and
  `triton_metadata_mvp_families` are complete across the required runtime
  evidence kinds.
- `proof_of_execution` is complete across HAC-IR, runtime-plan,
  compiler-decision, readiness, trace, input-manifest, output-contract,
  public-output-bundle, and reference-correctness evidence.
- `proof_of_systolic_execution` is complete across HAC-IR, runtime-plan,
  compiler-decision, readiness, trace, input-manifest, output-contract,
  public-output-bundle, and reference-correctness evidence.
- `source_intent_return_mlp` is complete across required runtime evidence and
  also records Source Intent return semantics plus Source Intent Runtime
  Returns evidence.

Future graph fixtures must either make every required evidence kind present or
show missing evidence as explicit matrix issues.

The CI-facing [Runtime Evidence Gate](RUNTIME_EVIDENCE_GATE.md) requires this
matrix to be complete before runtime executor conformance can count as passing
merge evidence. It also requires `source_intent_return_mlp` to remain present
with the `source_intent_metadata` source boundary and the
`source_intent_return_semantics` plus `source_intent_runtime_returns` artifact
kinds before Source Intent Runtime Returns can count as passing gate evidence.

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
