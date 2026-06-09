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
```

## Example

See `examples/triton_metadata_adapter.py` for a small metadata-to-pipeline
vertical slice. See `examples/triton_mvp_metadata.py` for a frontend-originated
graph that covers all MVP operation families without source parsing or Triton
JIT execution.
