# Fixed multiplication and gating C11 conformance

This installed-wheel consumer emits four CPU-only graphs: rank-one `x*x`, a
matrix product element by element, an eight-operation gated MLP with Linear,
bias, ReLU, residual Add and row Sum, and mixed Linear/Mul/ordinary Matmul/Sum.
Its scalar FP32 oracle evaluates explicit equations independently of manifests.

On Linux x86-64 with an existing local Docker daemon, copy this directory outside
the checkout, activate an environment containing the intended installed TUC wheel,
and write its `sha256:<hex>` identifier to `wheel-sha256.txt`. Run:

```sh
python3 -I consumer.py
sh operator.sh --c11
```

The first command emits a candidate report without native execution. The operator
builds pinned static and ASan/UBSan containers, checks the observations, and writes
`record.json`. Each build performs 16 successful runs (four graphs, two datasets,
two replays), 131 entrypoint calls, 64 scalar checks, 16 publications, 115 expected
rejections and 459 unchanged-output checks. Signed-zero results are compared by
their binary32 bits.

There are 29 controls; input-input aliasing is inapplicable to the square graph's
single public input and is explicitly excluded. Controls cover descriptor
counts/extents, aliases, exceptional values, product overflow, subnormal products,
nonzero products rounded to zero, and the floating-point environment. In composed
graphs the numeric controls reach the explicit Mul after valid normal Linear and
bias results, so a later operation cannot hide its invalid intermediate. These
are entrypoint boundary tests; no binary-frame parser is added.

Three checker faults (wrong result, wrong status, output changed on rejection)
and an invalid invocation run for each build, producing ten observations total.
Crashes and sanitizer failures are rejected. Receipts bind the wheel identifier,
installed compiler files, consumer, generated sources and support files. This
prevents accidental mixing, not forged evidence. There is no CUDA execution,
new runtime admission, or performance claim.

[CI run 35589963541](https://github.com/kirchherr/TUC/actions/runs/35589963541)
observed all ten static/sanitized results at `ce70446`. The
[original receipt](../../docs/evidence/bounded-cpu-gating-35589963541.json)
retains context/binding/image identities and wheel/consumer hashes.
