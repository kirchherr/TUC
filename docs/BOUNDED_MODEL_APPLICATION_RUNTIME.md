# Run a validated portable model request on the isolated CPU path

RFC 0340 adds an explicit runtime call on Linux x86-64:

```python
from pathlib import Path
from tuc.runtime.bounded_model_application import run_bounded_model_application

result = run_bounded_model_application(
    model_bytes, backend_bindings, bundle_bytes, input_bytes, request_bytes,
    workspace=Path("/caller-owned/private-workspace"),
)
```

The workspace must meet the existing C11 runtime ownership and permission
checks, and its fixed local Docker daemon must be available. This call fully
validates the original model context before building, runs the exact admitted
binary request through the existing isolated CPU image, checks the response
and releases build resources. Unsupported CUDA/mixed contexts reject before
build. No source, command, image or endpoint override is accepted.

The existing built C11 handle also exposes `run_frame(request_bytes)`, which
returns only a validated successful response. This lower-level method knows
the program/input protocol; use the model adapter when fixed parameters and
portable model identities must also be enforced. Named-input `run` retains
its original interface and shares all execution controls with `run_frame`.

Returned RFC 0339 receipts preserve exact output bits and request identities.
Their `native_execution_observed` flag remains false because protocol bytes
are not provenance. Mocked regression tests check control flow and isolation
contracts; actual native evidence and an independent numerical comparison are
still required. See [RFC 0340](../rfcs/0340-bounded-model-application-runtime.md).
