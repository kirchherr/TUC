# HAC-IR Semantic Charter

HAC-IR is TUC's hardware-independent compute-intent contract.

It exists to preserve what a workload means while giving the compiler enough
validated facts to plan across backend capabilities. It must not become a
container for backend implementation details, vendor promises, runtime handles,
or generated artifacts.

This charter separates HAC-IR data into four categories.

## 1. Compute Intent

Compute intent is the mathematical and tensor-level meaning of the workload.

HAC-IR may express:

- Operation family: `matmul`, `elementwise`, `reduction`, and `softmax`.
- Tensor identity, shape, dtype, inputs, and outputs.
- Operation linearity when it follows from the operation family.
- Semantic operation identity through `tuc.semantic_op`.
- User intent such as accepted error budget when validated and bounded.
- Softmax intent as a nonlinear operation family; decomposition into reduction
  and elementwise pieces is not HAC-IR semantics.

Compute intent must remain independent of backend assignment. A backend may be
better or worse for an operation, but it must not redefine what the operation
means.

## 2. Compiler Facts

Compiler facts are deterministic facts produced by TUC after validation.

HAC-IR may carry:

- `tuc.source_stage`
- `tuc.linearity`
- `tuc.operation_name`
- `tuc.arithmetic_ops`
- `tuc.bytes_read`
- `tuc.bytes_written`
- `tuc.arithmetic_intensity`
- `tuc.layout`
- `tuc.layout_tile_shape`
- `tuc.layout_alignment_bytes`
- `tuc.movement_notes`

Compiler facts must be reproducible from validated graph data and compiler
passes. They must not depend on backend code, host device state, environment
variables, subprocess output, network access, benchmark output, or generated
artifacts.

## 3. Planning Constraints

Planning constraints guide runtime placement without choosing a backend inside
HAC-IR.

HAC-IR may carry:

- `tuc.max_error_budget`
- `tuc.preferred_memory_domain`
- Abstract layout constraints.
- Movement estimates used by later runtime planning.

Planning constraints are not backend assignments. They may influence candidate
selection, but final placement belongs to runtime planning and HS-IR.

## 4. Forbidden Backend Details

HAC-IR must not carry:

- Backend assignment or produced backend layout.
- Vendor names, target architectures, or backend names.
- CUDA, HIP, Metal, photonic, neuromorphic, or other specialized placement
  targets.
- Device identifiers, device paths, runtime handles, queues, streams, or launch
  grids.
- Plugin entrypoints, import paths, dynamic libraries, backend binaries,
  generated artifacts, artifact output paths, or backend kernel names.
- Calibration evidence, benchmark results, measured performance, hardware
  certificates, device serial numbers, or backend-specific noise-model modules.

Backend hardware certificates are measured or governance artifacts, not HAC-IR
semantics.

These details belong, when allowed at all, to backend capability data,
transfer-cost profiles, HS-IR, runtime plans, backend implementation contracts,
or future sandboxed artifact/calibration schemas.

## Boundary Table

| Question | Belongs In HAC-IR? | Correct Home |
| --- | --- | --- |
| What operation is this? | yes | HAC-IR compute intent |
| What tensors does it consume and produce? | yes | HAC-IR compute intent |
| How many bytes does this operation read and write? | yes | HAC-IR compiler fact |
| What error budget did the workload request? | yes | HAC-IR planning constraint |
| Which backend should run it? | no | Runtime plan and HS-IR |
| What layout does the backend produce? | no | HS-IR and runtime plan |
| What vendor architecture is targeted? | no | Backend capability or backend lowering |
| What transfer profile estimates movement cost? | no | Transfer-cost profile |
| What generated artifact should execute? | no | Future sandboxed artifact contract |
| What calibration file proves device behavior? | no | Future calibration-artifact schema |
| How should softmax be decomposed for one backend? | no | Runtime plan, HS-IR, backend contract, or proof artifact |

## Review Rules

Every HAC-IR change must answer:

1. Is this compute intent, a compiler fact, or a planning constraint?
2. Can the value be validated before lowering?
3. Is the value deterministic and bounded?
4. Would the value still make sense if all current backends disappeared?
5. Could the value let a backend influence HAC-IR semantics?
6. Does the value introduce plugin discovery, imports, subprocesses, dynamic
   libraries, device access, network access, generated-artifact execution, or
   host-path leakage?

If the value is useful only for one backend family, it does not belong in
HAC-IR.

## Relationship To Existing Contracts

The executable v0 contract in `tuc.ir.dialect` enforces the current allowed
`tuc.*` attributes and rejects known hardware-leakage attributes through
`HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES`.

The neutrality checklist in `docs/HAC_IR_NEUTRALITY.md` is the reviewer-facing
approval checklist. This charter is the semantic reason behind that checklist.

Deterministic fixtures in `tests/golden/hac_ir/` make changes to proof and MVP
HAC-IR dumps visible during review. Updating those fixtures should be treated as
an intentional change to the hardware-independent interface contract.
