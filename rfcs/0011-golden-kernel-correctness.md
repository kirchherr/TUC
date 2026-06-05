# RFC 0011: Golden Kernel Correctness Suite

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds deterministic NumPy reference kernels and small JSON golden fixtures for
the MVP operation families. The suite checks semantic correctness separately
from runtime planning, backend assignment, and backend artifact generation.

## Motivation

IR and runtime plan dumps are necessary but not sufficient. TUC also needs a
stable correctness gate for the mathematical meaning of its MVP kernel families
before native MLIR lowering or backend execution paths are introduced.

## Decision

Add `tuc.reference` with bounded reference kernels for:

- MatMul.
- Elementwise kernels.
- Sum reduction.
- Softmax.

Add golden JSON fixtures under `tests/golden/kernels/` and a test suite that
compares reference output against those fixtures.

## Security Model

Reference kernels accept only NumPy arrays, not arbitrary array-like objects.
Inputs must be numeric, finite, rank-bounded, and element-count-bounded.

The suite does not execute backend plugin code, import user-selected modules,
spawn subprocesses, run generated code, or touch accelerator runtimes.

## Consequences

- The MVP operation families now have a semantic correctness gate.
- Future native lowering work can compare backend output against the same
  references.
- Golden fixture changes become review-visible correctness-contract changes.

## Follow-Up

1. Add dtype-specific tolerances once dtype lowering is implemented.
2. Add backend execution comparisons once executable backends exist.
3. Add decomposition-specific golden cases for softmax and reductions.
4. Add property-based tests for reference kernels once the MVP semantics settle.
