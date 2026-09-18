# RFC 0324: Explicit Bounded CPU Applications

Status: implemented slice with observed native CI; owner review required.

## Problem and decision

RFC 0323 emits a checked C11 function for a whole graph, but application authors
still need a native caller and transport. Add an installed-package API that
prepares a complete fixed CPU program and, through a separate explicit runtime
module, builds and runs that program for caller-supplied graph data.

The compiler module `tuc.compiler.bounded_c11_application` remains inert. The
runtime module `tuc.runtime.bounded_c11_application` exposes explicit build,
run and close actions. Neither import grants normal runtime admission or
registers an executable backend. Prior primitive emitters, evidence and CUDA
paths retain their existing contracts.

## Public interfaces

```python
prepare_bounded_c11_application(module, backend_bindings) -> BoundedC11Application
validate_bounded_c11_application(module, backend_bindings, application) -> None
encode_bounded_c11_inputs(module, backend_bindings, application, inputs) -> bytes
decode_bounded_c11_outputs(
    module, backend_bindings, application, request, response, exit_code
) -> dict[str, tuple[float, ...]]

build_bounded_c11_application(module, backend_bindings, *, workspace: Path)
    -> BuiltBoundedC11Application
# Built handles provide run(inputs), close(), program_digest and a context manager.
```

Preparation compiles and fully revalidates Source Intent, emits the checked C11
entrypoint, and revalidates that entrypoint before constructing the application.
Only selected CPU operations are accepted. Unused valid capabilities remain
bound to the original source contract. Existing graph, type, shape, SSA, public
return, storage and logical-work bounds remain in force.

The frozen application record contains `entrypoint`, `application_c`,
`application_h`, `application_json`, `dockerfile`, `dockerignore`, `build_sh`
and `program_digest`. Its fresh `files()` mapping contains nine fixed filenames:
three entrypoint files, three application files, Dockerfile, Dockerfile.dockerignore
and build.sh. Aggregate text is bounded by 512 KiB; application metadata by 64 KiB.
Validators require exact records, field sets, strings and containers before
comparing every field with a fresh deterministic reconstruction. Caller methods,
equality hooks and mutable nested compiler metadata do not choose emission.

The program digest is SHA-256 over the canonical nine-file template with a zero
program digest. That template includes the entrypoint, application source/header,
protocol metadata and fixed build recipe. A second materialization injects the
digest and updates source hashes. This avoids a self-reference while binding
every generated input. Hashes provide byte identity, not authenticity.

## Fixed byte protocol

Public tensor order is fixed at preparation. Public return aliases preserve
their declared order. No names, shapes, counts, offsets or allocation sizes are
parsed from native input.

| Frame | Layout |
| --- | --- |
| Request | `TUCIN001` (8 bytes), program digest (32), request digest (32), fixed FP32 inputs |
| Success response | `TUCOUT01` (8), program digest (32), echoed request digest (32), status (4), fixed FP32 outputs |
| Checked error response | Same 76-byte response header, no output payload |
| Invalid protocol | No response bytes |

FP32 and status use little-endian bytes. The host request digest is
`SHA256(program_digest_bytes || input_payload)`. Native code validates version,
program identity and the exact frame size before decoding input bits. The
request digest is opaque to native code and is echoed unchanged. Host decoding
rechecks the request hash and the response identity. This guards against stale
or mismatched frames without claiming authentication against a hostile producer.

The C function is:

```c
int tuc_application_process(const unsigned char *request, size_t request_size,
                            unsigned char *response, size_t response_capacity,
                            size_t *response_size);
```

The caller provides live, disjoint buffers and response-size storage. There are
no heap allocations or variable-length arrays. Header constants expose the
fixed request/response sizes. Exit zero means status zero and full output.
Exit one means a checked C11 status from one through three and only the header.
The process function returns two for invalid protocol or arguments, with response
size zero. The executable also exits two on stdout transport failures, which may
leave partial bytes; the host rejects them. The maximum frame budget is 262,220 bytes.
Generated main reads at most
the expected request size plus one byte, requires EOF before execution, sets a
five-second alarm and checks stdout writes and flushing.

`TUC_APPLICATION_NO_MAIN` permits a separate native parser harness to call the
same function. This does not expose runtime graph selection. The fixed-array
storage budget includes entrypoint tensor scratch, main/process buffers and a
64 KiB bookkeeping reserve, capped at 1 MiB. It is a source-level budget, not a
measured compiler stack-frame size.

Python inputs require exact dictionaries, string keys, tuples and floats.
Rounding to FP32 rejects non-finite values, subnormal results and nonzero-to-zero
underflow. Response decoding rejects exceptional bit patterns before exposing
float values. The RFC 0323 checked arithmetic policy applies to every native
product and accumulation. A fully validated error response raises
`BoundedC11ApplicationExecutionError(ValueError)` with a read-only status; an
invalid response remains an ordinary `ValueError`.

## Explicit runtime boundary

Build first creates independent validated snapshots of the module and bindings.
The handle retains these snapshots and verifies the original objects against
the bound application before each run, so later caller mutation cannot select
a different program. Handles have no public constructor or subclass hook;
authority is the exact object identity in a private weak registry. The registry
stores the immutable Docker image ID, private context and lifecycle state.
No caller-supplied image, compiler, command, Docker endpoint or executable source
fragment is accepted.

The implementation supports Linux x86-64 and the fixed local Unix Docker socket.
Docker resolution uses a fixed trusted PATH, root-owned executable and parent
directories, and recorded executable identity. Every invocation receives a fresh
empty Docker configuration/home and a minimal environment. Caller Docker
contexts, inherited credentials, `DOCKER_HOST`, arbitrary PATH entries and CLI
configuration are not inherited. The local daemon and host remain trusted.

The build sends an exact allowlisted USTAR archive through stdin. It is generated
from the already validated in-memory files; Docker never discovers the build
context by traversing a caller directory. The private on-disk copy provides
inspectable context and drift checks. Directories are user-owned, not
group/other-writable and have no symlink components. File creation is exclusive
and uses descriptor-relative no-follow operations. Cleanup verifies ownership,
inode identity, file types, depth and entry budgets before removing owned paths.

Docker builds use the pinned recipe, the static target, no build cache reuse and
network-disabled build commands. Image resolution may still involve the trusted
daemon; offline operation requires the pinned inputs to be present. Each run
uses the inspected image ID, never an external tag. Container arguments fix the
entrypoint, UID/GID, read-only root, no network, no capabilities, no new privileges,
private IPC, bounded tmpfs and resource limits. No host bind mount is accepted.

Process I/O is multiplexed with bounded pipes, avoiding unbounded `communicate()`
buffering. Build logs are capped at 2 MiB per stream; response stdout is capped at
the expected frame length and run stderr at 4 KiB. Deadlines are 600 seconds for
build, 30 for run and 10 for control commands. Timeouts and output-limit failures
terminate the process group and trigger owned-container cleanup. The caller must
close the handle, preferably through its context manager. Cleanup reports failure
instead of granting authority to remove unverified paths. This boundary does not
defend against a malicious Docker daemon, host administrator or arbitrary native
pointer misuse inside the separate C process API.

## Validation and evidence limits

Pure tests cover full application reconstruction, field/type/size boundaries,
request and response mutations, exact exit/status matching, FP32 rejection and
the distinction between checked native errors and malformed protocol. Runtime
tests use controlled process responses and do not prove Docker execution.

The installed consumer defines two independent applications: a projection with
ReLU and row totals, and standalone ReLU. The explicit native run requires three
input cases and two replays for each graph: 12 successful runs, 72 scalar checks,
and one separately verified numeric overflow rejection. The static application
is built through the public runtime API.

A separate ASan/UBSan harness exercises the generated parser with a fixed seed,
every truncation, extra bytes, every single-bit mutation, exceptional FP32 words,
undersized response capacities and null arguments. Expected case counts are
1,368 for projection and 1,092 for activation. Request-digest bit changes must
echo successfully in native code; host tests independently require hash matching.
The sanitizer main is also checked for exact success bytes and empty responses
to truncated, oversized and wrong-program frames.

The workflow installs a wheel outside the checkout and retains program/harness
identities, source commit, wheel hash and actual results only after its checks
pass. Native [run 35339997831](https://github.com/kirchherr/TUC/actions/runs/35339997831),
job `105583474523`, passed on `c9ebb2675f5114b7332284ce5fa380e8f259bb43` with
333 Linux tests and all application/parser requirements above. The original
[observed record](../integration/bounded_cpu_application/observed-ci-c9ebb26.json)
has SHA-256 `db4520bbd840d3f4ca743e68cf01eb9e671934f75a67acd4469a1df9c8e9777e`.
Its GitHub artifact `10544721871` ZIP has SHA-256
`99d2872fa25642945c39a092a16f5a9cf3d8556cea90e8fb0e8f42a20ec8b27f`;
the wheel identity remains in the record. These observations establish this
corpus at that revision, not broad correctness, performance, CUDA support or
normal runtime admission. Synthetic protocol fixtures remain separate from
this actual execution record.

The [application guide](../docs/BOUNDED_CPU_APPLICATION.md) contains a complete
user-defined graph example. The [installed consumer](../integration/bounded_cpu_application/README.md)
describes the explicit validation commands.
