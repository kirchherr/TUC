# TUC Architecture

TUC is organized around a small number of compiler and runtime boundaries.

## Frontend

The frontend preserves Triton-style developer ergonomics. During Phase 0, the
frontend work is represented by `CompilationHints`: optional metadata such as
noise robustness, sparsity preference, analog linear preference, and error
budgets.

Hints must never change mathematical correctness. They only inform lowering,
tuning, partitioning, and diagnostics.

## IR Stages

Phase 1 has an explicit Python-level IR skeleton with three stages:

- TLIR: Triton-like high-level intent.
- HAC-IR: hardware-agnostic compute intent and constraints.
- HS-IR: hardware-specific IR with backend assignments.

These modules are implemented in `tuc.ir.modules` and are dumped through
`tuc.ir.dump`.

## Hardware-Agnostic Compute IR

The current IR is a Python model, not an MLIR dialect yet. It exists to make the
contracts precise before native MLIR implementation begins.

The model contains:

- `TensorRef`: symbolic tensors.
- `OperationKind`: operation families such as matmul, elementwise, reduction,
  and softmax.
- `ComputeOperation`: ordered compute nodes.
- `ComputeGraph`: an ordered hardware-agnostic graph.

This is the conceptual seed for HAC-IR.

## Backend Capability Model

Backends declare what they can accept through `BackendCapability`.

Capabilities include:

- Supported operation kinds.
- Preferred operation kinds.
- Whether the backend supports noise modeling.
- Whether calibration is required or supported.
- Maximum error budget constraints.

This lets the runtime reason about a backend without knowing its implementation.

## Backend Lowering

Backends implement a minimal protocol:

- Expose capabilities.
- Lower a `ComputeGraph`.
- Return a `LoweringResult`.

The first backend is `LinearAlgebraSimulatorBackend`, a toy backend that accepts
linear algebra operations and emits a textual artifact.

## Runtime Partitioning

The Phase 0 runtime uses simple rule-based partitioning:

1. Prefer backends that explicitly prefer an operation kind.
2. Otherwise choose any backend that supports the operation.
3. Otherwise fall back to the default backend, currently named `gpu`.

This is intentionally simple. Later phases can replace the rule set with cost
models, transfer estimates, noise simulation, and calibration-aware scheduling.

## Compiler Pipeline

`tuc.compiler.pipeline` provides the current end-to-end skeleton:

```text
ComputeGraph
  -> TLIR module
  -> HAC-IR module
  -> PartitionPlan
  -> HS-IR module
```

The pipeline emits diagnostics and deterministic text dumps at each stage.

## Future MLIR Shape

The future native compiler pipeline should evolve toward:

```text
Triton-like frontend
  -> TLIR
  -> HAC-IR
  -> HS-IR
  -> backend artifact or runtime execution plan
```

Phase 0 exists to make those boundaries testable before native compiler
implementation begins.
