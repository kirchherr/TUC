# Run Linear layers with row-major weights

The bounded CPU path now accepts `X[M,K]` and weights `W[N,K]` directly for
`X * W^T + bias`. Keep each output feature's weights together in one row;
there is no need to transpose the input array before running the graph.

Use the installed wheel, Linux x86-64 and existing local Docker prerequisites
from the [source-to-CPU guide](BOUNDED_CPU_SOURCE.md). Save this source as
`linear.py`; the converter treats it as data inside its isolated parser.

```python
import triton
import triton.language as tl

@triton.jit
def linear(x, weight, bias, y):
    projected = tl.dot(x, tl.trans(weight))
    scores = projected + bias
    tl.store(y, scores)
```

Write `signature.json`:

```json
{"schema_version":"tuc.bounded_cpu_source.v0","source_name":"linear_example",
"kernel_name":"linear","tensor_shapes":{"x":[2,3],"weight":[2,3],"bias":[2],"y":[2,2]}}
```

Write `inputs.json`, with two unchanged weight rows `[1,0,2]` and `[-1,2,1]`:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{
"x":[1,2,-1,0,3,2],"weight":[1,0,2,-1,2,1],"bias":[0.5,-1]}}
```

```sh
set -e
mkdir -m 700 parse-work cpu-work
tuc-source-to-json linear.py --signature signature.json --workspace parse-work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs inputs.json --workspace cpu-work
```

Expected output: `{"y":[-0.5,1.0,4.5,7.0]}`. Inputs and outputs are flat
row-major arrays. `inspect` exposes the physical weight shape and deterministic
program identity; replacing numeric values preserves the graph and changes the
request identity.

In graph JSON, the Matmul operation uses `"attributes":{"rhs_transposed":true}`.
Absence means ordinary Matmul. The marker accepts only exact `true`, and only
on Matmul. Both operands must be rank-two FP32 with matching final dimensions.
The source spelling accepts only the direct right-hand `tl.trans(name)` shown
above. Separate transpose assignments, left transpose, member syntax, `.T`,
axis arguments and arbitrary nested expressions are unsupported.

Bias, ReLU and further normal/transposed Matmuls can be composed using the same
eight-operation and dimension 1-64 bounds. Every rounded product and sum uses
the existing checked FP32 contract. This extension currently uses one selected
C11 CPU backend.

The weight orientation is consistent with the
[documented Linear convention](https://docs.pytorch.org/docs/2.14/generated/torch.nn.Linear.html),
but this interface consumes explicit bounded source/JSON and arrays, not
PyTorch objects or model checkpoints. See [RFC 0328](../rfcs/0328-bounded-cpu-linear.md)
and the [independent installed consumer](../integration/bounded_cpu_linear/README.md).
Actual installed/native validation is pending.
