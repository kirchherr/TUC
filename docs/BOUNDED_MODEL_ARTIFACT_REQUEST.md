# Bind concrete inputs to bounded model artifacts

RFC 0338 adds a portable invocation alongside the RFC 0337 model bundle:

```python
from tuc.compiler import (
    create_bounded_model_artifact_request,
    inspect_bounded_model_artifact_request,
    validate_bounded_model_artifact_request,
)

request_bytes = create_bounded_model_artifact_request(
    model_bytes, backend_bindings, bundle_bytes, input_bytes
)
inspected = inspect_bounded_model_artifact_request(bundle_bytes, request_bytes)
validated = validate_bounded_model_artifact_request(
    model_bytes, backend_bindings, bundle_bytes, input_bytes, request_bytes
)
```

`input_bytes` uses the existing `tuc.bounded_cpu_inputs.v0` schema and contains
exactly the model's variable inputs. Fixed parameters come from the validated
bundle and cannot be supplied by the caller. The request contains both kinds
of input in ascending tensor-index order, with exact shapes and little-endian
FP32 bits. Only finite normal values and signed zero are admitted.

The request binds the exact bundle, model, model-compilation and capability
identities. Changing only variable data yields a different request digest
while retaining the bundle. Changed parameters or capabilities require a new
bundle and request. Each request is capped at 2 MiB and 65,536 total elements.

Inspection checks consistency and integrity against the supplied bundle.
Validation also recomputes from the original model, capabilities and inputs.
Neither authenticates the sender: the digests are content identities, not
signatures. Neither compiles or executes source, accesses devices, discovers
plugins, launches subprocesses, persists files or contacts a network.

The installed-style consumer in
`integration/bounded_model_artifact_request/consumer.py` covers CPU, CUDA and
mixed capability plans. Its committed report includes identities and counts,
with no generated source or input values. See
[RFC 0338](../rfcs/0338-bounded-model-artifact-request.md) for acceptance and
security boundaries.
