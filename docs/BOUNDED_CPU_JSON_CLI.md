# Run a CPU graph from JSON

`tuc-cpu-app` accepts a supported graph and input tensors as separate JSON files.
You can inspect the graph, then explicitly build and run it without writing a
Python integration script. This is the file interface to the
[bounded CPU application API](BOUNDED_CPU_APPLICATION.md).

[Elementwise products and gated MLPs](BOUNDED_CPU_GATING.md) use
`family: elementwise` with `elementwise_kind: mul` and exactly equal input shapes.

The CPU path also supports [Linear with row-major weights](BOUNDED_CPU_LINEAR.md):
Matmul with `rhs_transposed: true` consumes `X[M,K]` and `W[N,K]` and produces
`Y[M,N]`. Omit the attribute for ordinary Matmul.

The file commands currently require Linux x86-64. `inspect` does not use Docker;
`run` requires an existing local Docker daemon and the same trusted-tool/private
workspace prerequisites as the CPU application API. `--help` and the pure Python
bytes adapters also work on other supported Python platforms. The CLI does not
start a Docker service or choose a remote host.

## Try the included graph

Install the wheel built from this revision into a virtual environment. Copy
[projection.json](../integration/bounded_cpu_json/projection.json) and
[projection-inputs.json](../integration/bounded_cpu_json/projection-inputs.json)
to your application directory. From the environment:

```sh
tuc-cpu-app inspect projection.json
mkdir -m 700 work
tuc-cpu-app run projection.json --inputs projection-inputs.json --workspace work
```

The graph multiplies `x` by `weights`, then applies ReLU. The result's `outputs`
field is expected to be `{"scores":[0.0,10.0]}`. `inspect` reports public inputs,
outputs and a deterministic program digest with `native_execution_observed`
set to false. Successful `run` output contains the program digest, the encoded
request digest, named result arrays and `native_execution_observed: true`.

The module form is equivalent:

```sh
python -I -m tuc.bounded_cpu_application_cli inspect projection.json
```

The command builds for each invocation. Python applications that need several
runs with one build should use the context-managed API in RFC 0324.

## Graph and input contracts

The graph is an existing `source_intent.v0` document, with explicit `name`,
`schema_version`, `tensors`, `operations` and required public `returns`. It
describes computation; the CLI supplies the fixed `json_cpu` capability. JSON
cannot choose a Docker image, executable, backend plugin or compiler command.

The supported graph subset is static row-major FP32 with Matmul, explicit ReLU,
axis-one Sum and bounded Add. Add accepts equal rank-one/two shapes or a
right-hand row bias `[M,N] + [N]`; see the [Add/Bias guide](BOUNDED_CPU_ADD_BIAS.md).
At most eight operations, 24 tensors, eight terminal returns,
rank one or two and dimensions 1–64 are accepted. Existing graph semantics,
one-million-scalar-work and 256 KiB tensor-storage limits also apply. Every
terminal tensor must have one required return. See the
[Source Intent compiler guide](BOUNDED_SOURCE_COMPILER.md).

Inputs have this exact envelope:

```json
{
  "schema_version": "tuc.bounded_cpu_inputs.v0",
  "inputs": {
    "x": [1, -2, 3, 4],
    "weights": [2, 1]
  }
}
```

Names must match all public inputs. Arrays are flat row-major data with exact
element counts. JSON integer and fractional numbers are decoded to binary64,
then rounded to the existing binary32 contract. The lexical `-0` keeps its sign.
Booleans, nulls, strings, nested arrays, exceptional numbers and nonzero values
that underflow to zero reject. Subnormal FP32 values reject as in the Python API.
The checked native arithmetic policy also applies to intermediates.

Graph JSON is limited to 64 KiB, depth 12 and 4,096 lexical tokens. Input JSON is
limited to 2 MiB, depth six and 200,000 lexical tokens, followed by public tensor
extent checks. Numeric tokens have at most 64 characters. Both documents require
strict UTF-8 without a BOM, duplicate object keys or invalid surrogate strings.
Unknown fields and unsupported schema versions reject. Ordinary whitespace and
object-key order do not change the compiled program; return-array order matters.

## Read files, report errors, publish results

The Linux reader opens each path component without following symlinks. It
accepts regular files only, checks size before reading, reads no more than the
limit plus one byte, and checks the opened file's metadata again. Parent
traversal, symlink components, FIFOs and devices reject. Files that change during
the read are rejected when detected; a file's contents always remain untrusted
data. Keep application inputs stable while reading them.

Both documents and the complete encoded request pass validation before any
native build begins. `run` delegates isolation, image identity, bounded process
I/O and cleanup to the existing runtime. It publishes one bounded JSON document
only after successful execution and cleanup. Stdout transport errors can still
interrupt delivery; a digest is identity, not authentication or an independent
proof of numerical correctness.

Exit zero means the requested command succeeded. Exit two reports argument,
platform, file, graph or input rejection; exit one reports runtime or output
failure. Stderr uses a closed reason such as `tuc-cpu-app: numeric_rejection`.
It does not echo input contents, path names, arbitrary arguments or Docker logs.
Processing failures produce no result JSON. There is no silent fallback.

For Python callers, the pure adapters are:

```python
from tuc.compiler.bounded_cpu_json import source_intent_from_json, inputs_from_json

module = source_intent_from_json(graph_bytes)
# bindings/application are prepared through the existing compiler API.
inputs = inputs_from_json(module, bindings, application, input_bytes)
```

Both require exact `bytes` and perform no file I/O or native execution. This
adapter accepts structured graph data; it does not parse Python/Triton source,
inspect functions, evaluate code, discover plugins or admit CUDA execution.

See [RFC 0325](../rfcs/0325-bounded-cpu-json-cli.md) and the
[installed CLI conformance client](../integration/bounded_cpu_json/README.md).

## Observed installed execution

The [Linux integration run](https://github.com/kirchherr/TUC/actions/runs/35343784690)
at source revision `1b2a1ce4d8db86de320af341dd5f44ada916aa79` passed 308 tests
and executed the installed console outside the checkout: six programs, twelve
successful calls and 56 independent binary32 scalar comparisons. It also
confirmed one numeric overflow rejection and six malformed/duplicate/symlink
controls, unchanged input bytes and cleaned workspaces. The
[original receipt](../integration/bounded_cpu_json/observed-ci-1b2a1ce.json)
retains source, wheel, consumer, program and request identities. This observation
covers those bounded cases; owner review and final revision CI remain required.
