# RFC 0305: Second Source Program With Native Reduction

## Status

Implemented for review. Native acceptance requires the dedicated C11 workflow
to pass execution, sanitizer execution, and all three wrong-code probes.

## Context

RFC 0304 links one Matmul-plus-ReLU source program to two target observations.
Another evidence wrapper around that program would not test a new semantic
case. The existing research parser already handles a distinct source program:
matrix multiplication followed by an axis-1 sum, returning a vector.

## Decision

Add a separate fixed `matmul_reduction` C11 experiment. Parse the reviewed
inert module using the existing bounded research ingress, require the exact
canonical Source Intent digest, validate its typed dataflow, and derive C11
loop bounds from its shapes. Emit only fixed function symbols. The source and
all generated files must agree before any explicit native procedure starts.

The reviewed program computes `sum(A @ B, axis=1)` for FP32 `A[4,8]` and
`B[8,2]`, producing `y[4]`. It reuses the public input vector from RFC 0302;
the expected output is separately fixed as `[-5.875, 2.625, 5.125, 4.75]`.
A Python rational oracle and a binary64 C oracle contract B's columns before
applying A. All values in this fixed case are exactly representable; exact
comparison is intentional and is not a general floating-point guarantee.

Build static x86_64 C11 in the already reviewed digest-pinned GCC image.
Execute in `scratch` with a read-only filesystem, no network or mounts,
non-root identity, dropped capabilities, no-new-privileges, default seccomp,
and CPU, memory, PID, file-descriptor, core-dump and wall-clock bounds.
The worker checks its UID/GID, capability, privilege and seccomp facts and
uses a five-second alarm. The operator script cleans up its named container
even on timeout. No operator script is reachable through the TUC runtime.

Run a separate ASan/UBSan build with the same containment. Leak detection is
disabled because this experiment checks memory access and undefined behavior,
not an allocator or lifetime implementation. The sanitized image retains
the pinned compiler runtime; the accepted static image contains one binary.

Build and execute three fixed, in-bounds wrong-code variants against the
unchanged oracle: overwritten accumulation (missing sum), accidental ReLU,
and transposed reduction indexing (wrong axis). Each must exit with a
reference mismatch after exactly two calls. A crash, timeout, build failure,
or container security failure does not count as detecting wrong code.

## Security And Claim Boundary

The emitter is pure: no compiler process, source execution, imports from the
provided module, dynamic loading, device access, or artifact execution.
Only the operator procedure builds and executes the fixed artifacts. Public
observations contain digests, shapes, counts and results, never tensor values,
source, commands, host paths or device identifiers. The validator binds the
observation to fresh emission and rejects extra keys and bool/integer swaps.

This is a second source program on one C11 target, with same-maintainer
evidence. It does not extend the existing two-target equivalence claim to
reduction. General source ingestion, arbitrary programs, a general CPU backend,
normal runtime admission, performance, independent reproduction, and universal
hardware claims remain unsupported. The fixed source is parsed at review time
in-process; this RFC does not claim a new OCI source-worker observation.

## Validation

- Pure emission, fixed Source Intent, reference, rejection and report tests.
- Reproducible source/plan files and a closed observation schema.
- Native preflight with zero generated calls, then exact terminal output.
- ASan/UBSan execution of the same generated functions and harness.
- Three actually compiled wrong-code variants rejected by the same reference.
- Existing C11, CUDA/source-to-target, frontend and claim-boundary regressions.

## Next Research Question

Can this second program retain its axis and terminal semantics on a second
materially different compiler target? That result requires actual execution
and a separate acceptance decision, not a schema change or a renamed target.
