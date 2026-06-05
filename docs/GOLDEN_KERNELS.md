# Golden Kernel Correctness

TUC now has a small deterministic golden-kernel suite for the MVP operation
families.

## Scope

The suite covers:

- MatMul.
- Elementwise ReLU.
- Sum reduction.
- Softmax.

Fixtures live under `tests/golden/kernels/` and are compared against NumPy
reference kernels in `tuc.reference`.

## Why This Exists

Runtime plans and IR dumps can prove that TUC is making inspectable compiler
decisions. They do not prove that the operation families keep their mathematical
meaning. The golden-kernel suite is the first correctness gate before native
MLIR lowering or backend-specific execution is added.

## Security Rules

Reference kernels are deliberately narrow:

- Inputs must be NumPy arrays, not arbitrary array-like objects.
- Arrays must be numeric, finite, bounded in rank, and bounded in element count.
- Object dtypes are rejected.
- No backend plugin code, subprocesses, generated code, or device runtime is
  executed.
- Golden fixtures are repository-owned JSON files with small fixed values.

## Current Limitations

This is not a benchmark suite and does not claim hardware accuracy. It is a
small semantic reference suite for the MVP operation families.

Future work can add dtype-specific tolerances, decomposition checks, and backend
execution comparisons once backend execution exists.
