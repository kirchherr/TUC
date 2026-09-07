# Bounded Cross-Architecture GPU Threat Model

## Scope

This threat model covers the RFC 0301 `nvidia-sm86` observation and the
metadata-only aggregation of that report with the accepted RFC 0300 `sm_70`
observation. It does not cover arbitrary CUDA, TUC-generated native code, or a
production backend.

## Assets

- integrity of both physical observation reports;
- integrity of the fixed Objective Delta workload and CPU oracle;
- the remote Linux host, Docker daemon, NVIDIA driver, firmware, and GPU;
- the maintainer's SSH private key and workstation;
- TUC's default non-device compiler and runtime trust boundaries.

## Inputs And Trust

No runtime workload input is accepted. CUDA source, workload data, image
digests, build arguments, Compose policy, profile identity, and command mode
come from reviewed repository constants.

The host kernel, Docker Engine, NVIDIA Container Toolkit, NVIDIA driver,
firmware, physical GPU, digest-pinned CUDA image contents, and maintainer
attestations are trusted dependencies. Their correctness is not proved by the
report.

The public Git repository and container registry are potentially hostile
transport. Commit review, immutable source digests, pinned base-image manifest
digests, image labels, local image IDs, and fail-closed validation bind the
executed artifact to reviewed inputs.

## Primary Threats

- architecture substitution or PTX fallback broadens executable code;
- Compose drift adds network, mounts, devices, privilege, or writable state;
- a forged image tag points to code unrelated to reviewed sources;
- a compromised or stale driver exposes the host through GPU execution;
- unbounded output, processes, memory, or execution time exhausts the host;
- diagnostics leak host, device, SSH, process, or driver details;
- a second same-maintainer run is mislabeled as independent reproduction;
- aggregation combines different workloads or widened claims.

## Controls

- static trusted profile allowlist; forged profile objects fail closed;
- exact `compute_86 -> sm_86` SASS build and a required empty PTX listing;
- disabled PTX JIT and CUDA cache;
- source snapshot equivalence test against the `sm_70` worker;
- digest-pinned build/runtime images and source-binding image labels;
- one logical GPU with `compute` capability only;
- no network, volume, host path, Docker socket, stdin, shell, or repository
  mount at runtime;
- non-root user, all capabilities dropped, no-new-privileges, seccomp,
  read-only root filesystem, private IPC, and fixed resource limits;
- bounded process output and wall-clock timeout;
- exact worker response keys, values, reason codes, and report schemas;
- metadata-only reports with explicit blocked claims and same-maintainer scope;
- aggregate validation of both source reports and their common workload digest.

## Operator Gates

Before execution, the operator must establish that the installed driver is at
or above the current vendor security update for its branch, inspect the
no-kernel preflight, ensure no conflicting compute workload is active, and
acknowledge possible impact on a shared display GPU. Omitting either execution
attestation stops before Docker is invoked.

SSH is transport only. The private key is never copied to the remote host,
container, report, command output, or repository. Public evidence excludes the
host name and all connection details.

## Residual Risk

Container isolation cannot make a GPU driver bug harmless. Docker and the
NVIDIA runtime expose a kernel/driver attack surface, and the container memory
limit is not a hard VRAM quota. A device or driver fault can still reset a
shared GPU. The fixed workload, tiny allocation, idle-device check, current
driver prerequisite, and short timeout reduce but do not eliminate that risk.

Both observations are controlled by one maintainer and use NVIDIA CUDA. The
aggregate therefore remains supporting feasibility evidence, not independent
replication, cross-vendor evidence, or proof of the full TUC thesis.
