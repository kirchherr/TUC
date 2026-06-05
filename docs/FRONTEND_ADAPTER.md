# Triton-Like Metadata Adapter

TUC now has a prototype frontend adapter for Triton-like kernel metadata.

## Scope

The adapter accepts declarative metadata and produces a `ComputeGraph`.

It supports:

- Kernel name.
- Tensor names, shapes, and dtypes.
- Ordered operations.
- MVP operation kinds.
- Operation inputs and outputs by tensor name.
- Developer hints.
- Optional non-reserved operation attributes.
- Optional layout metadata through a dedicated field.

## Non-Goals

This is not a Triton source parser and does not execute `@triton.jit` functions.
It does not import user modules, inspect Python bytecode, evaluate decorators, or
run arbitrary frontend code.

## Security Rules

Frontend metadata is treated as untrusted data:

- Mapping ingestion accepts only plain `dict`, `list`, and `tuple` structures.
- Unknown fields are rejected.
- Reserved `tuc.*` attributes are rejected at the frontend boundary.
- Operation tensor references must resolve to declared tensors.
- Tensor and graph validation still happens in the core IR model.

This keeps the frontend adapter as a data boundary instead of a code execution
surface.

## Example

See `examples/triton_metadata_adapter.py` for a small metadata-to-pipeline
vertical slice.
