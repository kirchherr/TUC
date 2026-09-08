# Bounded Compiler-Emitted GPU Proof

## Status

Accepted under RFC 0302. The reviewed `sm_86` no-kernel preflight, exactly two
compiler-emitted kernel launches, independent CPU-reference comparison, and
sanitized report all passed.

Decision: `rfcs/0302-bounded-compiler-emitted-gpu-proof.md`.

Threat model:
[Bounded Compiler-Emitted GPU Threat Model](BOUNDED_COMPILER_EMITTED_GPU_THREAT_MODEL.md).

## Research Question

The earlier GPU observations used hand-reviewed fixed kernels. This proof asks
one additional question: can accepted hardware-neutral Source Intent produce
the kernels that are physically observed?

```text
accepted bounded Triton-like source
  -> source_intent.v0 plain data
  -> exact digest and semantic validation
  -> deterministic Matmul + ReLU lowering plan
  -> two compiler-emitted CUDA kernels
  -> ahead-of-time SASS-only sm_86 image
  -> zero-kernel preflight
  -> two physical kernel launches
  -> independent CPU-reference comparison
  -> metadata-only evidence
```

The admitted source program has fixed float32 shapes `[4, 8] x [8, 2]`, one
Matmul, and one explicit ReLU. The emitter will reject even another valid
Matmul/ReLU program because this experiment admits one canonical payload, not
a general CUDA backend.

## Compiler Boundary

Run deterministic emission inspection without Docker or GPU access:

```bash
python3 examples/bounded_compiler_emission.py
```

The command prints the metadata-only lowering plan. It does not write files or
execute source. Tests require these checked-in artifacts to equal fresh
emission byte for byte:

- `docker/gpu-observation/compiler_emission_plan.v0.json`;
- `docker/gpu-observation/compiler_emitted_workload.hpp`;
- `docker/gpu-observation/generated_compiler_emitted_sm86_kernels.cuh`.

The separate CUDA harness contains no `__global__` definition. It launches the
two fixed emitted symbols and implements the CPU oracle, device checks,
resource accounting, and sanitized protocol response.

## Controlled Procedure

The build may access only the container registry. The runtime has no network,
host mount, repository mount, shell command, PTX fallback, or JIT path.

Build the digest-pinned image:

```bash
docker compose --profile gpu-compiler-emitted-sm86 \
  build --pull gpu-compiler-emitted-sm86
```

Run the no-kernel preflight:

```bash
python3 examples/bounded_compiler_emitted_gpu_proof.py --preflight
```

Acceptance requires one visible `nvidia_cuda_sm86` device, a passing container
security boundary, `NOT_EXECUTED`, and exactly zero kernel launches.

Only after reviewing preflight may the fixed workload run:

```bash
python3 examples/bounded_compiler_emitted_gpu_proof.py \
  --execute \
  --attest-current-driver-security-update \
  --acknowledge-shared-display-risk
```

Execution allocates exactly 256 bytes for two inputs and two outputs, launches
exactly two kernels, and records PASS only when the float32 output matches the
independent CPU Matmul-plus-ReLU reference within `1e-5`. No timing is
collected.

## Evidence Contract

The closed public schema is
`schemas/bounded_compiler_emitted_gpu_observation_report.v0.schema.json`.
The accepted physical report is stored at
`tests/golden/proofs/bounded_compiler_emitted_gpu_observation_report.json`.

The report binds Source Intent, workload, lowering plan, generated kernel,
harness, Dockerfile, Compose security contract, container image, and worker
observation by SHA-256. It excludes source text, generated source, tensor
values, timings, commands, host paths, driver version, device model, UUID,
serial number, and PCI identity.

## Interpretation

A PASS proves a narrow compiler-to-physical-device feasibility path. It is
stronger than a hand-written GPU probe because the executed kernels are the
byte-verified result of deterministic lowering from admitted Source Intent.

It is not evidence for arbitrary programs, dynamic workloads, a general CUDA
backend, cross-vendor portability, production admission, performance parity,
or independent reproduction. The normal TUC executor and all native execution
gates remain unchanged.
