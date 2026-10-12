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
contracts; the retained installed Linux observation and a separate numerical audit
now cover the fixed three-context corpus. See [RFC 0340](../rfcs/0340-bounded-model-application-runtime.md).


The installed Linux evidence workflow copies the native consumer outside the
checkout and uses an installed wheel. It exercises three fixed contexts:
original inputs, changed variable inputs and changed fixed parameters. Its
public terminal outputs are row sums and ReLU scores (18 FP32 scalars total).
Malformed requests, wrong extents, fixed overrides and numerical overflow must
reject and leave the workspace clean.

`audit_native_receipt.py` uses only the Python standard library and no TUC or
consumer import. It independently recomputes FP32 multiplication, ordered
addition, ReLU and row sums; model/parameter identity, input bits, request and
response hashes and result payload integrity are checked. Its opaque compiled
bundle/capability identifiers are consistency checks, not independently
recompiled artifacts or sender authentication. The workflow retains the
original execution record with source, wheel, consumer and audit digests.

```sh
python -I native_consumer.py --run
python -I -S audit_native_receipt.py record.json
```

Only a successful native job establishes this fixed execution observation.
The standard-library audit strengthens numerical reviewability; it remains a
same-project audit rather than reproduction by a separate organization.


The [original installed Linux job](https://github.com/kirchherr/TUC/actions/runs/38277950014/job/114907922282)
passed at `59ad813`: three successful calls, 18 bit-exact numerical comparisons,
four rejection controls and clean workspaces. The immutable observation is
retained in `integration/bounded_model_application/observed-ci-59ad813.json`.
Its source, wheel, consumer, auditor and inner record digests were checked and
the independent auditor was replayed locally without TUC or native execution.
