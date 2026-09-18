# Installed checked C11 entrypoint client

This standalone client emits two graph functions through public installed TUC
APIs: the earlier seven-operation application and a small Matmul/Sum graph.
It links both into one executable and calls their generated public buffer ABI.
It does not implement either graph's native scheduling or arithmetic.

Independent scalar FP32 references check three corpora and two replays per graph.
The rejection suite checks caller descriptors, overlap, numerical edge cases and
floating-point environment, with unchanged sentinel outputs on every error.
Static and ASan/UBSan builds run the same closed suite. Three driver fault builds
ensure result, status and sentinel failures are detected.

Each successful build records 12 case runs, 414 entrypoint calls, 42 scalar
comparisons and 18 published outputs, plus 402 rejected calls and 2412 unchanged
output sentinel checks. Positive calls also verify unused output tails and
unchanged input/descriptor snapshots. These are fixed-suite expectations;
only accepted receipts from actual native execution establish observations.

The complete installation and execution procedure is in the
[dedicated workflow](../../.github/workflows/bounded-c11-entrypoint.yml). It builds
and installs a wheel, copies this directory outside the checkout, verifies the
isolated import path, and writes the exact wheel digest into `wheel-sha256.txt`.
For manual use, prepare that same separate environment and client copy first.

```sh
# Pure candidate report and fresh inert build context.
python3 -I consumer.py
python3 -I consumer.py --emit

# Explicit fixed native test, on Linux x86-64 with Docker.
sh operator.sh --c11

# Pure acceptance of captured receipts and the original context.
python3 -I consumer.py --accept tmp/bounded-c11-entrypoint.<suffix>
```

Keep the wheel environment on `PATH`; the sidecar contains one
`sha256:<64 lowercase hex>` line. The operator prints a private evidence
directory and writes `record.json` only after both real builds, negative controls,
driver falsifications, invalid-argument checks and source/context binding pass.
Candidate metadata and synthetic unit-test receipts are not native observations.

There is no runtime graph parser, arbitrary input stream, plugin loader,
device access or native launch in the Python client. The new compiler artifact
is inert and does not establish general native runtime admission or performance.
