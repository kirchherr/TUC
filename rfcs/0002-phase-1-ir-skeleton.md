# RFC 0002: Phase 1 IR Skeleton

## Status

Accepted for prototype implementation

## Summary

Introduce explicit prototype modules for TUC's three compiler stages:

- TLIR
- HAC-IR
- HS-IR

Add lowering passes, a small compiler pipeline, and deterministic IR dumps.

## Motivation

The roadmap calls for a controlled pipeline before native MLIR implementation.
The project needs an inspectable skeleton that names the compiler boundaries and
lets tests assert how hints, operation kinds, and backend assignments move
through the system.

## Goals

- Represent TLIR, HAC-IR, and HS-IR as explicit module stages.
- Lower a `ComputeGraph` through all three stages.
- Preserve developer hints as metadata.
- Mark HAC-IR operations with semantic metadata such as linearity.
- Attach backend assignments in HS-IR.
- Provide deterministic text dumps for debugging.
- Keep the model small enough to replace with native MLIR later.

## Non-Goals

- Native MLIR dialect definitions.
- Parsing Python or Triton ASTs.
- Real PTX, HIP, or LLVM lowering.
- Performance benchmarking.
- Production backend execution.

## Proposal

Add:

- `tuc.ir.modules`
- `tuc.ir.dump`
- `tuc.compiler.lowering`
- `tuc.compiler.pipeline`

The pipeline constructs TLIR from a `ComputeGraph`, lowers it to HAC-IR,
partitions the HAC-IR graph by backend capability, and lowers to HS-IR with
backend assignments attached as operation attributes.

## Compatibility

This extends the Phase 0 prototype without changing existing public behavior.
The API remains pre-alpha.

## Testing

Add tests for:

- Stage-aware IR dumps.
- TLIR -> HAC-IR metadata propagation.
- HAC-IR -> HS-IR backend assignment.
- End-to-end pipeline diagnostics.

## Open Questions

- Should TLIR become a separate frontend-specific graph type?
- How much of the Python prototype should survive once native MLIR begins?
- Which operation should get the first golden correctness suite?
