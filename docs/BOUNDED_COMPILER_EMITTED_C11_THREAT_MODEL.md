# Bounded Compiler-Emitted C11 Threat Model

## Scope

This threat model covers RFC 0303, the exact Source Intent C11 emitter, its
checked-in generated files, the static `x86_64` ELF image, and the controlled
host observation. It does not authorize arbitrary C, a general CPU backend,
or generated-artifact execution in the normal TUC runtime.

## Assets

- build-host and execution-host integrity;
- repository, credentials, container daemon, kernel, and seccomp boundary;
- correctness of the admitted Source Intent semantics;
- integrity of emitted C11, the static executable, and public evidence;
- the existing TUC executor and native-backend admission gates.

## Untrusted Inputs

- Source Intent and workload JSON bytes;
- JSON duplicate keys, number forms, encodings, nesting, and sizes;
- checked-in generated files and the Docker build context;
- Compose-rendered configuration and image inspection metadata;
- worker stdout, stderr, exit status, and process-security observations;
- repository changes proposed through pull requests.

## Threats And Controls

### Source Data Becomes Executable Syntax

Threat: source names, attributes, or strings are interpolated into C tokens,
identifiers, includes, compiler options, or commands.

Controls: the emitter accepts one canonical payload digest, invokes typed
Source Intent validation, checks the exact Matmul-plus-ReLU semantics, and
selects only fixed templates and symbols. It performs no evaluation, dynamic
import, subprocess call, device access, or file write. The build command and
compiler flags are fixed in the reviewed Dockerfile.

### Parser Ambiguity Or Resource Exhaustion

Threat: malformed UTF-8, duplicate keys, non-finite numbers, deep nesting,
large inputs, or file replacement cause inconsistent decisions.

Controls: strict UTF-8 and JSON decoding, duplicate-key and non-finite-number
rejection, byte/depth/item budgets, symlink rejection, before/after size
checks, canonical serialization, and diagnostics that do not echo rejected
input values.

### Generated Artifact Substitution

Threat: reviewed Source Intent is paired with a different header, source file,
workload, or lowering plan.

Controls: checked-in generated files must match fresh deterministic emission
byte for byte. File and payload digests are repeated as build arguments, OCI
labels, image-inspection assertions, and report provenance. The Docker build
also verifies exactly two allowlisted generated symbols.

### Harness Smuggles Computation

Threat: hand-written functions in the harness bypass the compiler-emission
claim or execute an additional workload.

Controls: generated function definitions exist only in the generated C11
translation unit; the harness contains only declarations through the generated
header and exactly two fixed calls. Static checks reject generated definitions
in the harness, symbol drift, dynamic loading, subprocess APIs, allocation
APIs, threads, networking, or device access.

### Toolchain Or Binary Drift

Threat: a mutable toolchain, architecture change, dynamic dependency, or
runtime compiler expands the reviewed execution boundary.

Controls: the builder uses the digest-pinned official GCC 14.2.0 image and a
fixed `linux/amd64` platform. The build uses fixed C11, hardening, and static
link flags; checks the ELF architecture; rejects dynamic `NEEDED` entries; and
installs only the executable and three metadata files into a `scratch` image.
There is no runtime compiler, shell, package manager, JIT, CUDA dependency, or
device node.

### Host Or Container Compromise

Threat: execution reaches the network, repository, host files, privileged
APIs, or unbounded resources.

Controls: the worker has no network, mounts, devices, or GPUs; runs as UID/GID
10001 in a read-only `scratch` filesystem; drops all capabilities; enables
no-new-privileges and seccomp; uses private IPC; and is limited to one CPU,
128 MiB memory, eight PIDs, 4 MiB shared memory, bounded output, and a 20 second
deadline. The worker confirms effective capabilities, no-new-privileges, and
seccomp state from `/proc/self/status` before accepting execution.

### Wrong Result Or Inflated Claim

Threat: the binary runs but does not preserve the admitted semantics, or its
PASS is reinterpreted as universal portability.

Controls: a separately implemented double-precision loop checks the fixed
public vector, then compares finite terminal outputs within the fixed float32
tolerance. A closed schema fixes every positive and blocked claim. The report
states that the normal executor is unchanged, no native backend is admitted,
performance is unmeasured, cross-ISA portability is untested, and independent
reproduction is not yet supplied.

### Evidence Leakage

Threat: public evidence exposes tensor values, source text, generated source,
host paths, commands, environment data, or hardware identifiers.

Controls: worker and report protocols use exact metadata-only key sets and
bounded serialization. Tests reject extra keys, non-finite data, host-specific
strings, source material, raw values, and timing samples.

## Residual Risk

- GCC, its pinned container layers, the container runtime, host kernel, and
  seccomp implementation remain trusted dependencies.
- Static linking reduces runtime dependencies but does not prove toolchain or
  libc correctness.
- SHA-256 and OCI labels establish identity, not benign behavior.
- One fixed vector and one `x86_64` ISA have limited wrong-code coverage.
- Same-maintainer execution is not independent reproduction.

These limits keep arbitrary programs, universal hardware support, a general
CPU backend, production admission, performance claims, and vendor replacement
explicitly blocked.

## Evidence

- schema:
  `schemas/bounded_compiler_emitted_c11_observation_report.v0.schema.json`;
- accepted report:
  `tests/golden/proofs/bounded_compiler_emitted_c11_observation_report.json`;
- tests: `tests/test_bounded_compiler_target_equivalence_proof.py`;
- decision: `rfcs/0303-bounded-compiler-target-equivalence-proof.md`.
