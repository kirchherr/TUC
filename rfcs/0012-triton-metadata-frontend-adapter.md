# RFC 0012: Triton-Like Metadata Frontend Adapter

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds a prototype frontend adapter that converts declarative Triton-like
kernel metadata into a `ComputeGraph`.

## Motivation

TUC needs a bridge from Triton-style developer intent into its TLIR -> HAC-IR ->
HS-IR pipeline. Parsing Python source or executing `@triton.jit` functions would
create a large and premature attack surface. A metadata adapter lets TUC validate
the frontend contract first.

## Decision

Add `tuc.frontend.triton_metadata` with:

- `TritonTensorMetadata`
- `TritonOperationMetadata`
- `TritonKernelMetadata`
- `triton_metadata_to_compute_graph(...)`

The adapter supports typed dataclass use and `TritonKernelMetadata.from_mapping`
for plain metadata dictionaries.

## Security Model

The adapter is a data-only boundary:

- It does not parse Python source.
- It does not execute Triton kernels.
- It does not import user-selected modules.
- It rejects unknown fields.
- It rejects custom mapping subclasses on the mapping ingestion path.
- It rejects reserved `tuc.*` attributes from frontend input.
- It resolves operation tensors against explicitly declared tensors.

The produced `ComputeGraph` still passes through the existing IR validation and
compiler pipeline.

## Consequences

- TUC can claim a prototype L3 Triton-like metadata adapter.
- Frontend work can proceed without expanding plugin or source-execution risk.
- Future Triton syntax support remains a separate, threat-modeled project.

## Follow-Up

1. Add schema-versioned JSON loading for frontend metadata if external metadata
   files become part of the public API.
2. Add richer Triton idiom coverage once the metadata contract stabilizes.
3. Add source/parser threat modeling before any direct `@triton.jit` ingestion.
