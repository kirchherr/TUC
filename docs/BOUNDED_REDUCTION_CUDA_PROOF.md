# Bounded Reduction CUDA Proof

RFC 0306 extends the second fixed source case, `sum(A @ B, axis=1)`, from
RFC 0305's C11 target to an explicitly invoked physical NVIDIA sm86 target.
Source Intent, input vector, reduction axis and output shape are unchanged.
The generated implementation uses two SASS-only kernels, each with one block
of 32 threads, and 240 bytes of device tensor allocations. CUDA context and
driver overhead are additional and are not represented by the tensor budget.

## Procedure

Review the current vendor security bulletins, installed driver and Container
Toolkit, device class and shared-device use before running. This is not a
zero-risk sandbox: CUDA can reach the host driver. Do not update drivers or
stop other workloads as part of the procedure. The explicit invocation is:

```bash
PYTHONPATH=.:src python3 examples/bounded_reduction_cuda.py
sh scripts/run_bounded_reduction_cuda_proof.sh --execute-reviewed-gpu
```

The first command only validates deterministic artifacts. The second builds
the pinned reviewed context, requires zero-call preflight, executes two
generated functions, and compares all four results exactly to the same fixed
reference used by C11. A separately structured binary64 oracle checks the
vector; Python also checks the rational reference. Three actually compiled
wrong-code variants must fail with a reference mismatch after two calls.
No dynamic shape, arbitrary source, runtime JIT or free-form target is allowed.

Reports are retained under the printed private temporary directory. The
operator record binds the actual image ID and current program-file digests;
it is not a signature or independent attestation. A fabricated matching JSON
object alone is not evidence of execution. The final aggregate compares two
validated observations of exact agreement with the same reference, not raw
serialized output values. The C11 observation comes from a separate CI run.

## Security Boundary

The normal executor and admission gates are unchanged. The fixed source uses
the existing review-time research parser; this is not a new OCI source-worker
observation. Canonical Source Intent is validated before either emitter runs.
Generated symbols and loop bounds cannot be supplied by the operator.
Pure validators reuse bounded, no-symlink, regular-file JSON input and reject
duplicate keys, nonfinite values, extra fields and boolean/integer confusion.

Builds have no GPU access and build commands are networkless; pinned base
images may be downloaded. Runtime permits one compute-only GPU, no network,
no host mounts, read-only rootfs, UID/GID 10001, no capabilities,
no-new-privileges, default seccomp, private IPC, one CPU, 1 GiB RAM/swap,
32 PIDs, 64 descriptors, disabled core dumps and bounded tmpfs. GPU VRAM is
not limited by Docker's RAM limit. Fixed allocations and kernel bounds are
reviewed; deadlines cannot guarantee recovery from a driver or hardware hang.
No device reset, service restart or container-wide cleanup is performed.

Host drivers, toolkit, Docker, compiler and base images remain trusted.
The GPU path does not claim an ASan/UBSan or Compute Sanitizer run. C11 has its
own sanitizer observation. Wrong-code probes are semantic tests, not a GPU
memory-safety proof. Metadata output omits values, timings and host/device IDs.

## Status And Limits

Accepted as a same-maintainer physical observation on 2026-09-10. The source
snapshot was commit `10d29e01e7d7a7676504c918a4bf9d931edb0495`. Its transmitted
archive SHA-256 was
`3ff58d3583733cc352db03ac8aac1cb898e92f45ac3b47c02416bdb93b5597ee`.
The operator observed zero-call preflight, two generated calls with exact
reference agreement, 240 device tensor bytes and three wrong-code rejections.
The container exited and the GPU returned to its initial idle occupancy.

Accepted artifacts:

- `tests/golden/proofs/bounded_reduction_cuda_record.json`
- `tests/golden/proofs/bounded_reduction_target_equivalence.json`

The record includes the actual Docker image ID and the source-file binding.
It was transferred back and independently revalidated by the local verifier;
this is a second validation location, not an independent maintainer.
The driver and toolkit were checked against the relevant published
[driver bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5821) and
[toolkit bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5850/~/security-bulletin%3A-nvidia-container-toolkit---june-2026).
No host identity, driver version or credentials are part of public evidence.
Hosted CI revalidates recorded GPU evidence; it does not rerun a physical GPU.

One source case and one vector on C11 and NVIDIA do not prove arbitrary
programs, another vendor, performance parity, independent reproduction,
production runtime admission or universal hardware coverage.

Next useful generalization: another input vector or shape under a bounded
reviewed contract, not another general evidence gate.
