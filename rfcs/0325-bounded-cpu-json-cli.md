# RFC 0325: Bounded CPU JSON Application CLI

Status: implemented; native CLI conformance observed. Owner review and final CI
remain required.

## Problem and decision

RFC 0324 executes caller-defined supported CPU graphs, but applications must
construct Python records and write integration code. Add an installed
`tuc-cpu-app` console with inert `inspect` and explicit native `run` commands.
It accepts the existing `source_intent.v0` plain-data graph format and a new
versioned tensor-input envelope. It delegates all code generation and native
execution to RFCs 0321–0324.

The adapter is `tuc.compiler.bounded_cpu_json`, next to the bounded compiler
facade. It reuses `source_intent_from_mapping` after strict JSON preflight and
the bounded compiler's exact reconstruction for shape, SSA, work, storage and
terminal-return checks. This keeps the old frontend data-only and avoids a
frontend dependency on compiler or runtime machinery. The existing research
Python/Triton parser and source-ingestion gates remain separate.

## Public surface and semantics

```text
tuc-cpu-app inspect GRAPH.json
tuc-cpu-app run GRAPH.json --inputs INPUTS.json --workspace DIR
tuc-cpu-app --help
```

`inspect` returns ordered public I/O and the inert application identity.
`run` returns named arrays after build, execution, validation and cleanup.
There is no implicit default run, filename-to-Python import, arbitrary image,
external capability document, plugin, remote endpoint or command argument.
The CLI owns one fixed C11/host capability named `json_cpu`; graph data remains
hardware-neutral. A fresh image is built per CLI run; reusable Python handles
remain available through RFC 0324.

The pure functions are `source_intent_from_json(data: bytes)` and
`inputs_from_json(module, bindings, application, data: bytes)`. The latter
converts JSON tensor arrays to tuples of exact Python floats and invokes the
existing full application/input validation. No function in the JSON adapter
reads files, imports input-specified modules or starts a native process.

Graph schema version is explicitly `source_intent.v0`. Input keys are exactly
`schema_version` (`tuc.bounded_cpu_inputs.v0`) and `inputs` (named flat arrays).
Integers and fractional input numbers both have binary64 decoding semantics,
then the existing binary32 conversion and arithmetic contract applies. Negative
zero is retained. Nonzero-to-zero conversion at either precision rejects.
Input bool/null/string/nested array values reject. Graph dimensions stay exact
integer tokens. This distinction is transport conversion, not a relaxation of
the existing Python runtime's exact-float boundary.

## Parser and file trust boundaries

Attacker-controlled bytes are bounded before decoding: graph 64 KiB, input
2 MiB. A string/escape-aware scan limits depth to 12/6 and lexical token count
to 4096/200000 before `json.loads`. Numeric tokens are capped at 64 characters.
Strict UTF-8, BOM/surrogate rejection, duplicate-key detection and finite-number
checks prevent ambiguous or resource-expanding inputs. Schema, field and graph
collection bounds precede the older Source Intent intake. Exact reconstruction
then applies the existing eight-op/24-tensor/shape/work/storage contract.

The file CLI requires Linux x86-64. A descriptor-relative path walk opens
directory components with no-follow semantics. The leaf is opened nonblocking
and checked with `fstat` before reading: only a bounded regular file is accepted.
Reading stops at the byte budget plus one; size/identity/timestamps are compared
again afterward. Symlink components, parent traversal, devices and FIFOs reject.
The opened descriptor fixes the object being consumed despite namespace changes;
metadata checks detect ordinary concurrent content drift. Host administrators
and a malicious same-privilege process are not sandboxed by these checks.

The portable bytes API remains usable on Windows. The file CLI does not claim
Windows reparse-point safety through a race-prone stat/open check, and adds no
Win32/ctypes executable surface. Help is available everywhere.

## Execution and output boundaries

The CLI validates graph, input data and encoded request before importing the
explicit application runtime or invoking build. RFC 0324 owns the fixed local
Docker socket, trusted executable/configuration, exact USTAR source stream,
immutable image identity, container isolation, pipe bounds, timeouts and cleanup.
Neither its implementation nor the C11 emitter/parser is changed by this RFC.

The complete result is validated and serialized in memory, capped at 2 MiB,
then emitted as one compact ASCII JSON document with a newline. Schema version
is `tuc.bounded_cpu_cli.v0`. Run results contain program/request digests and
named outputs; inspection declares no native observation. Nothing is published
before the runtime context manager finishes cleanup. A transport write failure
may interrupt stdout delivery and is not an atomic-publication guarantee.

Exit codes are zero (success), two (arguments/platform/file/JSON rejection),
or one (runtime/output failure). Diagnostics use closed reason codes without
paths, argument values, source/input contents, traceback or raw process logs.
Argument parsing has no abbreviation, from-file expansion or duplicate-option
override. Numeric native errors remain distinct from malformed frames and
process/timeout/cleanup errors. There is no fallback.

## Validation and observations

Pure tests cover JSON-vs-typed artifact identity, ordering, strict syntax,
schemas, numeric conversion, byte/depth/token/collection boundaries, rejection
before legacy intake and unchanged original compiler/runtime contracts.
CLI tests cover platform and argument grammar, descriptor-based file reads,
symlink/FIFO rejection, bounded output, no build on invalid inputs and no
publication when execution or cleanup fails. Mocks are not native evidence.

The installed standalone consumer owns three graph families (fanout, true
fanin and ReLU/Sum), two shape profiles and two input corpora per program.
The native requirement is 12 CLI calls and 56 independent binary32 scalar
comparisons, plus one checked overflow rejection and six malformed/duplicate/
symlink file controls. Each invocation must leave input files unchanged and
its workspace clean. The wheel and console are used outside the checkout.

The dedicated read-only workflow records actual results with source revision,
wheel SHA-256, consumer SHA-256 and per-program/request identities. Its actions
are commit-pinned and existing hash-pinned dependencies/toolchain are reused.
No new dependency, credentials, repository protections or release workflow is
introduced. Test plans and synthetic responses cannot substitute for actual
execution.

The [push CI run 35343784690](
https://github.com/kirchherr/TUC/actions/runs/35343784690), job `105595495204`,
succeeded on source revision `1b2a1ce4d8db86de320af341dd5f44ada916aa79`.
It passed 308 tests in 8.84 seconds and observed the installed CLI outside the
checkout completing all six programs, 12 successful calls and 56 independent
scalar comparisons. The checked numeric rejection and all six negative
controls passed; original input files were unchanged and workspaces were clean.
The [original receipt](../integration/bounded_cpu_json/observed-ci-1b2a1ce.json)
binds these results to the executed revision and its wheel, consumer and program
identities. This observation does not cover later revisions; owner review and
final CI remain required.

Prior C11/GPU sources, observations and proof goldens retain their original
scope. This is a bounded CPU application interface, not general source ingestion,
arbitrary kernel support, CUDA admission, a production sandbox or a performance
claim. User examples are in the [guide](../docs/BOUNDED_CPU_JSON_CLI.md).
