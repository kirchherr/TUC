# Portable model applications from the command line

The installed `tuc-model-app` command connects an existing bounded FP32 model
to explicit backend capabilities, a portable bundle, concrete requests and the
checked CPU runtime. File commands require Linux x86-64. `--help` works on every
platform. The complete example lives in `integration/bounded_model_cli`.

With a reviewed wheel installed, run from the repository:

```sh
work=$(mktemp -d)
mkdir -m 700 "$work/workspace"
example=integration/bounded_model_cli
tuc-model-app plan "$example/model.json" --backends "$example/backends.json" > "$work/bundle.json"
tuc-model-app inspect "$example/model.json" --backends "$example/backends.json" --bundle "$work/bundle.json"
tuc-model-app request "$example/model.json" --backends "$example/backends.json" --bundle "$work/bundle.json" \
  --inputs "$example/inputs.json" > "$work/request.json"
tuc-model-app run "$example/model.json" --backends "$example/backends.json" --bundle "$work/bundle.json" \
  --inputs "$example/inputs.json" --request "$work/request.json" --workspace "$work/workspace"
tuc-model-app run-batch "$example/model.json" --backends "$example/backends.json" --bundle "$work/bundle.json" \
  --batch "$example/batch.json" --workspace "$work/workspace"
```

`plan` emits the existing canonical portable bundle, including inert source text
and fixed parameter bits. `inspect` fully validates that bundle against the
original model and capability declarations, then reports identities, public I/O,
parameter metadata and the compiler decision report. It omits parameter values
and artifact text. `request` emits the existing canonical request, binding the
exact variable input and fixed parameter bits. These three commands never build
or execute native code.

`run` explicitly authorizes the existing isolated local C11 runtime, validates
the supplied request and returns one result. `run-batch` accepts the existing
`tuc.bounded_cpu_batch.v0` format with request IDs, variable inputs and optional
shared variable inputs. Fixed parameter overrides reject. The complete expanded
batch passes input, output and request budgets before the first build. One
session reuses that build, starts a fresh isolated process per request and closes
before any results publish. Later native errors discard the complete result.

Both execution commands require an absolute workspace and all-C11 declarations.
CUDA and mixed declarations can be planned and inspected; they cannot execute
through this command. No backend replacement, implicit fallback, endpoint, image
or command override is accepted. The existing Docker controls remain in force.

Successful execution emits `tuc.bounded_model_application_cli.v0` with model,
bundle, compilation and capability identities, ordered request IDs, local session
sequences and the existing protocol receipts containing public output bits.
The outer local execution flag is true only after the runtime returns and closes;
embedded receipts retain their conservative false provenance flag. Downloaded
JSON alone cannot establish who ran the command.

Input/argument errors return exit code 2; runtime, cleanup, interruption and
output errors return 1. Errors emit one closed diagnostic on stderr and no result
on stdout. Success returns 0 and one complete JSON value. Input files are bounded
regular files opened without following symlink components; the CLI itself writes
no output files. Shell redirections in the example are caller-owned operations.

## Backend declarations and Python API

The [backend declaration schema](../schemas/bounded_backend_bindings.v0.schema.json)
contains one or two explicit records for the existing `c11` and `cuda-sm86`
source targets. Each record specifies its name, operations, preferred operations,
noise/calibration capabilities, error budget, memory domain and row-major layouts.
The accepted target/domain pairs are C11/host RAM and CUDA/unknown. These are
capability descriptions, never credentials or executable backend registrations.

```python
from tuc.compiler import backend_bindings_from_json, backend_bindings_to_json

bindings = backend_bindings_from_json(backend_json_bytes)
canonical_json = backend_bindings_to_json(bindings)
```

The API is data-only on every platform. It enforces 64 KiB, depth five, 4,096
lexical tokens, closed fields and the existing bounded compiler's invariants.
It preserves the original capability and compilation digests. See
[RFC0342](../rfcs/0342-bounded-model-application-cli.md) and the
[session API](BOUNDED_MODEL_APPLICATION_SESSION.md).

The source-bound installed experiment passed on merged main3324f72. Its
[actual retained CLI packet and observation](evidence/BOUNDED_MODEL_APPLICATION_3324F72.md)
include the original numerical audit and artifact/source bindings. Independent
organizational reproduction remains open under the
[completion plan](PROJECT_COMPLETION_PLAN.md).
