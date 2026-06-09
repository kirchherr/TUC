# Triton-Like Metadata Adapter

TUC now has a prototype frontend adapter for Triton-like kernel metadata.

## Scope

The adapter accepts declarative metadata and produces a `ComputeGraph`.

It supports:

- Schema-versioned metadata through `triton_metadata.v0`.
- Kernel name.
- Tensor names, shapes, and dtypes.
- Ordered operations.
- MVP operation kinds.
- Operation inputs and outputs by tensor name.
- Developer hints.
- Optional non-reserved operation attributes.
- Optional layout metadata through a dedicated field.
- Deterministic intake reports through `TritonIntakeReport`.

## Non-Goals

This is not a Triton source parser and does not execute `@triton.jit` functions.
It does not import user modules, inspect Python bytecode, evaluate decorators, or
run arbitrary frontend code.

Direct Triton source ingestion remains blocked by
[`TRITON_SOURCE_THREAT_MODEL.md`](TRITON_SOURCE_THREAT_MODEL.md) until a future
parser implementation satisfies its resource-budget, negative-test, fuzzing,
and sandboxing gates.

The only source-text-facing implementation is
[`TRITON_SOURCE_PREFLIGHT.md`](TRITON_SOURCE_PREFLIGHT.md). It emits a bounded
diagnostic report and never produces a `ComputeGraph`.

[`SOURCE_INTENT_IR.md`](SOURCE_INTENT_IR.md) defines the future data-only
boundary between bounded source syntax data and schema-versioned metadata. It
does not convert to metadata or `ComputeGraph`.

[`SOURCE_INTENT_INTAKE.md`](SOURCE_INTENT_INTAKE.md) defines schema-versioned
plain-data construction of `SourceIntentModule`. It does not accept source
text, files, preflight reports, or Python objects.

[`SOURCE_INTENT_SCHEMA.md`](SOURCE_INTENT_SCHEMA.md) documents the
machine-readable `schemas/source_intent.v0.schema.json` contract for external
frontend authors. Runtime validation still happens in Source Intent Intake.

[`SOURCE_INTENT_METADATA.md`](SOURCE_INTENT_METADATA.md) defines the separate
execution-free adapter from an already constructed `SourceIntentModule` to
schema-versioned metadata. This still does not accept source text or preflight
reports.

[`SOURCE_INTENT_FRONTEND_CONFORMANCE.md`](SOURCE_INTENT_FRONTEND_CONFORMANCE.md)
defines a reusable certification path for external frontend authors that emit
`source_intent.v0` plain data. It checks in-memory cases only and does not load
frontend packages, parse source text, discover plugins, or execute backend
artifacts.

[`SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA.md`](SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA.md)
documents the machine-readable JSON Schema for deterministic frontend
conformance report artifacts:
`schemas/source_intent_frontend_conformance_report.v0.schema.json`.

[`SOURCE_TO_INTENT_PARSER_GATE.md`](SOURCE_TO_INTENT_PARSER_GATE.md) defines
the required future gate before source text or preflight reports may create
`source_intent.v0` plain data. It keeps parser work blocked until budgets,
corpus, diagnostics, goldens, HAC-IR neutrality review, and conformance
evidence exist.

[`SOURCE_TO_INTENT_READINESS.md`](SOURCE_TO_INTENT_READINESS.md) defines a
deterministic report for reviewing whether a future parser proposal has every
required gate artifact. The current golden report intentionally remains
blocked.

## Security Rules

Frontend metadata is treated as untrusted data:

- Mapping ingestion accepts only plain `dict`, `list`, and `tuple` structures.
- Unknown fields are rejected.
- Unsupported `schema_version` values are rejected.
- Reserved `tuc.*` attributes are rejected at the frontend boundary.
- Known execution-surface fields such as `import_module`, `python_source`,
  `jit_function`, `dynamic_library`, `device_path`, `subprocess`, `url`, and
  `generated_artifact` are rejected even when they appear inside otherwise
  allowed metadata or operation attributes.
- Operation tensor references must resolve to declared tensors.
- Tensor and graph validation still happens in the core IR model.

This keeps the frontend adapter as a data boundary instead of a code execution
surface.

## Intake Report

`TritonKernelMetadata.intake_report().dump()` emits stable evidence that the
frontend boundary remained execution-free. The report includes:

- schema version
- intake contract
- tensor count
- operation count
- operation kinds
- blocked execution surfaces

The intake report and the resulting HAC-IR, runtime plan, and compiler decision
report are golden-tested under:

```text
tests/golden/frontend/triton_metadata_intake.txt
tests/golden/hac_ir/triton_metadata_mlp.txt
tests/golden/runtime_plans/triton_metadata_mlp.txt
tests/golden/compiler_decisions/triton_metadata_mlp.txt
tests/golden/frontend/triton_metadata_mvp_families_intake.txt
tests/golden/hac_ir/triton_metadata_mvp_families.txt
tests/golden/runtime_plans/triton_metadata_mvp_families.txt
tests/golden/compiler_decisions/triton_metadata_mvp_families.txt
tests/golden/frontend/source_intent_intake_report.txt
tests/golden/frontend/source_intent_intake_module.txt
tests/golden/frontend/source_intent_intake_metadata.txt
tests/golden/hac_ir/source_intent_intake_mlp.txt
tests/golden/runtime_plans/source_intent_intake_mlp.txt
tests/golden/compiler_decisions/source_intent_intake_mlp.txt
tests/golden/frontend/source_intent_metadata_report.txt
tests/golden/frontend/source_intent_metadata_intake.txt
tests/golden/hac_ir/source_intent_metadata_mlp.txt
tests/golden/runtime_plans/source_intent_metadata_mlp.txt
tests/golden/compiler_decisions/source_intent_metadata_mlp.txt
tests/golden/frontend/source_intent_frontend_conformance_report.json
```

## Example

See `examples/triton_metadata_adapter.py` for a small metadata-to-pipeline
vertical slice. See `examples/triton_mvp_metadata.py` for a frontend-originated
graph that covers all MVP operation families without source parsing or Triton
JIT execution.
