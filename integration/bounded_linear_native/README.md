# Fixed Linear C11 conformance

This installed-wheel consumer emits four CPU-only checked entrypoints: nonsquare
`X[2,3] @ W[4,3].T`, singleton `X[1,1] @ W[1,1].T`, mixed Linear/ordinary Matmul
with row reduction, and a two-layer Linear/bias/ReLU/residual graph with reduction.
The fixed oracle evaluates scalar FP32 equations independently of manifests.

On Linux x86-64 with a local Docker daemon, copy this directory outside the
checkout, activate an environment containing the intended installed TUC wheel,
and write that wheel's `sha256:<hex>` identifier to `wheel-sha256.txt`. Run:

```sh
python3 -I consumer.py
sh operator.sh --c11
```

The first command only emits a candidate report. The operator builds pinned
static and ASan/UBSan containers, checks all observations and writes `record.json`.
It performs 16 successful runs (four graphs, two datasets, two replays), 132
entrypoint calls, 56 scalar checks, 16 publications, 116 expected rejections and
406 unchanged-output checks per build. The 29 rejection controls cover exact
descriptor extents/counts, aliases, special values, rounded product overflow,
subnormal products, nonzero products rounded to zero, and the FP environment.
This checks the native entrypoint boundary; it introduces no binary-frame parser.

Each build also runs three checker faults (wrong result, wrong status, changed
output on rejection) and an invalid invocation, for ten observations total.
Unexpected crashes and sanitizer reports are rejected. The receipts bind the
wheel identifier, installed compiler files, consumer, support files and emitted
sources. This prevents accidental mixing, and is not cryptographic authentication.
There is no CUDA execution, new runtime admission, or performance claim.
