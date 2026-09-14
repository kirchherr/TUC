# Bounded Reduction Shapes

RFC 0308 adds a shape dimension to the executed reduction experiment, not a
new general-purpose backend. The same inert source and neutral operation pair
`sum(A @ B, axis=1)` now lower for two explicitly allowlisted profiles:

| Profile | A | B | Projection | Output |
| --- | --- | --- | --- | --- |
| Previous baseline | 4x8 | 8x2 | 4x2 | 4 |
| New odd shape | 33x7 | 7x5 | 33x5 | 33 |

The new pure emitter reproduces the old baseline code byte for byte. The
odd shape needs new row/column strides, seven inner terms, five reduction
terms, six projection blocks and two output blocks on CUDA (32 threads per
block). Both kernels have excess launched threads which must not access
logical elements. Runtime launch parameters come from the generated plan.

Twenty fixed vectors cover zero inputs, sign, row and column permutation,
inner-dimension basis probes, a last-row-only case and six deterministic mixed
cases. A final baseline replay gives 21 executions and 42 generated calls per
target. Values are quarter-integers in [-4,4]; all tested FP32 intermediates
are exact. Rational Python and separately structured binary64 native
references agree with NumPy. This does not cover arbitrary FP32 rounding,
signed-zero bitwise semantics or all inputs in the numeric domain.

## Run

With the existing Linux Python dependencies and Docker:

```bash
PYTHONPATH=.:src python3 examples/bounded_reduction_shapes.py
sh scripts/run_bounded_reduction_shapes.sh --c11
sh scripts/run_bounded_reduction_shapes.sh --cuda-reviewed
PYTHONPATH=.:src python3 examples/bounded_reduction_shapes.py --compare CPU_RECORD GPU_RECORD
```

The first and last commands only validate data. Operator procedures build
reviewed images and execute native code; the GPU command requires a current
driver/toolkit security review and an available sm86 compute device. Examples
do not discover or register a CUDA backend in the normal executor.

Each target must pass a zero-call preflight, all twenty vectors and replay,
and three actually compiled wrong-code controls. Missing accumulation and a
wrong B stride must fail on the first case. The coverage control omits the
last CPU row or launches only one GPU block. NaN initialization makes missing
writes observable without relying on prior memory contents. This checks
logical coverage, not general GPU memory safety. C11 also runs ASan/UBSan.

## Security And Evidence

The same non-root, single-device, no-network, no-host-mount, read-only,
capability-free, no-new-privileges and seccomp controls remain. CUDA kernels
are AOT SASS-only with PTX JIT disabled. All four device buffers total 1,856
bytes; this excludes host corpus/reference tables (23,920 float-storage bytes),
CUDA context and driver overhead. Container RAM limits do not bound VRAM;
timeouts do not guarantee recovery from a GPU driver hang. The procedure does
not update drivers, restart services or stop other workloads.

Review [NVIDIA driver bulletins](https://nvidia.custhelp.com/app/answers/detail/a_id/5821)
and [toolkit bulletins](https://nvidia.custhelp.com/app/answers/detail/a_id/5850)
before GPU use; these links are a baseline, not a claim that future advisories
are absent. Docker, the toolkit, compiler and host driver remain trusted.

Observation loading uses the existing strict bounded JSON reader; records
omit raw values, timings, host identity and paths. Image and source hashes
bind operator-reported provenance, not independent cryptographic attestation.
Old golden files are unchanged. Shared native oracle code remains a
common-mode risk, mitigated but not eliminated by Python rational/NumPy tests.

## Status

Actual native C11 and physical sm86 CUDA execution passed on 2026-09-14:
twenty cases plus baseline replay, 42 generated calls per target, exact
agreement for all 33 outputs, zero-call preflight and all three wrong-code
rejections. C11 also passed ASan/UBSan. Both incomplete-coverage variants
failed at run index 0 with a reference mismatch after two generated calls.

Tested source commit: `c1cca5db79ab9cbbac60522a5bbea968b455bb1b`.
Transferred source archive SHA-256:
`b47228abb3a9506bd184ad04badc939c3dd955ecb7a7e81a4b325c4777f23a82`.
The archive contains that commit's `src`, `examples`, `docker`, `scripts`,
`schemas` and `tests/golden` trees. Observed program files remain unchanged;
subsequent changes add evidence, regression enforcement, CI and documentation.

Accepted files under `tests/golden/proofs/`:

- `reduction_shape_c11_record.json`
- `reduction_shape_cuda_record.json`
- `reduction_shape_equivalence.json`
- `reduction_shape_c11_incomplete_coverage.json` (rejection, never a PASS child)
- `reduction_shape_cuda_incomplete_coverage.json` (rejection, never a PASS child)

Hosted CI executes C11 and revalidates stored GPU records, not a new
physical GPU run. A second shape does not prove dynamic shape support,
performance, cross-vendor portability, production readiness or independent
reproduction.

Next: exercise non-exact FP32 inputs under an explicit rounding/error contract
on both targets, keeping the current fixed-shape and execution boundaries.
