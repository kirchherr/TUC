# TUC Architecture

TUC is organized around a small number of compiler and runtime boundaries.

## Frontend

The frontend preserves Triton-style developer ergonomics. During the early
prototype phases, frontend work is represented by `CompilationHints`: optional
metadata such as noise robustness, sparsity preference, analog linear
preference, and error budgets.

Hints must never change mathematical correctness. They only inform lowering,
tuning, partitioning, and diagnostics.

The first frontend adapter accepts Triton-like kernel metadata as declarative
data and converts it into `ComputeGraph`. It does not parse Python source,
execute `@triton.jit` functions, import user modules, or trust reserved `tuc.*`
attributes from frontend input.

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

HAC-IR also has an explicit v0 dialect contract in `tuc.ir.dialect`. It defines
the MVP operation family, future `tuc_hac.*` MLIR operation names, arity bounds,
required compiler-produced attributes, optional compiler attributes, and
fail-closed handling for unknown reserved `tuc.*` attributes. The compiler
validates HAC-IR immediately after TLIR lowering and again before HAC-IR is
specialized into HS-IR.

HS-IR has a matching v0 contract in the same module. It requires backend
assignment metadata to exactly match operations, requires every operation to
carry `tuc.assigned_backend` and `tuc.produced_layout`, validates produced
layouts against the layout vocabulary, and checks movement/runtime-transfer
summaries for finite non-negative values and internal byte-total consistency.

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

Schema-versioned JSON manifests are loaded through `tuc.manifests`. Manifest
loading is explicit, bounded, duplicate-key rejecting, and does not scan for or
execute backend plugins.

`tuc.backends.registry` adds an explicit backend capability registry. It accepts
trusted in-memory capabilities or caller-provided manifest paths, enforces
unique bounded backend names, and exposes capability tuples for partitioning.
It also emits compact pure-data support diagnostics explaining why a backend
accepts or rejects an operation. It does not perform directory scanning,
entry-point discovery, imports, device access, backend lowering, or artifact
execution.

Backend API v0.1 is documented in `docs/BACKEND_API.md`. It is an authoring
contract for trusted in-process prototypes and declarative manifests, not a
plugin ABI. TUC does not auto-discover backends or execute backend code during
capability checks, manifest loading, IR validation, partitioning, or dumping.

Backend conformance fixtures in `tuc.backends.conformance` check that trusted
prototype backends lower only operations accepted by their capability data,
reject unsupported operations, and return bounded, inspectable artifacts and
diagnostics.

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

The first MLIR design spike is a parseable unregistered-dialect artifact under
`examples/mlir/`. It maps current HAC-IR concepts toward `tuc_hac` syntax while
deliberately avoiding native C++ dialect code, external MLIR ingestion, or pass
execution.

The current Python HAC-IR and HS-IR dialect contracts are the reviewable source
of truth for future MLIR ODS/TableGen work until native dialect code is
explicitly hardened.
