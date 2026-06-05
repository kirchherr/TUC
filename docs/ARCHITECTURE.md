# TUC Architecture

TUC is organized around a small number of compiler and runtime boundaries.

## Frontend

The frontend preserves Triton-style developer ergonomics. During the early
prototype phases, frontend work is represented by `CompilationHints`: optional
metadata such as noise robustness, sparsity preference, analog linear
preference, and error budgets.

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
- `MovementEstimate`: per-operation bytes read, bytes written, arithmetic
  operations, arithmetic intensity, preferred memory domain, and layout.

This is the conceptual seed for HAC-IR.

IR objects validate and canonicalize their own boundary data: names are
identifier-safe, tensor ranks and dimensions are bounded, graph operation names
must be unique, tensor bindings must be consistent, and attributes/metadata are
immutable mappings with type, depth, key-count, string-size, and total-size
budgets.

## Data Movement Awareness

HAC-IR now records data movement as an explicit compiler fact. The pass in
`tuc.compiler.movement` estimates read bytes, written bytes, arithmetic
operations, arithmetic intensity, preferred memory domain, and layout constraints
for the MVP operation family.

This is the first compiler hook for addressing the memory wall and the von
Neumann bottleneck. It keeps future placement, transfer, and runtime scheduling
decisions tied to inspectable IR data rather than hidden backend behavior.

Movement metadata is secure by design:

- It is declarative and deterministic.
- Unknown dtypes and invalid shapes are rejected.
- Estimator resource limits bound tensor rank, tensor count, element count, and
  byte size.
- Compiler-produced movement attributes overwrite user-supplied `tuc.*`
  movement keys.
- Summaries fail closed when required attributes are missing.

## Backend Capability Model

Backends declare what they can accept through `BackendCapability`.

Capabilities include:

- Supported operation kinds.
- Supported tensor layouts.
- Produced tensor layouts.
- Backend memory domain.
- Preferred operation kinds.
- Whether the backend supports noise modeling.
- Whether calibration is required or supported.
- Maximum error budget constraints.

This lets the runtime reason about a backend without knowing its implementation.
Capability checks are pure data checks and must not execute backend plugin code.

Transfer-cost profiles can be supplied as validated declarative manifests. The
runtime uses them for transfer-edge estimates and candidate scoring without
executing backend code or trusting backend-provided behavior.

## Backend Lowering

Backends implement a minimal protocol:

- Expose capabilities.
- Lower a `ComputeGraph`.
- Return a `LoweringResult`.

The first backend is `LinearAlgebraSimulatorBackend`, a toy backend that accepts
linear algebra operations and emits a textual artifact.

## Runtime Partitioning

The early runtime uses simple rule-based partitioning:

1. Prefer backends that explicitly prefer an operation kind.
2. Otherwise choose any backend that supports the operation.
3. Break ties by minimizing cross-domain transfer bytes.
4. Otherwise fall back to the default backend, currently named `gpu`.

This is intentionally simple. Later phases can replace the rule set with richer
cost models, transfer estimates, noise simulation, and calibration-aware
scheduling.

Partition plans now expose backend assignments, memory domains, runtime transfer
edges, layout conversions, produced layouts, and estimated byte costs, so
runtime decisions stay inspectable.

Runtime transfer edges also carry coarse prototype bandwidth, latency, and
energy estimates, or estimates from a validated transfer-cost profile. These
estimates are deterministic planning data, not hardware certification claims.

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

The Python prototype exists to make those boundaries testable before native
compiler implementation begins.
