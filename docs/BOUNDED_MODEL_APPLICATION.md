# Admit model requests to the checked CPU application protocol

RFC 0339 connects the portable model bundle/request with the existing C11
application byte protocol. Preparation remains inert:

```python
from tuc.compiler import (
    prepare_bounded_model_application,
    decode_bounded_model_application_response,
    validate_bounded_model_application_result,
)

prepared = prepare_bounded_model_application(
    model_bytes, backend_bindings, bundle_bytes, input_bytes, request_bytes
)
# prepared.application.files() contains allowlisted inert build text.
# prepared.request_frame is the exact existing C11 binary request.
# No build, file write or execution has happened.

result = decode_bounded_model_application_response(
    model_bytes, backend_bindings, bundle_bytes, input_bytes, request_bytes,
    response_bytes, exit_code,
)
validated = validate_bounded_model_application_result(
    model_bytes, backend_bindings, bundle_bytes, input_bytes, request_bytes,
    response_bytes, exit_code, result.receipt_data,
)
```

All original inputs are required again during response decoding and receipt
validation. The bridge never trusts a caller-created prepared object or digest.
It validates fixed parameters and variable input bits and regenerates the C11
program. Every declared backend must target C11; CUDA and mixed contexts reject.

The existing binary request identity binds the program and input payload.
The receipt additionally binds that identity to the portable bundle and model
request, response hash and public output positions, shapes and exact FP32 bits.
Changing parameters or variable inputs changes both request identities; a
response for a different input cannot be replayed. All checked native error
statuses fail without emitting a successful result.

The returned data grants no execution authority. To build/run on Linux x86-64,
a caller must separately invoke the existing isolated C11 runtime with
`prepared.module`, explicit backend bindings and its own admissible workspace.
That runtime revalidates and regenerates its application; it does not accept
source or command overrides from this bridge.

Caller-supplied response bytes establish protocol consistency only. Receipts
always set `native_execution_observed` to false and cannot authenticate the
sender or prove numerical correctness. The installed-style consumer in
`integration/bounded_model_application/consumer.py` deliberately uses labelled
synthetic responses. Its report proves context binding and target rejection,
not native execution. See [RFC 0339](../rfcs/0339-bounded-model-application.md).
