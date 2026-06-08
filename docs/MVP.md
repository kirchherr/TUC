# MVP Definition

The TUC MVP is a vertical proof of abstraction, not a full compiler product.

## MVP Claim

TUC can represent compute intent in a hardware-agnostic IR, partition operations
by backend capabilities, explain the runtime plan, and produce a deterministic
mathematical result that matches an independent reference.

## Included In MVP

- MatMul, elementwise, reduction, and softmax-like operation families.
- `examples/proof_of_abstraction.py` as Objective Alpha.
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
- The proof-of-abstraction example prints HAC-IR, backend assignments, transfer
  plan, result, reference result, and `PASS`.
- The proof-of-abstraction output is checked against a golden validation file.
- Backend capability and partitioning behavior are inspectable.
- MVP kernel semantics are covered by deterministic golden reference tests.
- The next implementation step toward MLIR is clear and documented.
