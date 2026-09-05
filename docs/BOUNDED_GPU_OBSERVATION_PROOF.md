# Bounded GPU Observation Proof

## Status

Bounded GPU Observation Proof v0 is implemented as a separate opt-in research
path. The container build, static security contract, preflight, and physical
kernel observation are deliberately separate actions. The first checked-in
`PASS` observation was accepted after the local driver-security prerequisite,
no-kernel preflight, shared-display-risk acknowledgement, fixed execution, and
CPU-reference comparison all succeeded.

Decision: `rfcs/0300-bounded-gpu-observation-proof.md`.
Threat model: [Bounded GPU Observation Threat Model](BOUNDED_GPU_OBSERVATION_THREAT_MODEL.md).

## Claim

The proof is intentionally narrow:

> The fixed Objective Delta `2 x 2` `float64`
> `matmul -> elementwise identity` workload can run
> as two precompiled kernels on one physical NVIDIA compute-capability 7.0 GPU
> inside the reviewed container and match its fixed CPU reference.

This is the first TUC research artifact allowed to record
`physical_device_execution = true`. It proves a physical execution bridge for
one neutral workload. It does not prove that the TUC compiler generated CUDA or
that the normal runtime has admitted a native backend.

```text
Objective Delta public audit conformance vector
  -> reviewed fixed workload manifest
  -> deterministic C++ workload header
  -> digest-pinned CUDA 12.8 build
  -> sm_70 SASS-only native probe
  -> one logical physical GPU
  -> matmul kernel -> elementwise identity kernel
  -> fixed CPU reference comparison
  -> sanitized metadata-only evidence
```

## Why This Boundary

The simulator proofs already establish planning, placement, layout conversion,
transfer, allocation, correctness, and backend equivalence. The next useful
question is whether a real device can execute the same bounded compute family
without weakening TUC's default trust model.

The answer is tested outside `execute_graph()`. Existing
[Device Access Sandbox Gate](DEVICE_ACCESS_SANDBOX_GATE.md) and
[Native Backend Execution Security Gate](NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md)
remain unchanged and non-admitting. This proof is a reviewed laboratory
exception, not a policy migration.

## Fixed Workload

The public manifest at
`docker/gpu-observation/objective_delta_workload.v0.json` carries the exact
Objective Delta input and expected output. It is intentionally public and
non-sensitive. Tests require those values to match the installed portable
compute proof and require
`docker/gpu-observation/objective_delta_workload.hpp` to be the deterministic
header rendered from that manifest.

The native binary accepts no tensors or source at runtime. It first recomputes
the expected result on the CPU, then launches exactly:

1. one fixed `2 x 2` `float64` matrix multiplication kernel;
2. one fixed elementwise identity kernel.

Only four 32-byte workload buffers are explicitly allocated. Driver context
memory is outside that 128-byte claim.

## Container Contract

The `gpu-observation` Compose profile replaces the former broad GPU development
shell. It has:

- digest-pinned CUDA 12.8 build and runtime images;
- `sm_70` SASS only and disabled PTX JIT/cache;
- a four-file allowlisted build context;
- no runtime repository mount, Docker socket, network, or shell command;
- one logical GPU and only the `compute` driver capability;
- read-only root filesystem and non-root UID/GID 10001;
- all Linux capabilities dropped, no-new-privileges, seccomp, private IPC;
- bounded CPU, host memory, PID, shared-memory, tmpfs, output, and wall time.

The worker itself checks its effective capabilities, no-new-privileges,
seccomp mode, UID, and GID before its first CUDA call.

## Controlled Procedure

Prerequisites:

- Docker Desktop using the WSL 2 backend;
- a current NVIDIA security-updated driver that still supports the GV100;
- saved desktop work and unnecessary GPU-heavy applications closed.

Build the exact reviewed image. The build may access the registry, but runtime
network access remains disabled:

```powershell
docker compose --profile gpu-observation build --pull gpu-observation
```

Run the no-kernel preflight:

```powershell
py -3 examples/bounded_gpu_observation_proof.py --preflight
```

The preflight calls the CUDA runtime only to confirm one logical `sm_70` device
and the container security state. It emits `proof_status = NOT_EXECUTED` and
`kernel_launch_count = 0`.

Only after reviewing that result, run the fixed kernels:

```powershell
py -3 examples/bounded_gpu_observation_proof.py `
  --execute `
  --attest-current-driver-security-update `
  --acknowledge-shared-display-risk
```

The two explicit flags are part of the security boundary. Omitting either one
fails before Docker or device access.

## Observed Result

The accepted sanitized report is
`tests/golden/proofs/bounded_gpu_observation_report.json`. It records one
visible `nvidia_cuda_sm70` device, two kernel launches, 128 bytes of explicit
workload allocation, physical execution, and a passed CPU-reference check. It
also records that JIT execution, generated code, performance collection,
normal-executor modification, and TUC native-backend admission did not occur.

This closes only the local observation requested by RFC 0300. Independent
reproduction is still `not_yet_supplied`.

## Evidence

- CUDA source:
  `docker/gpu-observation/bounded_gpu_observation.cu`;
- workload manifest and generated header:
  `docker/gpu-observation/objective_delta_workload.v0.json` and
  `docker/gpu-observation/objective_delta_workload.hpp`;
- image recipe: `docker/gpu-observation/Dockerfile`;
- runtime profile: `docker-compose.yml`;
- orchestrator: `examples/bounded_gpu_observation_proof.py`;
- schema: `schemas/bounded_gpu_observation_report.v0.schema.json`;
- accepted physical observation:
  `tests/golden/proofs/bounded_gpu_observation_report.json`;
- tests: `tests/test_bounded_gpu_observation_proof.py`.

An accepted observation binds the workload, Objective Delta files, CUDA source,
generated header, Dockerfile, Compose contract, build/runtime base images,
local execution image, and sanitized worker observation by SHA-256.

## Public Evidence Policy

The final report may expose only the coarse accelerator class
`nvidia_cuda_sm70`, fixed workload metadata, bounded counts, security facts,
claim boundaries, and artifact digests. It does not serialize the GPU model,
UUID, PCI address, serial number, driver version, process list, environment,
host paths, command, raw values, value digests, or timing samples.

The report schema is closed:
`schemas/bounded_gpu_observation_report.v0.schema.json`.

## Non-Claims

This proof does not establish:

- a general CUDA, Triton, or native TUC backend;
- compiler-emitted or runtime-generated GPU code;
- arbitrary shapes, dtypes, inputs, operations, or devices;
- multi-device or heterogeneous physical execution;
- physical equivalence for the systolic/vector simulator placements;
- latency, throughput, utilization, energy, break-even, or native performance;
- container, driver, firmware, or GPU security certification;
- independent reproduction or production device admission;
- replacement of CUDA, ROCm, XLA, MLIR, TVM, IREE, or vendor toolchains.

Any broader native path requires a successor implementation RFC, independent
security review, artifact provenance, resource controls, negative testing, and
an explicit policy decision. Performance remains a separate proof class.
