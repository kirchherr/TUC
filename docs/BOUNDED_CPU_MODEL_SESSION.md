# Reuse a CPU model from Python

Use a session when inputs arrive separately and should share one build:

```python
from pathlib import Path
from tuc.bounded_cpu_model_session import open_cpu_model

model_data = Path("model.json").read_bytes()
first_inputs = b'{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{"x":[2,3]}}'
next_inputs = b'{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{"x":[-1,2]}}'

with open_cpu_model(model_data, workspace=Path("work")) as session:
    first = session.run(first_inputs)
    second = session.run(next_inputs)
    print(dict(second.outputs))
    print(second.model_digest, second.request_digest)
```

Create `model.json` with [pack-model](BOUNDED_CPU_MODEL.md), using a graph with an
`x` input matching this example. The caller is responsible for reading model and
input bytes from its trusted application files. Execution requires Linux x86-64,
the existing local Docker setup and an existing private `work` directory. Opening
and inspecting session identities does not build or execute. The first valid
request builds; subsequent calls reuse that build in independently isolated runs.

Each session allows 16 successful requests and a cumulative 65,536 elements for
inputs and separately outputs. Fixed weights count on every request. Malformed
input and parameter overrides reject without executing or consuming this budget.
Inputs must contain exactly the remaining variable bindings. Results contain
immutable `(name, tuple_of_values)` pairs, model/program/request identities and a
one-based sequence. Identical expanded data retain the CLI request identity.

Use the context manager or call `close()` explicitly. Execution failures close
the session; later calls report `closed`. Cleanup failures report `cleanup_failed`
and may be retried with `close()`. Concurrent operations report `session_busy`.
Do not abandon a live session and rely on garbage collection for cleanup.

Each successful call returns immediately. Earlier results remain available if a
later request fails or final cleanup fails. For complete-batch validation and
all-or-nothing publication after cleanup, use the existing `run-model-batch` CLI.
Build reuse does not imply resident weights or a measured speedup.

See [RFC 0334](../rfcs/0334-bounded-cpu-model-session.md) and the
[installed consumer](../integration/bounded_cpu_model_session/README.md).
[Installed CI](https://github.com/kirchherr/TUC/actions/runs/36570752112) passed at
`f4dbcc9`: 239 tests, four sessions, 21 successful calls, 42 output comparisons,
17 stable-context checks and all rejection/cleanup controls. The unchanged
[original receipt](evidence/bounded-model-session-36570752112.json) and
[audit details](../rfcs/0334-bounded-cpu-model-session.md#observed-execution) retain
the tested scope. The committed
[standard-library audit](BOUNDED_MODEL_SESSION_AUDIT.md) independently reconstructs
the fixed receipt identities and numerical results without another native run.
Final-head CI passed 55 checks with one expected skip and 7,383 tests passed;
owner review remains required.
