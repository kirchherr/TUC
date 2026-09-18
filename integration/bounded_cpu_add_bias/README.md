# Installed CPU Add and Bias consumer

This independent standard-library client owns source text, tensor signatures,
input corpora, expected graph declarations and ordered FP32 references. It
imports no TUC modules. It invokes installed `tuc-source-to-json` and
`tuc-cpu-app` consoles from the same Python environment, outside the checkout.

```sh
# Inert reports and source/signature/input fixtures.
python3 -I consumer.py
python3 -I consumer.py --emit

# Explicit isolated source conversion and CPU execution, with local Docker.
python3 -I consumer.py --run
```

The corpus has eight programs: affine projection with row bias, a two-layer MLP,
residual ReLU plus same-shape addition, and `x + x`, each in two shape profiles.
The latter two families cover both rank-one and rank-two tensors. Two changing
datasets per program require eight source conversions, sixteen successful CPU
calls and 86 independent scalar comparisons. The MLP is five operations:
Matmul, Add, ReLU, Matmul, Add.

Addition accepts equal rank-one/rank-two shapes or `[M,N] + [N]` with the bias
on the right. Duplicate read-only operands are valid; every output is fresh.
There is no scalar, column, left-vector or general broadcasting. Source syntax
is limited to `a + b` with two simple tensor names. Existing static shape,
operation, work, storage and checked FP32 bounds continue to apply.

Eight negative controls cover scalar, nested and subtraction expressions,
incompatible same-shape addition, column broadcast, a vector on the left,
incorrect bias length and a rank-three signature. Two additional native
controls use only normal-or-zero FP32 inputs and require exact numeric rejection
for addition overflow and a subnormal addition result. Error cases require
empty stdout and the exact closed diagnostic; they do not relax numerical rules.

The client independently checks complete converted graphs, public bindings,
source/signature/graph/input hashes and request digests. Program identities must
match inspect and both runs; the compiler's nine-file hash algorithm is not
reimplemented here. Original fixture bytes must remain unchanged and every
workspace must be empty after cleanup. `record.json` is written exclusively
after all checks pass. Default reports and synthetic tests are not native
observations; the installed workflow's actual execution remains required.

## Small MLP example

The [source](mlp.py.txt), [signature](mlp-signature.json) and
[inputs](mlp-inputs.json) form a small biased network with expected scores
`{"y":[1.5,23.5]}`:

```sh
set -e
mkdir -m 700 work
tuc-source-to-json mlp.py.txt --signature mlp-signature.json --workspace work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs mlp-inputs.json --workspace work
```

Source text is parsed as data in the isolated worker, never imported or JIT
executed. The result is limited to the bounded CPU application path; it does
not establish CUDA Add support, arbitrary Triton/PyTorch compatibility,
production sandboxing or performance claims. Earlier consumers and observations
retain their original scope.
