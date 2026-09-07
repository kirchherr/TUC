# RFC 0301: Bounded Cross-Architecture GPU Proof

## Status

Accepted as a separate opt-in research implementation after the reviewed
`sm_86` no-kernel preflight, fixed two-kernel observation, and aggregate
cross-architecture evidence all passed. This RFC does not admit a native TUC
backend.

## Context

RFC 0300 proves that one fixed Objective Delta workload can execute as two
precompiled `sm_70` kernels on one physical Volta GPU and match its CPU
reference. That observation is valuable but cannot distinguish a portable
compute boundary from a one-device coincidence.

The next bounded research question is:

> Can the exact same neutral workload and public reference semantics execute
> through separately compiled SASS-only probes on two NVIDIA compute
> architectures without introducing runtime target selection, JIT, or a
> general native backend?

## Decision

Add one reviewed `nvidia-sm86` profile beside the immutable `nvidia-sm70`
profile. Profiles are frozen data selected from a static allowlist. Callers
cannot supply compute capabilities, SASS targets, source paths, image names,
Compose services, protocols, or claim scopes.

The `sm_86` profile has its own CUDA source snapshot, Dockerfile, Compose
service, report schema, image identity, worker protocol, and proof contract.
Tests require its CUDA source to remain semantically identical to the `sm_70`
source except for the reviewed compute capability, accelerator class, and
worker protocol.

The aggregate proof accepts exactly one valid RFC 0300 report and one valid
`sm_86` report. It binds their report and image digests, requires the same
workload metadata and manifest digest, and emits metadata-only evidence.

## Execution Boundary

Both observations retain the RFC 0300 limits:

- one logical device and NVIDIA `compute` capability only;
- no network, host mount, repository mount, Docker socket, or runtime shell;
- read-only root filesystem, non-root UID/GID 10001, all capabilities dropped,
  no-new-privileges, seccomp, and private IPC;
- one CPU, 1 GiB memory, profile-bounded PIDs (`16` for `sm_70`, `32` for
  `sm_86`), bounded tmpfs, bounded output, and a 30 second wall-clock limit;
- exactly two fixed `2 x 2` `float64` kernels and 128 bytes of explicit
  workload allocation;
- SASS for exactly one reviewed architecture, no embedded PTX, disabled JIT
  and cache;
- explicit operator attestation for driver security and shared-GPU risk before
  execution.

The `sm_86` preflight may query device count, compute capability, and process
security state, but launches no kernel. Execution is allowed only after that
preflight returns `NOT_EXECUTED`, zero kernel launches, and a passing security
boundary.

The `sm_86` PID budget is `32` because NVIDIA Container Toolkit 1.20 performs
device injection in a Go-based OCI hook before the worker starts. A diagnostic
preflight proved that `16` prevents that hook from creating its required
threads while `32` succeeds. The worker remains single-process; this is a
bounded runtime compatibility allowance, not workload parallelism.

## Claim Boundary

A successful aggregate establishes only:

> The same fixed neutral Objective Delta workload was observed on one Volta
> `sm_70` device and one Ampere `sm_86` device, and both observations matched
> the same CPU reference under equivalent bounded isolation.

It does not prove arbitrary-program portability, cross-vendor execution,
native performance parity, a production device backend, independent
reproduction, or the universal-compute thesis. Both devices remain NVIDIA
devices and both observations remain under the same maintainer's control.

No device model, host name, UUID, serial, PCI address, driver version, SSH
identity, process list, environment, host path, command, raw tensor value, or
timing sample enters public evidence.

## Evidence

- profile-aware orchestrator: `examples/bounded_gpu_observation_proof.py`;
- aggregate builder: `examples/bounded_cross_architecture_gpu_proof.py`;
- fixed `sm_86` source and image recipe: `docker/gpu-observation/`;
- schemas:
  `schemas/bounded_gpu_sm86_observation_report.v0.schema.json` and
  `schemas/bounded_cross_architecture_gpu_proof.v0.schema.json`;
- accepted physical `sm_86` observation:
  `tests/golden/proofs/bounded_gpu_sm86_observation_report.json`;
- accepted aggregate proof:
  `tests/golden/proofs/bounded_cross_architecture_gpu_proof.json`;
- tests: `tests/test_bounded_gpu_sm86_observation_proof.py` and
  `tests/test_bounded_cross_architecture_gpu_proof.py`;
- procedure: `docs/BOUNDED_CROSS_ARCHITECTURE_GPU_PROOF.md`;
- threat model: `docs/BOUNDED_CROSS_ARCHITECTURE_GPU_THREAT_MODEL.md`.

## Consequences

This is a stronger physical feasibility observation than RFC 0300 because the
compute intent and terminal semantics remain fixed while the compiled target
and physical architecture change. The cost is one intentionally explicit
profile and source snapshot. That duplication preserves the original evidence
and is guarded by a semantic-difference test.

Adding any further target requires a new reviewed profile and evidence. A free
target argument, PTX fallback, generated CUDA, input-bearing kernel, dynamic
library path, performance claim, or connection to `execute_graph()` remains
forbidden without a successor RFC.
