# Run affine layers and a small MLP on CPU

The installed source converter and CPU application now support tensor addition
and a right-hand row bias. This enables affine projections, residual sums and
small MLP graphs with caller-provided weights. The example below computes
`ReLU(x @ w1 + b1) @ w2 + b2` using five bounded operations.

Use the Linux x86-64, installed wheel and local Docker setup in the
[source-to-CPU guide](BOUNDED_CPU_SOURCE.md). Source text is parsed as data in
an isolated worker; do not execute this source file with Python.

```python
import triton
import triton.language as tl

@triton.jit
def mlp(x, w1, b1, w2, b2, y):
    projected = tl.dot(x, w1)
    biased = projected + b1
    hidden = tl.where(biased > 0.0, biased, 0.0)
    final_projection = tl.dot(hidden, w2)
    scores = final_projection + b2
    tl.store(y, scores)
```

Save that text as `mlp.py`, and write `signature.json`:

```json
{"schema_version":"tuc.bounded_cpu_source.v0","source_name":"small_mlp",
"kernel_name":"mlp","tensor_shapes":{"x":[2,2],"w1":[2,2],"b1":[2],
"w2":[2,1],"b2":[1],"y":[2,1]}}
```

Use these separate `inputs.json` values:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{
"x":[1,-2,3,4],"w1":[2,-1,1,2],"b1":[1,1],"w2":[1,2],"b2":[0.5]}}
```

```sh
set -e
mkdir -m 700 parse-work cpu-work
tuc-source-to-json mlp.py --signature signature.json --workspace parse-work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs inputs.json --workspace cpu-work
```

Expected named output: `{"y":[1.5,23.5]}`. The same graph JSON can be reused
with different numeric inputs having the same signature. The shell creates the
graph file before conversion; check command success before consuming it.

Addition accepts two named FP32 tensors of identical rank-one/two shapes, or
`[M,N] + [N]` with the bias on the right. The output uses the left shape. Other
broadcasts, scalar addition, indexing, nested expressions and dtype promotion
are unsupported. Keep each expression in its own assignment. `x+x` is allowed;
the compiler treats the repeated operand as one external input.

Existing dimensions 1-64, eight-operation and 24-tensor bounds still apply.
Native arithmetic rejects overflow and subnormal results, including when the
inputs themselves are normal. This extension executes on CPU only.

See [RFC 0327](../rfcs/0327-bounded-cpu-add-bias.md) and the
[independent installed examples](../integration/bounded_cpu_add_bias/README.md).
Native observation is pending until the dedicated CI run succeeds.
