# Bounded GPU Observation Threat Model

## Scope

This threat model covers only Bounded GPU Observation Proof v0. The proof runs
one reviewed, precompiled CUDA program for one public `2 x 2` Objective Delta
workload in a dedicated OCI container.

It does not cover arbitrary CUDA, compiler-emitted code, Triton JIT, external
backend packages, plugins, user tensors, benchmark workloads, or the normal TUC
executor. The report schema is
`schemas/bounded_gpu_observation_report.v0.schema.json`.

## Trust Boundary

The trusted computing base is deliberately explicit:

- the reviewed CUDA source and generated workload header in
  `docker/gpu-observation/`;
- the fixed public workload manifest bound into that image;
- the digest-pinned NVIDIA CUDA build and runtime images;
- Docker Desktop, its WSL 2 kernel path, and the local Docker daemon;
- the installed NVIDIA display driver and container GPU mediation;
- the fixed Python orchestrator in
  `examples/bounded_gpu_observation_proof.py`;
- the local operator's driver-security and shared-display-risk attestations.

The Docker daemon, WSL kernel, NVIDIA driver, firmware, and physical GPU are not
sandboxed from one another by TUC. A container reduces process privileges and
host exposure, but it does not turn the kernel or device driver into an
untrusted component.

## Assets

- host and WSL kernel integrity;
- NVIDIA driver and GPU availability;
- other desktop processes sharing the display GPU;
- repository contents and developer credentials;
- correctness of the fixed workload and CPU reference;
- integrity and privacy of the public evidence report.

## Threats

1. Arbitrary source or command injection expands a fixed probe into a native
   code execution service.
2. A mutable or substituted base image changes the compiler or runtime after
   review.
3. A stale local image executes code that no longer matches reviewed source.
4. Broad GPU exposure reveals additional devices or driver capabilities.
5. Repository mounts, Docker socket access, network access, or root privileges
   turn the container into a host pivot.
6. Oversized allocation, launch geometry, loops, or output exhaust host, device,
   or log resources.
7. A malformed result, NaN, CUDA failure, or partial launch is mistaken for a
   successful semantic proof.
8. Driver diagnostics, device UUIDs, PCI identifiers, process lists, paths,
   environment values, or tensor values leak into public evidence.
9. A long-running or faulty kernel resets the WDDM display driver and disrupts
   applications using the same GV100.
10. A vulnerable host driver permits impact outside the container boundary.
11. A successful fixed probe is overstated as a general native backend,
    portable-hardware proof, or performance result.

## Controls

### Fixed Executable Surface

- The binary accepts only `--preflight` or `--execute`.
- It reads no source, tensor, path, plugin, network, or environment input.
- The workload is one public `float64` `matmul -> elementwise identity` graph with shape
  `2 x 2`.
- The execute path launches exactly two one-block, 32-thread kernels.
- It requests exactly four 32-byte workload buffers, for 128 bytes total.
- A built-in CPU implementation checks the reviewed expected result before the
  GPU runs; the returned GPU result must be finite and match at `1e-12`.
- CUDA failures map to a closed reason-code enum. Raw driver text is discarded.

### Build And Provenance

- Both CUDA images are pinned by Linux `amd64` manifest digest.
- The build context allowlists only the Dockerfile, CUDA source, generated
  header, and fixed workload manifest.
- Build arguments bind SHA-256 digests for source, header, and workload; the
  image repeats those bindings as OCI labels.
- The header is deterministically rendered from the manifest and tested against
  Objective Delta's independent public conformance vector.
- `nvcc` emits only `sm_70` SASS. PTX JIT is disabled in the runtime.
- The runtime image contains no compiler installation step and uses a fixed
  binary entrypoint.

### Runtime Isolation

- one logical NVIDIA device, device `0`, is requested;
- only the NVIDIA `compute` driver capability is exposed;
- the container has no network namespace route, repository mount, Docker
  socket, host path, or additional volume;
- the root filesystem is read-only;
- UID/GID `10001:10001`, all Linux capabilities dropped, no-new-privileges,
  Docker's seccomp filter, private IPC, 16 PID limit, one CPU, 1 GiB host-memory
  limit, and a small `noexec,nosuid,nodev` tmpfs are required;
- the binary observes UID, GID, effective capabilities, no-new-privileges, and
  seccomp state before calling CUDA;
- Compose configuration and image metadata are independently validated before
  the container starts.

### Operator Gate

`--execute` is rejected before Docker access unless the operator explicitly
attests that a current vendor security update supporting the device is
installed and acknowledges that the GPU is shared with the desktop. The
operator must save work and stop unnecessary GPU applications before launch.

### Evidence Boundary

The public report contains a coarse `nvidia_cuda_sm70` class, fixed workload
facts, security booleans, and provenance digests. It excludes device model,
UUID, serial number, PCI address, driver version, process list, environment,
host paths, command lines, tensor values, tensor-value digests, and timing
samples.

## Fail-Closed Conditions

Execution does not count as evidence if any of these occur:

- the image or Compose contract differs from the reviewed contract;
- source, header, workload, Objective Delta, or OCI label digests drift;
- more or fewer than one logical device is visible;
- the device is not compute capability 7.0;
- the container security observations differ;
- an allocation, transfer, launch, synchronization, or result check fails;
- stdout, diagnostics, execution time, or report size exceeds its bound;
- either operator acknowledgement is absent.

## Residual Risk

- NVIDIA GPU access necessarily expands the driver attack surface beyond a
  CPU-only container.
- Docker resource limits do not enforce a hard VRAM quota. The fixed reviewed
  source limits explicit workload allocation, while the CUDA context may use
  additional driver-managed memory.
- A host-side timeout can terminate the container process but cannot guarantee
  immediate cancellation of a wedged device kernel.
- A WDDM reset can interrupt other applications using the display GPU.
- The driver-security statement is operator-attested, not independently
  attested or remotely verified.
- Native C++/CUDA remains memory-unsafe. This v0 program has no parser or
  attacker-controlled input; any input expansion requires a new RFC, native
  sanitizer/Compute Sanitizer evidence, fuzzing where parsing is introduced,
  and independent security review.
- A compromised Docker daemon, WSL kernel, NVIDIA driver, base-image publisher,
  firmware, or GPU is outside this proof.

These residual risks make the proof suitable for a controlled local research
observation, not production device admission.

## References

- [Docker Desktop GPU support](https://docs.docker.com/desktop/features/gpu/)
- [Docker Engine security](https://docs.docker.com/engine/security/)
- [NVIDIA container driver capabilities](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html)
- [NVIDIA legacy CUDA GPU compute capabilities](https://developer.nvidia.com/cuda/gpus/legacy)
