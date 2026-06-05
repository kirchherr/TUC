# MVP Kernels

The first TUC kernel set is intentionally small. It exists to validate compiler
and runtime boundaries before performance work begins.

## Kernel Families

| Family | Why It Matters | Phase 1 Scope |
| --- | --- | --- |
| MatMul | Core operation for attention, MLPs, and linear projections. | Represent in TLIR, normalize into HAC-IR, assign to simulator or GPU fallback. |
| Elementwise | Activations, scaling, bias, masking, and simple nonlinear work. | Represent and keep on fallback backend unless a backend explicitly supports it. |
| Reduction | Sums, norms, statistics, and softmax components. | Represent as linear-friendly HAC-IR where possible. |
| Softmax-like | Common transformer workload and useful partitioning boundary. | Model as an operation family; detailed decomposition is future work. |

## Phase 1 Success Criteria

- Each family has a stable `OperationKind`.
- Each family can appear in a `ComputeGraph`.
- Hints can be attached as metadata without changing correctness.
- The pipeline can dump TLIR, HAC-IR, and HS-IR views.
- Backend assignment decisions are visible in HS-IR.

## Out Of Scope

- Vendor-level performance.
- Full Triton AST capture.
- Real CUDA/HIP lowering.
- Full decomposition of softmax into reductions and elementwise operations.

## Next Kernel Work

The next useful slice is a golden-kernel suite with small tensor shapes and
reference NumPy/PyTorch results. That suite should become the first correctness
gate before native MLIR lowering starts.
