# RFC 0326: Explicit bounded source-to-CPU application bridge

Status: implemented; installed native conformance observed at `1da2276`;
final revision CI and owner review pending.

## Problem and decision

RFC 0325 executes caller-owned supported JSON graphs, but users must spell out
every tensor and operation record. The existing research parser already handles
a small Triton-like notation. Add an explicit installed conversion command that
parses that notation in the fixed isolated OCI worker, validates its result
against the bounded CPU subset, and emits actual graph JSON. The existing
`tuc-cpu-app` then inspects and executes the emitted graph with caller inputs.

This RFC authorizes that narrow research bridge. It does not change the default
parser, general source-ingestion admission, backend discovery, plugin admission,
the metadata-only source-buffer API, or prior research claim gates. Source text
is data throughout; no import, decorator, JIT, function object or source program
is evaluated. The parser's accepted syntax is broader than the CPU subset, so
parent-side compiler validation remains required after successful parsing.

## Public boundary

```text
tuc-source-to-json SOURCE.py --signature SIGNATURE.json --workspace DIR
tuc-source-to-json --help
```

The file command explicitly builds and runs a parser container on Linux
x86-64. Help is portable and starts no process. Source and signature paths use
the existing descriptor-relative no-follow regular-file reader. The signature
is exactly `schema_version` (`tuc.bounded_cpu_source.v0`), `source_name`,
`kernel_name` and `tensor_shapes`. Shapes describe every function argument,
including public `tl.store` targets. Identifiers are ASCII with at most 64
characters; at most 24 shape entries have rank one or two and dimensions 1–64.

The accepted language is one `@triton.jit` function with literal `import triton`
and `import triton.language as tl`; assignments use two-argument `tl.dot`,
ReLU spelled `tl.where(x > 0.0, x, 0.0)`, and `tl.sum(x, axis=1)`. Terminal
values are explicitly stored with `tl.store(public_name, value)`. No loops,
loads, pointer arithmetic, mask arguments, constexpr, arbitrary calls or
softmax execution is introduced. Input argument names and public return aliases
are disjoint in this bridge. All required terminal results must be returned.

`prepare_source_request(source: bytes, signature: bytes)` is pure transport
validation. `decode_source_response(request: bytes, response: bytes)` checks the
worker response and returns bounded canonical graph JSON with a newline.
Neither function parses a Python AST or starts a worker. The explicit runtime
`convert_bounded_cpu_source(..., workspace=Path(...))` owns the worker lifecycle.

## Parser isolation and package boundary

Source bytes are capped at 64 KiB and 2048 lines, signature JSON at 16 KiB,
the encoded request at 96 KiB and the worker response at 256 KiB. Strict UTF-8,
duplicate-key rejection and pre-decode JSON structure/token bounds protect the
host transport. AST preflight and parsing occur only inside the worker, with
the existing CPU, address-space, file-size and descriptor limits.

The installed adapter bundles only six fixed, original frontend modules and
empty package initializers. It verifies their fixed import closure; those
trusted package files alone are inspected as AST on the host. This avoids
loading unrelated package initializers or NumPy into the worker. No caller
source, signature, tensor data, arbitrary path or command enters the build
context. A fresh bounded USTAR stream supplies the fixed sources and Dockerfile.

The parser reuses the existing digest-pinned Python base and Dockerfile frontend
without package installation or build networking. Its local Docker executable,
endpoint, environment, empty configuration, directory ownership and immutable
image identity follow RFC 0324. Runtime fixes UID/GID10001, no network, no host
mounts/devices, a read-only root, dropped capabilities, no-new-privileges,
seccomp, private IPC, CPU/memory/PID limits and a bounded noexec tmpfs.
The unchanged worker reports its observed isolation facts; the parent checks
exact values and types. Host and Docker administrators remain trusted.

Bounded concurrent pipe draining and deadlines apply to Docker operations.
Failure or interruption removes the owned container and attempts image/context
cleanup. A successful, exactly name-filtered Docker lookup must confirm that
the owned container is absent, including after normal automatic removal.
A cleanup failure prevents graph publication. There is no fallback
to the host parser or the weaker process-only research worker.

## Result validation and semantics

The parent checks protocol, request/source binding, source-free ingress report,
observed isolation, graph schema, exact signature coverage and shapes. It then
passes the graph through RFC 0325's full bounded source validation. Eight
operations, 24 tensors, required terminal returns, SSA, static FP32, shape,
work and storage limits remain in force. Compiler/runtime contracts and native
arithmetic are unchanged.

Stdout contains only the canonical graph document, after successful parser
cleanup. It contains structured graph data, not raw source or execution claims.
Normal CPU execution remains an explicit second command. Program/request hashes
provide identities, not authentication or proof of source semantics. A failed
stdout transport can interrupt delivery; no atomic filesystem write is claimed.

Exit codes: zero for conversion/help, two for arguments/files/source/signature/
graph rejection, one for worker/runtime/output failures. Stderr contains only a
closed `tuc-source-to-json: reason` diagnostic, without source, paths, user data,
tracebacks or Docker logs.

## Validation and supply chain

Pure tests exercise malformed signatures and hostile response documents, exact
security types, request/source binding, invalid shapes and unsupported graphs.
Runtime tests check fixed build contents, installed import closure, bounded
processes, immutable image use and cleanup on all error paths. CLI tests check
validation before runtime import, closed arguments and no premature publication.
Mocks are synthetic and cannot establish successful native execution.

The independent installed consumer owns six source programs across fanout,
true fanin and ReLU/Sum shape profiles. Six conversions feed twelve CPU calls
and 56 independent binary32 comparisons. Ten negative controls cover malicious
source constructs, invalid signatures, nonterminal returns and parser-valid
softmax outside the CPU subset.
Original source/signature/input bytes and cleanup are checked. Its new read-only
workflow retains observed results bound to the source revision and installed
wheel/consumer hashes. [Run 35346924415](
https://github.com/kirchherr/TUC/actions/runs/35346924415) observed all six
conversions, twelve CPU calls, 56 comparisons and ten rejection controls at
`1da22767afcd396ac90a1fa3b0c5663840080c9d`; all 573 Linux boundary tests passed.
The [unaltered receipt](../integration/bounded_cpu_source/observed-ci-1da2276.json)
preserves that source identity and does not claim a later revision was run.

Existing parser/worker sources, proof goldens and earlier records are unchanged.
No new dependency, credential, package release, remote host, GPU execution or
repository-protection change is introduced. The narrow CPU research result
does not establish general Triton compatibility, production sandboxing or
performance parity. Owner review and final revision CI remain required.
