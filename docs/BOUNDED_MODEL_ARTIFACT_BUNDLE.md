# Transfer bounded model artifacts

RFC 0337 serializes the existing capability-planned model result as one
canonical JSON envelope:

```python
from tuc.compiler.bounded_model_artifact_bundle import (
    create_bounded_model_artifact_bundle,
    inspect_bounded_model_artifact_bundle,
    validate_bounded_model_artifact_bundle,
)

bundle_bytes = create_bounded_model_artifact_bundle(model_bytes, backend_bindings)
inspected = inspect_bounded_model_artifact_bundle(bundle_bytes)
validated = validate_bounded_model_artifact_bundle(
    model_bytes, backend_bindings, bundle_bytes
)
files = validated.files()
```

The envelope uses contract `tuc.bounded_model_artifact_bundle.v0`. It contains
the model and model-compilation digests, Source Intent and backend-binding
digests, fixed FP32 parameter bits, variable-input and public-output bindings,
the compiler decision report, and the exact five inert artifact files with
individual SHA-256 digests. The envelope itself has a SHA-256 digest over its
canonical payload.

`inspect_bounded_model_artifact_bundle` accepts untrusted bytes and checks the
closed structure, types, resource limits, canonical encoding, file names and
all content digests. `validate_bounded_model_artifact_bundle` additionally
recompiles from the original model and explicit backend capabilities and
requires byte-for-byte equality. Use validation when provenance and semantic
binding to those inputs matter.

The bundle is capped at 4 MiB and reuses the compiler's tensor, name, shape,
metadata and artifact budgets. Duplicate JSON keys, non-finite values,
unexpected fields, non-canonical encodings and digest drift are rejected with
one closed diagnostic.

All returned source remains inert text. The API performs no filesystem or
network access, native compilation, runtime execution, plugin discovery,
device access, subprocess launch or generated-code execution. The caller alone
decides whether and where validated files are persisted and whether a separate
trusted build or runtime boundary later consumes them.

See [RFC 0337](../rfcs/0337-bounded-model-artifact-bundle.md) for the acceptance
contract and non-claims.
