# Run elementwise products and a gated MLP on CPU

The bounded CPU path supports `left * right` for FP32 tensors with identical
rank-one or rank-two shapes. This lets one computed tensor scale another
element by element. `x*x` is also supported with one external input.

A ReLU-gated MLP combines two Linear branches before its final projection:

```python
import triton
import triton.language as tl

@triton.jit
def gated_mlp(x, wv, bv, wg, bg, wo, y):
    vp = tl.dot(x, tl.trans(wv))
    value = vp + bv
    gp = tl.dot(x, tl.trans(wg))
    gate_bias = gp + bg
    gate = tl.where(gate_bias > 0.0, gate_bias, 0.0)
    gated = value * gate
    scores = tl.dot(gated, tl.trans(wo))
    tl.store(y, scores)
```

Save this as `gated_mlp.py`. It contains seven operations. The output projection
can have a separate bias as an eighth operation. Every expression is a separate
assignment; the source converter parses this file as data in its isolated worker.

Write `signature.json`:

```json
{"schema_version":"tuc.bounded_cpu_source.v0","source_name":"gated_example",
"kernel_name":"gated_mlp","tensor_shapes":{"x":[1,2],"wv":[2,2],"bv":[2],
"wg":[2,2],"bg":[2],"wo":[1,2],"y":[1,1]}}
```

Write `inputs.json` with flat row-major arrays:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{
"x":[2,3],"wv":[1,0,0,1],"bv":[1,-1],
"wg":[1,1,-1,1],"bg":[-1,0],"wo":[2,-1]}}
```

Use the installed wheel on Linux x86-64 with the existing local Docker setup
described in the [source-to-CPU guide](BOUNDED_CPU_SOURCE.md):

```sh
set -e
mkdir -m 700 parse-work cpu-work
tuc-source-to-json gated_mlp.py --signature signature.json --workspace parse-work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs inputs.json --workspace cpu-work
```

The `outputs` field is `{"y":[22.0]}`: the value branch is `[3,2]`, the
activated gate is `[4,1]`, their product is `[12,2]`, and the projection is 22.
This sample demonstrates a ReLU gate; GLU and SwiGLU use different activations.

In graph JSON, use `"family":"elementwise"` and
`"attributes":{"elementwise_kind":"mul"}` with two inputs and one fresh
output. Both inputs and the output must have exactly the same shape. Scalars,
row broadcasting, nested multiplication, promotion and general tensor views
are unsupported. Existing dimension 1-64, eight-operation and storage/work
limits apply. Mul-containing graphs currently require one C11 CPU backend.

Each product is checked after rounding to FP32. Overflow, subnormal products
and nonzero products rounded to zero reject before outputs are published;
signed zero remains observable. Changing numeric inputs retains the program
identity and changes the request identity.

See [RFC 0329](../rfcs/0329-bounded-cpu-gating.md) and the
[independent installed examples](../integration/bounded_cpu_gating/README.md).
Installed/native validation is pending.
