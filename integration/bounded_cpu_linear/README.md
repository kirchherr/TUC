# Installed bounded CPU Linear consumer

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

Six programs cover affine Linear, a two-layer Linear/Add/ReLU MLP, and a chain
mixing normal Matmul with Linear. Each has two non-square profiles, including
a single-row input. Two changing datasets per program require six source
conversions, twelve successful CPU calls and 60 bitwise FP32 scalar comparisons.
The references perform each multiplication and sequential addition separately;
they do not interpret emitted graph operations or generated C source.

The source form `tl.dot(x, tl.trans(weight))` accepts physical row-major
`x[M,K]` and `weight[N,K]` and returns `[M,N]`. It lowers to Matmul with the
exact attribute `rhs_transposed: true`. Weights already have `[N,K]` storage;
no transpose is materialized. Bias remains a separate Add. The normal Matmul
source form retains its original meaning. This client does not import PyTorch
or claim arbitrary model, transpose, Triton, GPU or performance support.

Ten negative source controls cover an arbitrary nested call, double transpose,
left-hand transpose, positional and keyword axes, method and attribute forms,
a nested addition, standalone transpose and incompatible inner dimensions.
Two numeric controls use normal-or-zero operands that cause a product overflow
or subnormal product. Both require exact numeric rejection with empty stdout.
These extra rejected calls are separate from the twelve successful runs.

The client checks complete graph contents and public bindings, retains source,
signature, graph and input hashes, and independently reconstructs request
digests. Program identities must agree between inspection and both runs;
the compiler's nine-file program hash algorithm is not duplicated here.
Original fixtures must remain byte-for-byte unchanged and workspaces empty
after every command. It creates `record.json` exclusively after all checks pass.
Its schema is `tuc.bounded_cpu_linear_integration.v0`; reports from the default
mode and synthetic tests are not native observations. Actual installed/native
CI observation is pending.

## Small Linear example

The [source](linear.py.txt), [signature](linear-signature.json) and
[inputs](linear-inputs.json) compute `x @ weight.T + bias`, with expected
named output `{"scores":[-0.5,1.0,4.5,7.0]}`:

```sh
set -e
mkdir -m 700 work
tuc-source-to-json linear.py.txt --signature linear-signature.json --workspace work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs linear-inputs.json --workspace work
```

The converter parses source as data inside its isolated worker. Do not execute
the fixture with Python. Existing bounded CPU shape, operation, storage, work
and numerical constraints remain in force. Earlier consumers and observations
retain their original scope.
