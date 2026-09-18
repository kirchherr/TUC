# Build and run a bounded CPU application

The RFC 0324 API accepts your own supported Source Intent graph and named input
tensors. Preparation returns source files. An explicit build creates a container
image, and an explicit `run()` sends one input frame to a fresh container.
Importing either module does not start a process.

The [native CI run](https://github.com/kirchherr/TUC/actions/runs/35339997831)
passed on revision `c9ebb2675f5114b7332284ce5fa380e8f259bb43`: 333 Linux tests,
12 application calls, 72 numerical checks, one checked overflow rejection and
2,460 sanitizer parser cases. This establishes the tested corpus; the numerical
result in the separate custom example below is the expected result.

## Requirements

Use an installed TUC wheel with its dependencies. The native API currently
requires Linux reporting `x86_64`, a working local Docker daemon at
`unix:///var/run/docker.sock`, and permission to use that daemon. It does not
install Docker, choose a remote endpoint, use a caller-supplied Docker context,
or select CUDA.

The Docker executable must be root-owned and non-writable by group/other, as
must its resolved parent directories. It is located through the fixed path
`/usr/local/bin:/usr/bin:/bin`. The workspace must already exist, belong to the
calling user, have no symlink components, and disallow group/other writes.
`TemporaryDirectory` normally supplies a suitable private workspace.

The build uses a digest-pinned GCC image and Dockerfile frontend. Docker may
need these images available from its local cache or registry. Build commands
have networking disabled; that flag is not a promise that the daemon never
resolves a base image. The local Docker daemon and host administrator remain
trusted components.

## A complete application

This two-operation graph multiplies a two-row matrix by a column and applies
ReLU. Names in `data` are the external tensor names; returned keys are explicit
public return aliases. Tensor tuples contain flat row-major data.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.runtime.bounded_c11_application import build_bounded_c11_application

module = SourceIntentModule(
    "row_scores",
    tensors=(
        SourceIntentTensor("x", (2, 2)),
        SourceIntentTensor("weights", (2, 1)),
        SourceIntentTensor("projection", (2, 1)),
        SourceIntentTensor("positive", (2, 1)),
    ),
    operations=(
        SourceIntentOperation("project", "matmul", ("x", "weights"), ("projection",)),
        SourceIntentOperation(
            "activate", "elementwise", ("projection",), ("positive",),
            attributes={"elementwise_kind": "relu"},
        ),
    ),
    returns=(SourceIntentReturn("scores", "positive"),),
)
bindings = (
    BoundedBackendBinding(
        BackendCapability(
            "my_cpu",
            frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
            memory_domain=MemoryDomainKind.HOST_RAM,
        ),
        DAGTarget.C11,
    ),
)
data = {
    "x": (1.0, -2.0, 3.0, 4.0),
    "weights": (2.0, 1.0),
}

# Pure preparation: no compiler or container starts here.
prepared = prepare_bounded_c11_application(module, bindings)
print(prepared.program_digest)
files = prepared.files()

# Explicit native actions: build once, run with caller-supplied values, clean up.
with TemporaryDirectory(prefix="my-tuc-app-") as directory:
    with build_bounded_c11_application(
        module, bindings, workspace=Path(directory)
    ) as application:
        result = application.run(data)
        assert result == {"scores": (0.0, 10.0)}
```

Each `run()` starts a separate restricted container using the built immutable
image ID. A handle can accept multiple input dictionaries for the same graph.
Changing input values does not rebuild the image. Do not mutate the source
module or bindings while using the handle: it stores validated snapshots and
also checks the original objects for graph drift before each run.

Use the context manager, or call `close()` explicitly. The runtime removes its
owned image tag and private temporary context. It does not promise to remove
shared base images or Docker build-cache layers. Handles cannot be constructed
directly or subclassed, and a closed handle rejects execution.

## Supported graphs and values

The existing bounded Source Intent limits apply: at most eight operations and
24 tensors, static dimensions from 1 through 64, FP32 row-major tensors, at most
one million logical scalar operations and 256 KiB of tensor scratch. Supported
operations are two-dimensional Matmul, explicit ReLU on rank-one or rank-two
tensors, and axis-one Sum from rank two to rank one. Every terminal tensor needs
one explicit required public return. Selected CUDA or mixed plans reject.

Inputs must be an exact `dict` whose keys match all public inputs, with exact
`tuple` values of the required lengths. Elements must be Python `float` values;
integers such as `1`, booleans, subclasses and array objects reject. Convert
application data deliberately before calling this boundary. The encoder rounds
to binary32 and rejects NaN, infinity, subnormal results and nonzero values that
round to zero. Both signed zeros are accepted.

Generated arithmetic checks each rounded product and sequential addition.
Overflow, subnormal intermediates and a nonzero product rounded to zero reject
even if a later operation could conceal them. Exact zero products and exact
cancellation are allowed. The required floating environment is round-to-nearest
with FTZ/DAZ disabled and SSE exceptions masked. This API has no dynamic shapes,
autograd, arbitrary kernels, GPU execution or performance guarantee.

## Artifacts, errors and protocol

`prepared.files()` returns a fresh mapping containing exactly:

```text
entrypoint.h             entrypoint.c            entrypoint.json
application.h            application.c           application.json
Dockerfile               Dockerfile.dockerignore build.sh
```

`validate_bounded_c11_application(module, bindings, prepared)` reconstructs the
entire artifact. The pure helpers `encode_bounded_c11_inputs(...)` and
`decode_bounded_c11_outputs(...)` also perform full revalidation. They are useful
for protocol inspection; they do not launch the program.

The binary request contains an eight-byte version, the program digest, a request
digest, then fixed-count little-endian FP32 inputs. The host computes the request
digest over program identity and input payload. The native process echoes that
digest; it does not authenticate it or recompute it. The host checks the echo,
program identity, exact frame length, exit code, status and output value domain.
Neither a digest nor a synthetically constructed response proves execution or
numerical correctness.

The pure decoder raises `BoundedC11ApplicationExecutionError` only for a fully
validated native error response; its read-only `status` is 1 (argument), 2
(numeric), or 3 (environment). Malformed protocol data raises `ValueError`.
The explicit runtime exposes `BoundedC11ApplicationRuntimeError.reason`, such as
`numeric_rejection`, `environment_rejection`, `input_rejection`,
`protocol_rejection`, `timeout`, or `cleanup_failed`. It does not include raw
process logs or host paths in those diagnostics.

Builds have a 600-second deadline; container requests have a 30-second deadline
and the application process has a five-second alarm. Pipes have fixed output
limits, failed processes are terminated, and cleanup targets only owned names
and verified private paths. Container restrictions include no network, a
read-only root, UID/GID 10001, no capabilities, no new privileges and bounded
memory, CPU and process resources. There are no host bind mounts or arbitrary
command parameters in this API.

For the installed example and recorded native validation, see
[the application consumer](../integration/bounded_cpu_application/README.md) and
[RFC 0324](../rfcs/0324-bounded-cpu-application.md).
