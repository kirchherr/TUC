# MVP Definition

The TUC MVP is a vertical slice, not a full universal compiler.

## MVP Claim

TUC can represent a Triton-style compute workload in a hardware-agnostic IR,
carry developer hints through the pipeline, partition operations by backend
capabilities, and lower supported operations into a backend artifact.

## Included In MVP

- MatMul, elementwise, reduction, and softmax-like operation families.
- Developer hints as metadata.
- Hardware-agnostic compute graph model.
- Backend capability declarations.
- At least one simulator backend.
- Rule-based runtime partitioning.
- Tests for correctness of metadata, capability matching, partitioning, and
  backend lowering.
- Golden-kernel fixtures for the MVP operation families.
- Reproducible Docker development environment.

## Excluded From MVP

- Full Triton fork integration.
- Native MLIR dialect implementation.
- Real photonic or neuromorphic hardware support.
- Production PyTorch integration.
- Automatic global graph optimization.
- Performance parity with vendor libraries.

## MVP Success Criteria

- The repository builds and tests inside Docker.
- The Phase 0 example runs end to end.
- Backend capability and partitioning behavior are inspectable.
- MVP kernel semantics are covered by deterministic golden reference tests.
- The next implementation step toward MLIR is clear and documented.
