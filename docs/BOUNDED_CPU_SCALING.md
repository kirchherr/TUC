# Scaled attention and feature calibration on CPU

The bounded CPU path accepts compact right-hand scaling tensors. Multiply a
vector or matrix by a `[1]` tensor, or multiply each column of `[M,N]` by its
corresponding factor in `[N]`. The factor is an ordinary input, so changing it
does not require a different graph.

This supports scaled dot-product attention and fixed feature calibration before
a classifier, through the existing source conversion, single-run and batch CLI.

## A small scaled attention calculation

Save `attention.py`:

```python
import triton
import triton.language as tl

@triton.jit
def attention(q, k, v, scale, y):
    scores = tl.dot(q, tl.trans(k))
    scaled = scores * scale
    probabilities = tl.softmax(scaled, axis=1)
    result = tl.dot(probabilities, v)
    tl.store(y, result)
```

Save `signature.json`:

```json
{"schema_version":"tuc.bounded_cpu_source.v0","source_name":"scaled_attention_example",
 "kernel_name":"attention","tensor_shapes":{"q":[1,4],"k":[2,4],"v":[2,2],"scale":[1],"y":[1,2]}}
```

Save `inputs.json`:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{
 "q":[2,0,0,0],"k":[1,0,0,0,0,1,0,0],"v":[1,2,3,4],"scale":[0.5]}}
```

On Linux x86-64 with the installed wheel, local Docker and the existing
[private-workspace requirements](BOUNDED_CPU_SOURCE.md):

```sh
set -e
mkdir -m 700 parse-work cpu-work
tuc-source-to-json attention.py --signature signature.json --workspace parse-work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs inputs.json --workspace cpu-work
```

For a key dimension of four, `scale=[0.5]` supplies `1/sqrt(4)`. The scaled
scores are `[1,0]`, the probabilities are approximately `[0.7310586,0.2689414]`,
and the expected output is approximately `[1.5378828,2.537883]`.
This is unmasked attention for one head; it has no dropout, causal mask or model loader.

## Calibrate features before classification

For `x[M,K]`, supply `gain[K]` and `offset[K]` as named inputs:

```python
scaled = x * gain
calibrated = scaled + offset
projected = tl.dot(calibrated, tl.trans(weight))
logits = projected + bias
probabilities = tl.softmax(logits, axis=1)
tl.store(y, probabilities)
```

This applies caller-provided affine calibration; it does not estimate means,
variances or training parameters. Use [run-batch](BOUNDED_CPU_BATCH.md) to share
`gain`, `offset`, `weight` and `bias` across several input sets.

## Supported shapes and arithmetic

| Left tensor | Right tensor | Result |
| --- | --- | --- |
| `[N]` or `[M,N]` | identical shape | Existing elementwise product |
| `[N]` or `[M,N]` | `[1]` | One factor for every element |
| `[M,N]` | `[N]` | One factor for each column |

The output always has the left shape. Identical shapes retain their original
interpretation. Other broadcasting, reversed operands that need broadcasting,
rank-zero values and scalar literals reject. Both source operands must be
declared tensor names. Graph JSON continues to use `elementwise_kind="mul"`.

Dimensions remain 1-64 and graphs remain bounded to eight operations and the
existing work/storage limits. The runtime reads the compact right tensor; no
expanded scale tensor is required. Each output uses one checked FP32 product.
NaN, infinity, subnormal values and nonzero products rounded to zero reject;
exact signed-zero products are allowed. Softmax retains its
[separate numerical contract](BOUNDED_CPU_SOFTMAX.md).

See [RFC 0332](../rfcs/0332-bounded-cpu-scaling.md) and the
[installed examples](../integration/bounded_cpu_scaling/README.md).
[Installed CI](https://github.com/kirchherr/TUC/actions/runs/35826990657) passed
at `d09d325`: six source conversions, twelve single runs, one three-request batch,
82 output comparisons and twelve probability-row checks. Static and ASan/UBSan
conformance passed, including 118 rejected calls per build. The unchanged
[original receipt](evidence/bounded-cpu-scaling-35826990657.json) and
[verification details](../rfcs/0332-bounded-cpu-scaling.md#observed-execution)
record the corpus. Final CI and owner review for
[PR #129](https://github.com/kirchherr/TUC/pull/129) remain required.
The guide values above are expected results.
