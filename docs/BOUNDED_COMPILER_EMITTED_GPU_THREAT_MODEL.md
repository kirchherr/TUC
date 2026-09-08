# Bounded Compiler-Emitted GPU Threat Model

## Scope

This threat model covers RFC 0302, the exact Source Intent emitter, its
checked-in CUDA artifacts, the dedicated SASS-only image, and the opt-in
physical observation. It does not authorize a general CUDA backend or generated
artifact execution in the normal TUC runtime.

## Assets

- maintainer workstation and remote GPU host integrity;
- repository, credentials, Docker daemon, and NVIDIA driver boundary;
- correctness of the admitted Source Intent semantics;
- integrity of the emitted kernel and public evidence;
- the existing TUC runtime and native-backend admission gates.

## Untrusted Inputs

- Source Intent and workload JSON bytes;
- JSON duplicate keys, number forms, nesting, sizes, and encodings;
- checked-in generated files and Docker build context;
- Compose-rendered configuration and image inspection metadata;
- worker stdout, stderr, exit status, and runtime device observations;
- repository changes proposed through pull requests.

## Threats And Controls

### Source Becomes Behavior

Threat: source names, attributes, or strings are interpolated into generated
CUDA or executed during validation.

Controls: the emitter consumes plain data only, accepts one canonical payload
digest, invokes typed Source Intent validation, checks explicit ReLU semantics,
uses fixed symbols, performs no dynamic import or evaluation, and has no
subprocess or write path.

### Parser Ambiguity Or Resource Exhaustion

Threat: duplicate keys, non-finite numbers, malformed UTF-8, deep nesting,
large inputs, or file replacement create inconsistent validation.

Controls: strict UTF-8, duplicate-key and non-finite rejection, byte/depth/item
budgets, symlink rejection, before/after size checks, canonical serialization,
and fail-closed diagnostics that do not echo rejected values.

### Generated Artifact Substitution

Threat: reviewed Source Intent is paired with different headers or a different
lowering plan.

Controls: checked-in plan and headers must equal fresh emission byte for byte.
Their payload and file digests are independently bound into build arguments,
OCI labels, image inspection, and the final report.

### Harness Smuggles Additional Kernels

Threat: a manually written kernel bypasses the compiler-emission claim.

Controls: the harness is rejected if it contains `__global__`; the generated
header must contain exactly two definitions with fixed symbols; the Docker
build repeats these checks before compilation.

### Runtime Code Generation Or Target Drift

Threat: PTX JIT, free-form targets, runtime source, or a changed device class
expands execution beyond review.

Controls: the profile fixes `compute_86` and `sm_86`; the image must contain
SASS and no PTX; JIT and CUDA cache are disabled; the worker rejects any device
other than compute capability 8.6; the CLI exposes no target argument.

### Host Or Container Compromise

Threat: GPU execution reaches the network, repository, host filesystem,
privileged APIs, or unbounded resources.

Controls: one logical compute-only GPU, no network or mounts, non-root
UID/GID 10001, read-only root filesystem, all capabilities dropped,
no-new-privileges, seccomp, private IPC, one CPU, 1 GiB memory and swap, 32
PIDs, 16 MiB shared memory, 8 MiB noexec tmpfs, 64 file descriptors, disabled
core dumps, no log driver, bounded output, and a 30 second deadline.

GPU driver access remains a privileged host boundary. The operator must attest
that current vendor security updates are applied and acknowledge shared-device
risk. This experiment is not a sandbox proof against a compromised driver.

### Wrong Result Or Misleading Claim

Threat: a kernel runs but produces incorrect semantics, or evidence is promoted
to general backend or portability claims.

Controls: a separately implemented CPU Matmul-plus-ReLU oracle validates the
public vector before device access and compares finite terminal outputs after
execution. A closed schema fixes all positive and blocked claims. The report
states that `execute_graph()` is unchanged, native backend admission is false,
performance is unmeasured, cross-vendor execution is absent, and independent
reproduction is still missing.

### Evidence Leakage

Threat: public output exposes host identity, source text, generated source,
tensor values, commands, driver details, or hardware identifiers.

Controls: worker and report schemas contain metadata only; outputs are byte
bounded and exact-key validated; serialization tests reject forbidden fields
and host-specific strings.

## Residual Risk

- CUDA compiler, base images, container runtime, NVIDIA Container Toolkit,
  kernel, and GPU driver remain trusted dependencies.
- SHA-256 and image labels prove identity, not benign behavior.
- Same-maintainer execution is not independent reproduction.
- One fixed vector has limited wrong-code detection power.
- Only NVIDIA `sm_86` is exercised by this compiler-emitted proof.

These limits keep arbitrary programs, a general CUDA backend, production
admission, native performance claims, and independent reproduction explicitly
blocked.

## Evidence

- schema:
  `schemas/bounded_compiler_emitted_gpu_observation_report.v0.schema.json`;
- accepted report:
  `tests/golden/proofs/bounded_compiler_emitted_gpu_observation_report.json`;
- tests: `tests/test_bounded_compiler_emitted_gpu_proof.py`;
- decision: `rfcs/0302-bounded-compiler-emitted-gpu-proof.md`.
