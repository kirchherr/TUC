# RFC 0014: Native MLIR Design Spike

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds a parseable MLIR design-spike artifact for the future HAC-IR dialect.
The artifact uses unregistered dialect syntax so it can be checked with
`mlir-opt` without introducing native dialect code yet.

## Motivation

The Python IR prototype has made TLIR, HAC-IR, HS-IR, runtime planning, movement
metadata, and backend capability contracts inspectable. The next step is to map
those concepts toward MLIR without prematurely adding a native parser, pass
pipeline, or C++ dialect implementation.

## Decision

Add:

- `examples/mlir/tuc_hac_ir_spike.mlir`
- `scripts/verify_mlir_spike.py`
- Tests for artifact-level design invariants.

The spike sketches `tuc_hac.matmul` and `tuc_hac.elementwise` operations with
movement, layout, preferred-memory-domain, and error-budget metadata.

## Security Model

This is a repository-owned design artifact. It is not accepted as user input by
the compiler pipeline.

The verification script invokes `mlir-opt` with:

```text
--allow-unregistered-dialect
```

against the fixed repository artifact only. It does not scan directories, run
backend code, load dynamic libraries, or process caller-selected MLIR files.

Before TUC accepts external MLIR text or native parsers, the project must add a
dedicated threat model, fuzz targets, sanitizer coverage, and resource limits.

## Consequences

- The first native MLIR shape is visible and reviewable.
- HAC-IR concepts can be discussed using MLIR syntax before C++ work starts.
- Native implementation remains blocked on explicit hardening gates.

## Follow-Up

1. Define a TableGen dialect skeleton only after operation names and attributes
   settle.
2. Add parser/deserializer fuzzing before accepting external MLIR input.
3. Add MLIR pass contracts for TLIR -> HAC-IR and HAC-IR -> HS-IR lowering.
4. Add native-code sanitizer requirements to CI before merging C++ dialect code.
