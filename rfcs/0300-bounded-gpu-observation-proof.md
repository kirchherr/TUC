# RFC 0300: Bounded GPU Observation Proof

## Status

Accepted as a separate opt-in research implementation. It does not admit a
native backend into TUC's normal compiler or runtime. A public `PASS` artifact
requires a successful local preflight and execution under the controls below.

## Context

Objective Delta and Runtime Materialized Heterogeneous Storage establish one
bounded hardware-neutral semantic slice through trusted simulators. They do not
touch a physical device. RFC 0249 and RFC 0251 correctly keep general device
access and native backend execution closed until a concrete implementation
defines sandboxing, provenance, budgets, negative tests, and review.

The next research question is narrower than opening those general surfaces:

> Can one already-proven TUC workload be observed on a physical GPU through a
> fixed, reviewable, isolated experiment without changing the default trust
> boundary?

## Decision

Add Bounded GPU Observation Proof v0 as an external research harness.

The accepted workload is exactly the public Objective Delta `2 x 2` `float64`
`matmul -> elementwise identity` conformance vector. A reviewed CUDA program
performs one matrix multiplication kernel and one identity kernel on a single
logical NVIDIA compute-capability 7.0 device, then compares the finite result
with its fixed CPU reference.

The program is built in a digest-pinned CUDA 12.8 development image for
`sm_70` SASS only and copied into a digest-pinned runtime image. It accepts no
source, tensors, paths, plugins, commands, or environment-derived behavior.

The host orchestrator validates static source bindings, Objective Delta,
rendered Compose configuration, image configuration and provenance labels,
bounded worker output, semantic success, and the public report before emitting
evidence.

## Isolation Decision

The runtime must enforce:

- explicit profile and fixed entrypoint;
- one logical GPU, device `0`;
- NVIDIA `compute` capability only;
- no network, repository mount, host path, Docker socket, or extra volume;
- read-only root filesystem;
- UID/GID 10001, all capabilities dropped, no-new-privileges, seccomp;
- private IPC, one CPU, 1 GiB host memory, 16 PIDs, 16 MiB shared memory, and
  an 8 MiB `noexec,nosuid,nodev` tmpfs;
- fixed two-kernel geometry and 128 bytes of explicit workload allocation;
- 8 KiB stdout/stderr limits, 30 second wall-clock limit, and 64 KiB report
  limit;
- fail-closed CUDA and semantic reason codes without raw driver diagnostics.

The program must observe its process privilege state before its first CUDA
call. The operator must explicitly attest a current vendor security update and
acknowledge shared-display risk before `--execute` can invoke Docker.

## Provenance Decision

- CUDA base images are pinned by Linux `amd64` manifest digest.
- The allowlisted build context contains only Dockerfile, CUDA source, workload
  header, and workload manifest.
- The image binds SHA-256 labels for the CUDA source, generated header, and
  workload manifest.
- The host validates those labels against current repository files.
- The public report binds the local image ID plus all reviewed source and
  planning artifacts by SHA-256.
- PTX is not embedded for runtime fallback; PTX JIT and cache are disabled.

## Evidence Boundary

Schema: `schemas/bounded_gpu_observation_report.v0.schema.json`.

The report records physical device and fixed native probe execution honestly.
It also records that the TUC native backend remains unadmitted, the normal
executor is unchanged, both previous gates remain uninterpreted, performance
was not measured, and broad native/portable/vendor claims remain blocked.

No device model, UUID, serial, PCI address, driver version, process list,
environment, path, command, raw tensor value, tensor-value digest, or timing
sample may enter public evidence.

## Security Analysis

The normative threat model is
`docs/BOUNDED_GPU_OBSERVATION_THREAT_MODEL.md`. It explicitly treats Docker,
WSL 2, the local daemon, NVIDIA driver, firmware, and physical GPU as trusted
dependencies and documents the lack of a hard VRAM quota and the residual WDDM
reset risk.

Because v0 has no attacker-controlled parser or data input, it does not add a
native fuzz target. Any input-bearing successor must add native sanitizer and
fuzz evidence before admission. Broader CUDA execution, JIT, plugins, dynamic
library paths, generated code, or compiler output require a new RFC.

## Evidence

- implementation: `examples/bounded_gpu_observation_proof.py`;
- CUDA source and workload: `docker/gpu-observation/`;
- runtime policy: `docker-compose.yml`;
- schema: `schemas/bounded_gpu_observation_report.v0.schema.json`;
- tests: `tests/test_bounded_gpu_observation_proof.py`;
- documentation: `docs/BOUNDED_GPU_OBSERVATION_PROOF.md`;
- threat model: `docs/BOUNDED_GPU_OBSERVATION_THREAT_MODEL.md`.

## Consequences

TUC gains a credible simulator-to-device bridge without pretending to possess
a production GPU backend. The experiment is small enough to audit and repeat,
while its report can become the first physical-execution evidence in the
roadmap after a controlled local run.

The former broad GPU development Compose service is removed. GPU access now
defaults to the fixed preflight in an explicit profile; kernel execution
requires the separately acknowledged host runner.

Promotion into `execute_graph()`, Runtime Evidence Gate, an installed public
API, CI, release claims, or performance evidence is forbidden without a
successor RFC, external review, independent reproduction, and unchanged
security/privacy controls.
