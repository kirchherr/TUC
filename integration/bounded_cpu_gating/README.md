# Installed bounded CPU gating consumer

This independent standard-library client owns its source text, signatures,
input corpora, complete expected graphs and ordered FP32 references. It imports
no TUC modules. The explicit run uses installed `tuc-source-to-json` and
`tuc-cpu-app` consoles beside the current interpreter, outside the checkout.

```sh
# Inert reports and portable source/signature/input fixtures.
python3 -I consumer.py
python3 -I consumer.py --emit

# Explicit isolated source conversion and native CPU execution, using local Docker.
python3 -I consumer.py --run
```

Six programs cover vector products, elementwise `x*x` on non-square matrices,
and a ReLU-gated MLP, each in two shape profiles. The MLP computes
`value = Linear(x, wv, bv)`, `gate = ReLU(Linear(x, wg, bg))`, followed by
`Linear(value * gate, wo)`. One profile has seven operations; the second has an
eighth operation for the final output bias. Two changing datasets per program
require six source conversions, twelve successful CPU calls and 56 bitwise
FP32 scalar comparisons. The vector and square cases include signed zero.

Multiplication accepts two named rank-one or rank-two FP32 tensors with exactly
equal shapes and a fresh output of that shape. `x*x` has one public input and
two read-only operands. Scalar and broadcast multiplication are unsupported.
Each product and sequential accumulation is rounded separately to FP32 by the
independent reference. The MLP uses physical row-major `[N,K]` Linear weights,
separate bias additions and a ReLU gate. This is a bounded application example,
with no arbitrary model, PyTorch, SwiGLU, GPU or performance claim.

Ten negative controls cover scalar operands on either side, nested products,
division, power, a nested function call, row/column broadcasts, unequal matrix
shapes and vector broadcasting. Three numeric controls use only normal-or-zero
operands but produce overflow, a subnormal product or a nonzero product rounded
to zero. Each requires exact numeric rejection with empty stdout. These rejected
calls are separate from the twelve successful CPU runs.

The client checks complete converted graphs and typed public bindings, records
source/signature/graph/input hashes and reconstructs request digests. Program
identities must agree between inspection and both runs; it does not duplicate
the compiler's nine-file program hash algorithm. Original fixture bytes must
remain unchanged and workspaces empty after every command. It creates
`record.json` exclusively after every check passes, with schema
`tuc.bounded_cpu_gating_integration.v0`. Default reports and synthetic tests are
not native observations.

[CI run 35589963541](https://github.com/kirchherr/TUC/actions/runs/35589963541)
observed all six conversions, twelve successful calls, 56 scalar checks,
ten source and three numeric rejections at `ce70446`. The
[original receipt](../../docs/evidence/bounded-cpu-gating-35589963541.json)
also contains the separate static and ASan/UBSan entrypoint observations and
binds source revision, wheel and both consumers.

## Small gated MLP example

The [source](gated-mlp.py.txt), [signature](gated-mlp-signature.json) and
[inputs](gated-mlp-inputs.json) form a seven-operation network. Its value branch
is `[[2,-3],[4,3]]`, its ReLU gate is `[[0,4],[7,0]]`, and the final named output
is `{"scores":[-24.0,28.0]}`.

```sh
set -e
mkdir -m 700 work
tuc-source-to-json gated-mlp.py.txt --signature gated-mlp-signature.json --workspace work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs gated-mlp-inputs.json --workspace work
```

Source stays data inside the isolated parser worker; do not run the fixture
with Python. Existing bounded CPU shape, operation, work, storage and numerical
constraints remain in force. Earlier consumers and observations keep their
original scope.
