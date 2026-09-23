# CPU probabilities and small attention graphs

The bounded CPU path supports row Softmax on rank-two FP32 tensors. Combine it
with Linear and Bias for class probabilities, or put it between two Matmuls for
a small unscaled attention calculation. Existing single-run and batch commands
both accept these graphs.

## A three-class example

Save `classifier.py`:

```python
import triton
import triton.language as tl

@triton.jit
def classifier(x, w, b, y):
    projected = tl.dot(x, tl.trans(w))
    logits = projected + b
    probabilities = tl.softmax(logits, axis=1)
    tl.store(y, probabilities)
```

Save `signature.json`:

```json
{"schema_version":"tuc.bounded_cpu_source.v0","source_name":"classifier_example",
 "kernel_name":"classifier","tensor_shapes":{"x":[1,2],"w":[3,2],"b":[3],"y":[1,3]}}
```

Save `inputs.json`:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0",
 "inputs":{"x":[1,2],"w":[1,0,0,1,1,1],"b":[0,0,0]}}
```

Run the installed wheel on Linux x86-64 with the existing local Docker setup
and [private-workspace requirements](BOUNDED_CPU_SOURCE.md):

```sh
set -e
mkdir -m 700 parse-work cpu-work
tuc-source-to-json classifier.py --signature signature.json --workspace parse-work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs inputs.json --workspace cpu-work
```

The logits are `[1,2,3]`; expected `outputs.y` is approximately
`[0.09003057, 0.24472848, 0.66524094]`. The row sums to approximately one.
Use [run-batch](BOUNDED_CPU_BATCH.md) with shared `w` and `b` to classify several
input sets after one build.

## Scope and numerical behavior

Graph JSON uses `"family":"softmax"` and `"attributes":{"axis":1}`. Input and
output must have the same rank-two shape, dimensions 1-64, and distinct tensor
identities. Other axes, arbitrary views, dynamic shapes and dtypes reject.
The existing eight-operation and graph/resource limits apply.

Each row subtracts its maximum, applies `expf`, sums in order and divides by
the sum. Inputs and rounded arithmetic must remain normal FP32 values or
permitted signed zero. Exponentials and probabilities must remain positive
normal values. Overflow and very small probabilities reject with
`numeric_rejection`; they are not silently clipped to zero.

Softmax examples use explicit numerical tolerances, since math libraries need
not return identical exponential bits. The fixed conformance corpus uses
absolute tolerance `2e-6` plus relative tolerance `2e-5`, with row sums within
`8e-6` of one. This does not promise that bound for every supported composition.
See [RFC 0331](../rfcs/0331-bounded-cpu-softmax.md) for the exact evaluation order.

The [installed examples](../integration/bounded_cpu_softmax/README.md) also cover
`Q @ K.T -> Softmax -> probabilities @ V`. This calculation has no mask,
scale factor, dropout or multi-head arrangement. It is a small building block,
not a complete attention layer or general model loader.

[Installed CI](https://github.com/kirchherr/TUC/actions/runs/35694760750) passed
at `a69b5fb`: six source conversions, twelve single runs, one three-request
batch, 106 numerical comparisons and 22 probability-row checks. Static and
ASan/UBSan conformance also passed, including 108 rejected calls per build.
The [original receipt](evidence/bounded-cpu-softmax-35694760750.json) and
[verification details](../rfcs/0331-bounded-cpu-softmax.md#observed-execution)
record the tested corpus. The guide values above are expected results; final
CI and owner review for [PR #128](https://github.com/kirchherr/TUC/pull/128)
remain required.
