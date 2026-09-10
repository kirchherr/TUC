# RFC 0306: Bounded Reduction CUDA Proof

## Status

Accepted as a bounded research observation on 2026-09-10 after physical sm86
execution, exact reference agreement and three wrong-code rejections.
Observed source commit: `10d29e01e7d7a7676504c918a4bf9d931edb0495`.
Repository merge approval remains a separate maintainer decision.

## Decision

Execute RFC 0305's unchanged Matmul-plus-axis-1-Sum source intent on a second
compiler target: fixed NVIDIA sm86 CUDA/SASS. Reuse the exact source validator,
input vector and independent expected results, but emit thread-indexed CUDA
kernels rather than C11 host loops. Preserve negative terminal values and the
rank-changing output. Require a no-call preflight, exactly two generated
function launches, exact reference agreement and three wrong-code rejections.

The operator is separate from the normal executor. No plugin API, IR type,
source intake permission, runtime backend or release dependency is added.

## Alternatives

Re-running C11 on another host would test reproducibility but would not test
a different compiler target. Extending the existing ReLU GPU proof without
changing terminal semantics would not exercise reduction. Arbitrary source
or dynamic shapes would exceed the current review and execution boundary.

## Evidence

The worker reports source-intent, vector and generated-code digests, shape,
allocation and call counts, security facts and reference status. The explicit
operator records its image ID and source-file binding. Both children pass
their strict validators before a metadata-only equivalence report is built.
This is same-maintainer observation, not independently signed provenance.

Procedure, threat boundaries, exclusions and acceptance status:
`docs/BOUNDED_REDUCTION_CUDA_PROOF.md`.
