# RFC 0330: Bounded CPU batch applications

Status: implemented with observed installed CPU execution at `c82d48d`.
Final CI and owner review remain required before acceptance.

## Problem and decision

The installed CPU CLI currently builds a graph for each input document. The
existing Python application handle already supports repeated calls to one
built immutable image. Expose that capability through an explicit `run-batch`
command, so applications can evaluate Linear and gated MLP graphs on several
datasets without writing a Python adapter or repeating the build.

The batch is an application request envelope, not a new IR operation or tensor
dimension. Source Intent, capability selection, HAC-IR, generated C, native
framing and runtime admission keep their existing contracts. One explicit build
is followed by sequential calls to the existing handle. Each call still starts
a fresh restricted container and sends all of its input tensors.

## Data boundary

`tuc.bounded_cpu_batch.v0` contains `schema_version`, `requests`, and optional
`shared_inputs`. Each request contains exactly `id` and `inputs`. Tensor values
use the existing flat row-major JSON number representation. Shared inputs are
convenient for weights and biases; omission means an empty shared mapping.

There are 1-16 requests. IDs match `[A-Za-z][A-Za-z0-9_-]{0,63}`, are unique and
case-sensitive, and retain their input order. Shared and per-request input names
must be disjoint. Each expanded input set must match all graph inputs exactly.
Missing names, unknown names and implicit overrides reject. No filename,
executable, image, backend or command can be selected by the envelope.

The pure bytes adapter uses the existing strict JSON scanner and FP32 input
encoder. It rejects duplicate keys, invalid UTF-8, BOMs, unknown fields, invalid
numeric literals, NaN/infinity, subnormal rounded values and nonzero underflow.
Signed zero is retained. It fully revalidates the graph and prepared application.

Bounds apply before execution:

- At most 2 MiB of JSON, depth 8, 200,000 lexical tokens and 64 characters per
  numeric token; existing tensor name/count and 4,096-element array limits.
- At most 65,536 expanded input elements across all requests. Shared values
  count once for every request in which they occur, not once for the document.
- At most 65,536 output elements across all requests, derived from the validated
  application manifest. This bounds result storage and JSON serialization.
- Existing graph limits remain eight operations, 24 tensors, dimensions 1-64,
  one million logical scalar operations and 256 KiB tensor storage per request.

All requests, IDs, shapes, numeric inputs and aggregate budgets pass preflight
before importing the execution runtime or creating a build context. Returned
records hold immutable tuples; creating a request's runtime mapping returns a
fresh dictionary. These inert records are not execution authority.

## Identity and results

Program identity remains the existing graph/compiler identity. Each request
digest remains the existing program identity plus its encoded complete FP32
input payload. Shared-versus-individual placement of identical values does not
change those identities.

The batch digest is SHA256 over ASCII JSON with sorted keys, compact separators,
no NaN, and no trailing newline, containing:

```json
{"schema_version":"tuc.bounded_cpu_batch.v0","program_digest":"...",
 "requests":[{"id":"sample_0","request_digest":"..."}]}
```

Request order and IDs affect batch identity; they do not affect program or
individual numerical request identity. Output uses the separate
`tuc.bounded_cpu_batch_cli.v0` schema, action `run-batch`, program/batch digests,
ordered `results` with `id`, `request_digest` and named `outputs`, and
`native_execution_observed: true` only after successful actual execution.
Digests identify data and do not authenticate execution or prove correctness.

## Execution and failure behavior

`tuc-cpu-app run-batch GRAPH --batch BATCH --workspace DIR` reads both regular
files through the existing bounded no-follow reader. Platform and workspace
requirements remain Linux x86-64 and the fixed existing local Docker operator.
The command builds once and executes requests in order using the same owned
handle, without changing compiler options or adding persistent sessions.

Results remain in bounded host memory until every requested run, output check
and handle cleanup succeeds. A malformed later request causes no build. A
runtime rejection stops further requests, attempts cleanup through the existing
context manager and publishes no result JSON. Earlier native requests may have
executed; there is no rollback or transaction across containers. An OS-level
stdout write failure can still prevent delivery of a completed result.

Invalid batch data produces exit code 2 and the closed `batch_json_rejected`
diagnostic. Runtime failures retain existing closed diagnostics and exit code 1.
Diagnostics contain no raw paths, input values, IDs or process output. Single
`run` and `inspect` commands retain their existing schema and behavior.

## Security, validation and limits

The new attacker-controlled surface is bounded JSON data and repeated use of an
existing explicit execution handle. Preflight expansion must count common
weights repeatedly, prevent duplicate identity/override ambiguity and bound all
retained results before starting work. Runtime import remains behind validation.
No source execution, plugin discovery, dependency, native protocol, compiler
artifact or container restriction changes are introduced.

Boundary tests cover malformed final requests, duplicate/hostile IDs, overlap,
shape/FP32 errors, expansion/output budgets, deterministic identities and signed
zero. CLI lifecycle tests check exactly one build, request order, first-failure
stop, input separation, cleanup and no partial result publication. Existing
single-call, runtime and native parser/sanitizer workflows remain required.

A separate standard-library consumer, installed outside checkout, owns six
fixed graph declarations and ordered FP32 equations. It exercises affine,
gated-MLP and elementwise product graphs in two profiles, changing data and a
second batch of an existing graph. It independently verifies complete public
bindings, program identity consistency with `inspect`, independently reconstructed
request/batch identities, exact results, malformed inputs,
numeric failure in later requests, original-file preservation and cleanup.
Synthetic candidates and mocked lifecycle tests do not establish native runs.

CI reuses pinned read-only actions and hash-locked dependencies, builds an
offline wheel and retains the original observation bound to source, wheel and
consumer hashes. Acceptance requires actual installed observations and final
checks. Shared inputs do not mean resident weights; this slice makes no latency,
throughput, cache, concurrency, general model or GPU claim.

## Observed execution

[CI run 35609641378](https://github.com/kirchherr/TUC/actions/runs/35609641378)
passed at `c82d48dc69d9bc2cd20b1e86577004ed3518960d`: 642 boundary/lifecycle tests,
an offline wheel build and installation outside checkout, then seven batches
across six fixed programs with 21 results and 96 bitwise FP32 comparisons.
Six malformed batch controls and two runtime numeric failures at the second or
last request produced exact closed diagnostics, empty stdout, unchanged fixture
files and clean workspaces. These observations do not measure native build counts.

The [original receipt](../docs/evidence/bounded-cpu-batch-35609641378.json) is
retained without reserialization: 16,805 bytes, SHA256
`bb4301048b4083f303752adef4e310174441edb110cbe58db28f18a0cf206872`.
Artifact `10642149808` contained only `ci-record.json`; its ZIP SHA256
`7e9700de5d270ccf94c031f2408a9f54ec276d851f34456bca6331a3e4563e29`
matches GitHub metadata and the upload log. Consumer SHA256 is
`65845aee71a999e4ccb01ef5fa4c5267af3268c91694980e0f2d231ca746545b`.
Wheel SHA256 is
`f6cde7b54dbe9f33888554e788c85ba8817fe29b783413dde07b71a309d44ced`,
matching the build log. The artifact contains no wheel or container image.

A separate local audit reconstructed all six graph declarations, public bindings
and compiler program identities; every request and batch digest, original input
hash and rejection-control identity matches the receipt. Ordered NumPy FP32
equations independently match all 96 observed scalars, including signed zero.
This audit checks the retained evidence; it does not reinstall or rerun the
native wheel. Existing native parser and sanitizer workflows remain required
for the final revision; this feature leaves their C emitters and runtime unchanged.
