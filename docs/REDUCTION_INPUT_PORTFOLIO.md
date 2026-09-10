# Reduction Input Portfolio

RFC 0307 tests the unchanged generated reduction functions from RFCs 0305 and
0306 with twenty fixed inputs instead of one. Shapes remain A[4,8], B[8,2]
and y[4]; the operation remains `sum(A @ B, axis=1)`.

The corpus includes the previous baseline, zero A, negated A, half A, swapped
B columns, reversed A rows, cancelling B columns, eight inner-dimension basis
probes and five deterministic small mixed-sign cases. Quarter-integers in
[-4,4] keep products and intermediate sums exactly FP32-representable. A
rational Python oracle and differently structured binary64 native reference
agree with the expected values. This is numeric equality, not signed-zero
bitwise equivalence or arbitrary floating-point coverage.

Each target compiles once. Its one process executes all twenty vectors and
then repeats the baseline, with buffers reused between cases: 21 executions,
42 generated calls. CUDA allocates 240 tensor bytes once; the 240-byte
per-case metric excludes the resident host corpus, expected-value tables,
CUDA context, driver and executable overhead. The corpus plus reference
tables occupy 4,160 bytes of float storage before compiler optimization.

## Run

With the existing Linux Python dependencies:

```bash
PYTHONPATH=.:src python3 examples/reduction_input_portfolio.py
sh scripts/run_reduction_input_portfolio.sh --c11
sh scripts/run_reduction_input_portfolio.sh --cuda-reviewed
```

Review driver/toolkit security updates and shared GPU use before the last
command. The first command is pure verification; it does not execute kernels.
The two procedures retain metadata-only observations in their printed private
temporary directories. Compare their `record.json` files:

```bash
PYTHONPATH=.:src python3 examples/reduction_input_portfolio.py --compare CPU_RECORD GPU_RECORD
```

Every target requires zero-call preflight, all cases and the replay, plus four
compiled wrong-code rejections. The new frozen-output mutant returns the old
baseline result regardless of the inputs: it must pass the baseline and fail
at the zero vector. The three prior mutants must still fail at the baseline.
C11 additionally executes all cases under ASan/UBSan. No GPU sanitizer result
is claimed. Mutation observations are never accepted as execution evidence.

## Boundary And Status

Implementation ready for actual observation; acceptance is pending native
C11 and physical CUDA execution. The old single-vector records are unchanged.
Fresh artifact checks require byte-identical generated C11 and CUDA functions.
No dynamic inputs, shapes, parsing permissions, backend API or executor path
are introduced. Native harnesses share reference/report code, so the separate
Python rational and NumPy checks remain important against common-mode errors.

Runtime isolation retains the previous non-root, no-network, no-host-mount,
read-only, no-capabilities, no-new-privileges, seccomp and resource controls.
Builds are pinned and networkless after base-image resolution. Host drivers,
Docker and toolkits remain trusted. Docker RAM limits do not bound VRAM;
deadlines cannot guarantee recovery from a GPU driver hang. No services or
drivers are updated and no other workloads are stopped by this procedure.

Image IDs and source digests record operator provenance, not signed or
independent attestation. Hosted CI can execute C11 and revalidate stored CUDA
records but cannot claim a new physical GPU observation. Twenty vectors do
not prove correctness for all inputs, other shapes, vendors, performance or
production use. Next: one additional bounded shape with fresh lowering and
actual execution on both targets.
