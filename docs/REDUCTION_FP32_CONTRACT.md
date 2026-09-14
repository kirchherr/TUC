# Bounded FP32 Reduction Contract

RFC 0309 tests a question absent from the exact quarter-integer experiments:
can the same compute intent satisfy an explicit numerical contract on a
native CPU and GPU when arithmetic actually rounds?

This is still the fixed inert Triton-shaped `sum(A @ B, axis=1)` source,
A[33,7], B[7,5], y[33]. The emitted C11/CUDA files and separate allocation/
launch harnesses are reused byte for byte from RFC 0308. No parser extension,
source execution, normal-runtime admission or general CUDA backend is added.

## Contract Before Measurement

Ten fixed rational input recipes cover decimal fractions, signs, cancellation,
small and large scales, reciprocal scaling, mixed magnitudes, zero and a
last-row-only case. They are rounded once to binary32, ties to even, using
integer/rational arithmetic. Hexadecimal C literals preserve those bits.
The reference is the exact real result of these **binary32 inputs**, not of
the original decimal recipes. Input conversion error is outside the arithmetic
budget. A final first-case replay gives 11 runs and 22 generated calls per
target, 363 scalar output checks.

For output row r define, in exact rational arithmetic:

```text
u       = 2^-24
gamma13 = 13*u / (1 - 13*u)
S_r     = sum_k sum_c abs(A[r,k] * B[k,c])
R_r     = sum_k A[r,k] * sum_c B[k,c]
E_r     = gamma13 * S_r
accept iff finite(y_r) and abs(y_r - R_r) <= E_r
```

Derivation: each product's contribution traverses at most one product
rounding, seven sequential projection additions and five output additions.
Under normal-range, round-to-nearest arithmetic, each operation contributes
a factor (1+delta), |delta| <= u. A path has at most 13 such factors; the
standard product bound gives |product(1+delta)-1| <= gamma13. Summing absolute
term contributions gives E_r. This is a conservative forward absolute bound,
not a measured tolerance or a relative-accuracy promise under cancellation.

Python checks every intermediate of the specified operation order is zero
or within [2^-100,2^100] in magnitude. C11 disables contraction, reassociation
and excess precision; CUDA disables FMA contraction and flush-to-zero.
Preflight checks host binary32/binary64 formats and nearest rounding. This
does not establish IEEE conformance for arbitrary compilers or inputs.

Exact interval endpoints R_r +/- E_r are serialized as binary64 values
rounded **inward**. Converting a finite binary32 output to binary64 is exact,
so native interval comparisons cannot enlarge the rational budget. The
binary64 lattice is finer than binary32, so inward rounding cannot exclude
an admissible binary32 output. Zero-budget zero outputs remain exact.

The separate binary64-rounded reference table is only a rounding witness:
outputs differing from it necessarily differ from the exact rational answer.
At least one such output is required; its count is not the acceptance
criterion. No tensor values or value digests enter observation JSON.

## Checks And Boundaries

- Exact rational reference, operation-ordered integer-rounding simulation and
  independently evaluated NumPy results check the corpus before native use.
- Both targets must pass the full corpus and replay inside the same intervals.
- Missing sum, wrong stride and incomplete coverage must still fail.
- A separate harness probe moves output 0 one FP32 step beyond the upper
  budget endpoint; another injects infinity. Both must fail on the first run.
- C11 also executes under ASan/UBSan. This is not GPU sanitization.

The comparison proves both reported executions satisfy the same bounded
contract. By the triangle inequality their pairwise difference is at most
2*E_r. It does **not** claim bitwise equality or a pairwise E_r bound.
NaN/infinity are rejected; signed zeros use numerical equality only.

Shared generated oracle tables remain a common-mode risk, mitigated by
independent tests, not eliminated. Self-reported observations are not signed
attestation or independent reproduction. Old proof files are unchanged.

## Run

```bash
PYTHONPATH=.:src python3 examples/reduction_fp32_contract.py
sh scripts/run_reduction_fp32_contract.sh --c11
sh scripts/run_reduction_fp32_contract.sh --cuda-reviewed
PYTHONPATH=.:src python3 examples/reduction_fp32_contract.py --compare CPU_RECORD GPU_RECORD
```

Pure commands only read bounded data. Native procedures require explicitly
reviewed Linux Docker execution; GPU use additionally requires an available
sm86 device and current host security review. Build context is deny-by-default
and copies only allowlisted files. Images remain digest-pinned, UID/GID 10001,
read-only, networkless, mount-free, capability-free and resource bounded.
CUDA remains AOT SASS-only with PTX/JIT disabled and one compute-only device.
Four tensor buffers total 1,856 bytes; host tables and driver/context memory
are additional. Docker RAM limits do not bound VRAM. Deadlines cannot
guarantee recovery from driver hangs. No services or drivers are changed.

See [the existing host-risk boundary](BOUNDED_REDUCTION_SHAPES.md#security-and-evidence)
and the current [driver](https://nvidia.custhelp.com/app/answers/detail/a_id/5821)
and [toolkit](https://nvidia.custhelp.com/app/answers/detail/a_id/5850) bulletins.

## Status

Actual native C11 and physical sm86 CUDA execution passed on 2026-09-14.
Both targets passed all ten cases and replay: 363 scalar output checks,
298 outputs differing from the binary64-rounded exact reference, 22 generated
calls, zero-call preflight and all five negative controls. C11 also passed
ASan/UBSan. Test containers exited and the GPU returned to idle occupancy;
no other workloads, services or drivers were changed.

Tested source commit: `0d813135048642e91e89c130660696d4f38ac98c`.
Transferred archive SHA-256:
`5568b7595810ddef78ff63338d9f81e272a2a7b02a6923669be15588f0e49fcb`.
The archive contains that commit's `src`, `examples`, `docker`, `scripts`,
`schemas` and `tests/golden` trees. Subsequent changes only add observations,
regression enforcement, CI and documentation; observed program files are
unchanged.

Accepted evidence: `tests/golden/proofs/reduction_fp32_comparison.json`,
two `reduction_fp32_{c11,cuda}_record.json` children, and five actual negative
observations per target. Hosted CI executes C11 and revalidates stored GPU
records; it does not run a physical GPU.

Next: an explicitly reviewed FMA-enabled target variant under this same
reference/error bound, to test numerical implementation freedom rather than
merely adding more vectors. Arbitrary inputs, dynamic shapes, native runtime
admission, performance parity and independent reproduction remain open.

## Numerical References

- [NVIDIA: Floating Point and IEEE 754](https://docs.nvidia.com/cuda/floating-point/index.html)
  explains rounding, operation ordering, FMA and compiler controls.
- [Higham and Mary, A New Approach to Probabilistic Rounding Error Analysis](https://eprints.maths.manchester.ac.uk/2673/1/paper.pdf)
  summarizes the classical deterministic gamma_n framework. This experiment
  uses that deterministic bound, not the paper's probabilistic improvement.
