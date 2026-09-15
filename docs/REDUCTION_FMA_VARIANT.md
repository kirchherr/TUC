# Bounded FMA Variant

RFC 0310 asks whether two explicitly different numerical implementations of
the same intent can produce different answers while satisfying unchanged
accuracy requirements on a native CPU and GPU.

## What Changes

The fixed inert source, A[33,7], B[7,5], y[33], ten binary32 input vectors,
exact rational reference and gamma13 error intervals from RFC 0309 remain
unchanged. Docker copies the existing inputs/oracle headers directly. The
existing generated separate-multiply/add code is also unchanged.

A bounded emitter derives a second version from the same validated Source
Intent, with explicit C11 `fmaf` or CUDA `__fmaf_rn` for projection accumulation.
Column reduction stays sequential binary32 addition. Automatic contraction,
reassociation, fast math and flush-to-zero stay disabled. C11 calls the
standard library; it does not claim a specific CPU FMA instruction. GPU
build checks require FFMA in the candidate projection's SASS and none in the
baseline projection. PTX/JIT remains disabled.

**Same error bound is not the same execution policy.** RFC 0309's contract
explicitly specifies separate operations. Its digest and files are preserved,
not silently reinterpreted. This experiment adds a distinct execution-policy
artifact and digest while binding the unchanged acceptance-interval artifact.
This is an explicit native research exception, not permission for a normal
backend to ignore a no-FMA request or a change to Source Intent semantics.

## Why The Bound Still Holds

An FMA rounds an exact product-plus-accumulator only once. Each term in this
fixed expression passes through at most seven FMA rounds and five reduction
rounds. The existing 13-round path bound is therefore still conservative.
All fixed-corpus intermediates in both policies are checked with exact
rational arithmetic and integer ties-even rounding to remain normal or zero.
No tolerance is selected from measured native errors.

The two policies are simulated separately before execution. Every native
output must both lie inside the unchanged rational-reference interval and
match its policy-specific ordered binary32 oracle. The latter check tests
that the declared numerical policy was followed on these vectors; it is
not a universal bitwise-equivalence contract. Results may legitimately differ
between policies. Their pairwise deviation is bounded by twice the original
per-output error budget.

## Paired Execution

Each run executes the baseline and FMA candidate back to back using the same
inputs. GPU buffers are reused, but projection/output storage is poisoned
before each evaluation and synchronized before reading outputs. Ten cases
plus replay mean 44 generated calls and 726 scalar checks per target.
Both variants must reproduce their own first-case outputs on replay.

Before native measurement the rational simulator predicts 61 differing
outputs out of 363 pairs, with 298 rounding witnesses per variant. The
observed counters must match; raw runtime values never enter the JSON report.
These aggregate observations do not establish general compiler correctness.

Six compiled controls must fail on the first run: missing sum, wrong stride,
incomplete coverage, finite over-budget perturbation, infinity and
`separate-as-fma`. The final control still satisfies the numerical budget but
must fail the declared-policy check, exposing silent fallback. C11 also runs
under ASan/UBSan; no GPU-sanitizer claim is made.

## Run And Security

```bash
PYTHONPATH=.:src python3 examples/reduction_fma_variant.py
sh scripts/run_reduction_fma_variant.sh --c11
sh scripts/run_reduction_fma_variant.sh --cuda-reviewed
PYTHONPATH=.:src python3 examples/reduction_fma_variant.py --compare CPU_RECORD GPU_RECORD
```

Verification is pure bounded data processing. Only explicit operator commands
build/run native code. The [RFC 0309 isolation and host-risk boundaries](REDUCTION_FP32_CONTRACT.md#run)
apply unchanged: digest-pinned builds, deny-by-default build context,
non-root UID/GID 10001, no network/host mounts, read-only root, dropped
capabilities, no-new-privileges, seccomp, bounded RAM/PIDs/tmpfs and deadlines.
One compute-only sm86 device is exposed. Four device buffers total 1,856 bytes;
additional host tables, output/replay arrays and driver memory are excluded.
RAM limits do not cap VRAM, and deadlines cannot recover a driver hang.

Exact-oracle generation remains a common-mode risk. Regression checks include
a cancellation example where FMA retains a term lost by separate rounding.
Image/source hashes and observations are same-maintainer provenance, not
independent reproduction or signed attestation. There is no new input surface,
dependency, core runtime admission, general native backend or performance claim.

## Status

Actual native C11 and physical sm86 CUDA execution passed on 2026-09-14.
Each target performed 726 scalar checks in 44 generated calls: both policies
satisfied the unchanged intervals, with exactly 61 differing output pairs
and 298 rounding witnesses per policy. Both replay checks and all six
negative controls passed; the silent-fallback control failed with
`execution_policy_mismatch`, not a widened or violated numerical budget.
C11 also passed ASan/UBSan; the CUDA build passed the per-kernel SASS checks.
Test containers exited and GPU occupancy returned to its initial idle level.
No other workloads, host services or drivers were changed.

Tested source commit: `e65af416fc7e72948a773d6b6becd382dee31d38`.
Transferred archive SHA-256:
`89ff5f38f19fed67d82bdcf2effa0da26deac05fdaddef7ccb6cb2f0f92269d3`.
The archive includes that commit's `src`, `examples`, `docker`, `scripts`,
`schemas` and `tests/golden` trees. Later changes only add actual records,
regression enforcement, CI and documentation; observed program files are
unchanged.

Accepted comparison: `tests/golden/proofs/reduction_fma_comparison.json`,
with two `reduction_fma_{c11,cuda}_record.json` children and six actual
negative observations per target. A separate bounded CI job runs the C11
pair and revalidates stored GPU evidence, without a hosted physical GPU run.

Next: connect the reviewed primitives into a bounded source-derived
Matmul -> ReLU -> reduction chain, carrying explicit numerical policy through
lowering and real two-target execution. More vectors or general-purpose
evidence gates alone do not close that composition question.

## References

- [C11 committee draft N1570, section 7.12.13.1](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf)
  defines single-rounding `fmaf` semantics under the current rounding mode.
- [NVIDIA single-precision intrinsics](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__SINGLE.html)
  defines the explicit round-to-nearest-even device intrinsic.
- [NVIDIA floating-point guide](https://docs.nvidia.com/cuda/floating-point/index.html)
  explains how FMA and operation order can change results.
