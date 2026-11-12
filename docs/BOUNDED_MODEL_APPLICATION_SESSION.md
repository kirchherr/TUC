# Reusable bounded model application sessions

The explicit CPU model protocol can reuse one build across validated requests
for the same model, capabilities and artifact bundle. The single-call API and
the independently replayable original observation remain unchanged.

```python
from tuc.compiler.bounded_model_artifact_request import create_bounded_model_artifact_request
from tuc.runtime.bounded_model_application_session import open_bounded_model_application

with open_bounded_model_application(model, bindings, bundle, workspace=workspace) as session:
    for inputs in (first_inputs, second_inputs):
        request = create_bounded_model_artifact_request(model, bindings, bundle, inputs)
        completed = session.run(inputs, request)
        print(completed.sequence, completed.result.outputs)
```

The model, bindings, bundle and inputs above use the existing portable model
contracts. The workspace is an absolute caller-owned path satisfying the
[CPU runtime requirements](BOUNDED_CPU_APPLICATION.md). Opening, entering
and closing an unused session neither builds nor accesses that path. Only
`run` authorizes the existing Linux x86-64/local-Docker build/run boundary.
Use the context manager or call `close()` explicitly.

## Request and lifecycle rules

Every invocation supplies concrete input bytes and their matching portable
request. The session pins the model, compilation, bundle, capabilities and
program. A changed parameter model requires another session. CUDA/mixed
contexts reject. Unknown or invalid input does not select another target.

Pure input rejection does not consume a request or element budget. It leaves
an otherwise valid session usable. Changed original context, build failure,
native failure or a rejected response closes it. A failed cleanup can be
retried with `close()`; a closed session cannot run again. Concurrent run and
close operations reject with `session_busy` instead of overlapping.

Each session permits at most 16 successful requests and separate cumulative
limits of 65,536 input elements and 65,536 output elements. Expanded fixed
parameters count on each invocation. Every native process receives a complete
request; parameter memory is not retained inside a resident native process.

`BoundedModelApplicationSessionResult.sequence` is a local counter.
`result` is the existing checked `BoundedModelApplicationResult`; its
receipt's conservative provenance flag remains false. Neither value is a
native handle or an independently authenticated observation.

## Native validation

The [native workflow](../.github/workflows/bounded-model-application.yml)
runs the installed session consumer outside the checkout. It must observe two
builds for two fixed contexts, two successful requests in the first session,
one overflow that closes it, a rejected use after close, and one successful
request in the second session. A separate standard-library audit checks all
18 output values and four existing rejection controls against the unchanged
original record. CI retains the numerical packet and separate lifecycle
observation as `bounded-model-application-session-receipt`.

The source-bound CI artifact and PR record the actual result. These are
project-controlled observations and add no independent reproduction,
performance, general model or accelerator claim. See
[RFC0341](../rfcs/0341-bounded-model-application-sessions.md).
