# RFC 0334: Bounded Python CPU model sessions

Status: Implemented with installed execution observed; final CI and review pending.

## Problem and contract

RFC 0333 packages graph data and fixed parameters, but its single-call CLI builds
on every invocation. A Python application needs to supply later inputs without
rebuilding. `tuc.bounded_cpu_model_session.open_cpu_model(model_bytes, workspace=Path(...))`
creates an inert, factory-only handle. The first valid `run(input_bytes)` builds
the existing CPU application. Subsequent runs reuse its image and context while
each request executes in a fresh isolated container. No resident weights, daemon,
new native protocol, operation, backend capability, or performance claim is added.

Every call expands fixed parameters and validates the complete request before
runtime import or execution. Program, model and request identities retain RFC
0333 semantics. Frozen results contain these identities, one-based sequence and
immutable ordered output tuples. Results do not confer execution authority.

## Lifecycle and bounds

One session admits at most 16 successful requests, 65,536 expanded input elements
and 65,536 output elements cumulatively. Fixed parameters count for every request.
Existing graph, JSON, FP32, execution timeout and process-output limits apply.
Input and budget rejections preserve the live session and consume no execution
budget. Concurrent run/close calls fail with `session_busy`; they never overlap.

A build, execution, identity or output-validation failure closes the session and
attempts cleanup before raising a closed diagnostic. `KeyboardInterrupt` and
other non-Exception failures also trigger cleanup, then propagate. Cleanup
failure reports `cleanup_failed`; the closed handle retains cleanup authority so
`close()` can retry. Closing is idempotent after success. Callers must use a context
manager or explicitly close; garbage collection is not resource management.

Results publish per successful call, before final session cleanup. An error in a
later call or in close does not revoke earlier values. This differs deliberately
from the all-or-nothing result publication of the batch CLI. The session retains
neither prior input payloads nor output histories. The Python caller controls its
own trusted process; private registries are not an in-process sandbox.

## Security and validation

The only model/input surfaces are bounded bytes. No caller graph objects, plugins,
external weights, backend selection, arbitrary commands or image names are accepted.
Workspace admission and native lifecycle are delegated to the existing explicit
runtime. Handle identity is registry checked; direct construction, subclassing,
copying and forged unregistered handles cannot grant execution authority.

Tests exercise preflight without executable runtime imports, identity stability,
parameter changes, malformed data, exact limits, cumulative expanded budgets,
concurrent close/run, malformed results, build/execute/cleanup failures and cleanup
retry. An installed consumer checks Linear and Softmax equations independently,
unchanged owned context identity across repeated calls, 16-call limits, parameter
variants, numeric rejection and empty workspace after close. Synthetic tests are
not native evidence. Actual installed observations are retained only after CI.

## Compatibility and supply chain

Existing CLI commands and schemas stay unchanged. Python 3.11+ API, no new
dependencies. A read-only pinned workflow builds an offline wheel, installs it
outside checkout and runs the independent consumer with `python -I`. Native
arithmetic and sandbox code are unchanged and remain covered by existing native
and sanitizer workflows. Full CI and owner review remain required.

## Observed execution

[Run 36570752112](https://github.com/kirchherr/TUC/actions/runs/36570752112)
passed at `f4dbcc9a109142fad5bb2734443532cdbc6345d6`: 239 tests, offline wheel
build and isolated installation, then four sessions with 21 successful calls.
All 42 scalar comparisons passed (38 bitwise, four tolerance), together with
17 stable-context checks, 20 malformed-extent rejections and nine additional
input/lifecycle controls. Numeric rejection closed the session and cleared its
workspace while the earlier result remained available.

The unchanged [original receipt](../docs/evidence/bounded-model-session-36570752112.json)
contains 8,508 bytes, SHA256
`6e94549a7e11d5501198ac0e7070e4b4f909d5148345e98902cb5b42aa686d1a`.
Artifact `11033643495` ZIP SHA256
`cab949642937d3cafe932eb0e41641b78543058f6748b8bb3793dee4c5750cdf`
matches the downloaded archive and metadata. Wheel SHA256
`60546f131e2473e9cfd3eeca8a0e38342be3e5a37010e5a64522f88df7ee7dfd`
matches the build log; the consumer hash matches the observed source revision.
The artifact retains the receipt, not wheel/image bytes or host context paths.

A separate local audit reconstructed three model/program identities and 21
request bindings. Independent NumPy equations matched all 42 observed values,
including the 38 exact FP32 bit patterns; maximum absolute Softmax difference
was `1.4551915228366852e-11`. This audit did not repeat native execution.
Final CI and owner review for [PR #131](https://github.com/kirchherr/TUC/pull/131)
remain required.
