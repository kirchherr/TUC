# Convert a bounded source program and run it on CPU

An installed `tuc-source-to-json` converts the supported Triton-like research
notation into a checked graph. The existing `tuc-cpu-app` executes that graph
with your input tensors. The converter parses source as data in a fixed isolated
container; it never imports your source or evaluates `@triton.jit`.

## Requirements

Use an installed TUC wheel on Linux x86-64 and the existing trusted local Docker
setup described in [CPU application requirements](BOUNDED_CPU_APPLICATION.md).
Both commands use existing private workspace directories. Paths must have no
symlink components; source/signature/input documents must be regular files.
The converter builds a fresh parser image from fixed installed TUC files and
the existing pinned Python base, with no package installation. Docker may need
to resolve that base image. No Triton installation is required.

## Write source, shapes and inputs

Save this as `projection.py`. These imports and the decorator are syntax read by
TUC, so do not execute the file with Python:

```python
import triton
import triton.language as tl

@triton.jit
def project(x, weights, scores):
    projection = tl.dot(x, weights)
    positive = tl.where(projection > 0.0, projection, 0.0)
    tl.store(scores, positive)
```

Save the signature as `signature.json`. Shapes cover every function argument,
including output targets:

```json
{
  "schema_version": "tuc.bounded_cpu_source.v0",
  "source_name": "row_scores",
  "kernel_name": "project",
  "tensor_shapes": {"x": [2, 2], "weights": [2, 1], "scores": [2, 1]}
}
```

Save numeric data as `inputs.json` using the existing input format:

```json
{
  "schema_version": "tuc.bounded_cpu_inputs.v0",
  "inputs": {"x": [1, -2, 3, 4], "weights": [2, 1]}
}
```

## Convert, inspect and execute

```sh
mkdir -m 700 parse-work cpu-work
tuc-source-to-json projection.py --signature signature.json --workspace parse-work > graph.json
tuc-cpu-app inspect graph.json
tuc-cpu-app run graph.json --inputs inputs.json --workspace cpu-work
```

Successful conversion writes one `source_intent.v0` graph document. Inspect
shows its ordered inputs/outputs and program identity. Run returns named
output arrays; the expected `outputs` for this example are
`{"scores":[0.0,10.0]}`. Each command must succeed before the next is used.
The shell creates `graph.json` for redirection even if conversion fails; always
check the exit code. The graph is emitted only after parser cleanup succeeds.

Example files and the [independent installed consumer](
../integration/bounded_cpu_source/README.md) are included in the repository.

## Supported subset

One function with the two literal imports and `@triton.jit` is accepted.
Statements are assignments using `tl.dot(a, b)`, ReLU as
`tl.where(x > 0.0, x, 0.0)`, `tl.sum(x, axis=1)`, and terminal
`tl.store(output_name, value)` calls. Source arguments denote complete tensors.
RFC 0327 also accepts `result = left + right` for two named tensors: identical
rank-one/two shapes or a matrix plus its right-hand row bias `[M,N] + [N]`.
See the [Add/Bias application guide](BOUNDED_CPU_ADD_BIAS.md) for a small MLP.
This does not implement pointer arithmetic, `tl.load`, masks, loops, constexpr,
softmax execution or general Triton kernels. Public output names are separate
from input names, and all terminal values must be stored.

The existing CPU contract applies: static row-major FP32, rank one/two,
dimensions 1–64, at most eight operations and 24 tensors, checked work/storage
budgets and checked FP32 arithmetic. Unsupported graphs reject explicitly.
The source limit is 64 KiB/2048 lines; signature JSON is limited to 16 KiB,
24 entries and identifiers of at most 64 ASCII characters. Request encoding
can hit the separate 96 KiB worker transport bound before the source-byte bound.

Only bounded source bytes cross the parser's stdin. The parent validates its
response, request/source identity, observed isolation facts and graph semantics.
The parser container has no network or host mounts and uses a read-only root,
non-root user and resource limits. This remains an explicit research interface;
host/Docker administrators are trusted, and production sandboxing or full Triton
compatibility is not claimed.

Exit zero means conversion/help succeeded. Exit two means arguments, files,
signature, source or the resulting graph were rejected. Exit one means worker,
runtime or output failure. Stderr is a closed diagnostic such as
`tuc-source-to-json: source_rejected`; source text, paths and process logs are
not included. `--help` is portable and does not start a process.

See [RFC 0326](../rfcs/0326-bounded-source-to-cpu.md) for the boundary and
validation design. [Native CI run 35346924415](
https://github.com/kirchherr/TUC/actions/runs/35346924415) passed at source
revision `1da2276`: six conversions, twelve CPU calls, 56 independent FP32
comparisons and ten rejection controls. Its [original observed record](
../integration/bounded_cpu_source/observed-ci-1da2276.json) binds the source
revision, installed wheel and consumer. Final revision CI and owner review
remain required for acceptance.
