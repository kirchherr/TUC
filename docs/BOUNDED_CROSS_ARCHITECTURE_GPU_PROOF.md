# Bounded Cross-Architecture GPU Proof

## Status

The `sm_86` implementation and closed execution protocol are ready for an
explicit physical observation. RFC 0301 remains proposed until the preflight,
execution, sanitized report, and aggregate proof all pass.

Decision: `rfcs/0301-bounded-cross-architecture-gpu-proof.md`.
Threat model:
[Bounded Cross-Architecture GPU Threat Model](BOUNDED_CROSS_ARCHITECTURE_GPU_THREAT_MODEL.md).

## Research Question

RFC 0300 observed the fixed Objective Delta workload on Volta `sm_70`. This
proof changes exactly one relevant dimension: the physical and compiled CUDA
architecture becomes Ampere `sm_86`.

```text
same fixed Source Intent and Objective Delta vector
  -> same 2 x 2 float64 matmul -> elementwise semantics
  -> reviewed sm_70 SASS-only observation
  -> reviewed sm_86 SASS-only observation
  -> both match the same CPU reference
  -> metadata-only cross-architecture evidence
```

This is evidence for a bounded portability mechanism, not a claim that TUC has
proved universal hardware independence.

## Static Profile Boundary

`examples/bounded_gpu_observation_proof.py` exposes only two reviewed profile
IDs: `nvidia-sm70` and `nvidia-sm86`. A profile fixes the CUDA source,
Dockerfile, image, Compose service, protocol, schema, accelerator class, and
SASS target. There is no free-form architecture option.

The `sm_86` worker is an explicit snapshot. Tests normalize its reviewed
target-identity substitutions and require the remaining source to equal the
`sm_70` worker byte for byte.

The `sm_86` container allows at most 32 PIDs. The NVIDIA Container Toolkit 1.20
OCI hook needs more than the RFC 0300 limit of 16 threads during device
injection, before the worker starts. The workload itself remains one bounded
process. All other runtime limits remain equivalent to the `sm_70` profile.

## Controlled Procedure

The image build may access the container registry. The resulting runtime has
no network access and receives no repository or host mount.

Build the digest-pinned image:

```bash
docker compose --profile gpu-observation-sm86 build --pull gpu-observation-sm86
```

Run the no-kernel preflight:

```bash
python3 examples/bounded_gpu_observation_proof.py \
  --profile nvidia-sm86 \
  --preflight
```

The accepted preflight must report `NOT_EXECUTED`, exactly one visible
`nvidia_cuda_sm86` device, zero kernel launches, and a passing process-security
boundary.

Only after reviewing that result, run the fixed workload:

```bash
python3 examples/bounded_gpu_observation_proof.py \
  --profile nvidia-sm86 \
  --execute \
  --attest-current-driver-security-update \
  --acknowledge-shared-display-risk
```

The report is accepted only if two fixed kernels execute, all four 32-byte
buffers are released, and the result matches the CPU reference. Timing is not
measured.

After both physical reports are present, build the aggregate:

```bash
python3 -m examples.bounded_cross_architecture_gpu_proof
```

## Interpretation

A `PASS` means the same fixed compute intent retained its observable result on
two NVIDIA architecture classes through two separately precompiled probes. It
does not establish independent reproduction because both hosts are controlled
by the same maintainer. It also does not establish cross-vendor portability,
arbitrary-program support, compiler-emitted CUDA, performance parity, or
production backend admission.

The normal TUC compiler pipeline, Runtime Evidence Gate, Device Access Sandbox
Gate, and Native Backend Execution Security Gate remain unchanged.
