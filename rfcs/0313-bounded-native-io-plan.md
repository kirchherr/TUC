# RFC 0313: Explicit Bounded Native Boundary I/O

Status: Implemented; native C11 and physical sm86 CUDA observations accepted

## Question and Scope

Can the same restricted source and checked compute plan also determine the
native operator's external input/output movement, with completed copies checked
against the plan? This extends RFC 0312 without changing its source, kernels,
FP32 oracle, core snapshot, normal executor, or accepted evidence.

The closed operator plan composes two before-compute input steps, the existing
three compute steps, and one after-compute output step. Tensor names, shapes,
dtypes, byte sizes and terminal status come from the checked HAC-IR graph.
The fixed logical port/slot mapping is still experiment-owned. This is not
general core partitioning, mixed placement, or public-output selection support.

## Address Spaces and Costs

Addressability and physical memory technology are different properties.
The host endpoint is `host_process` / `host_ram`. CUDA's execution endpoint is
`device_global` / `unknown`: it is a separate device address space, but the
core capability does not pretend to know a physical RAM technology. C11's
execution endpoint aliases the host address space. No global memory enum or
versioned schema is widened merely for this experiment.

The CUDA plan contains 924-byte and 140-byte uploads followed by a 132-byte
download: 1196 explicit boundary bytes per run. C11 binds the two caller input
buffers and publishes its caller-owned output buffer, with no explicit boundary
copy. Zero explicit copy bytes is not zero execution latency or zero physical
memory traffic. Both targets leave latency and energy null / not measured.
Initialization, oracle reads, allocation, caches and driver-internal traffic
are not included in this boundary-copy metric. No performance claim follows.

The old core partition plan still covers inter-operation edges only. The new
operator I/O plan is separately bound to its full core snapshot and compute
dispatch. It neither rewrites old transfer estimates nor invents measured costs.

## Execution and Validation

Only freshly reconstructed, bounded plain metadata lowers to static I/O tables.
Limits remain 512 items / existing depth, 16 KiB strings, 64 KiB serialized data,
and 63-bit integers. No external native plan parser, symbols, addresses, code,
JIT, subprocess dispatch or plugin registration are admitted.

The native worker validates compute and I/O tables before GPU discovery or
device-buffer allocation: exact count, phases, slots, full sizes, directions,
address spaces, unique inputs and terminal output. Native pointer sources remain
compiled closed switches/arrays; table values cannot supply a host pointer.

The worker performs uploads before kernels and download after kernels. CUDA
copy counters advance only after successful cudaMemcpy and explicit device
synchronization. Host bindings and completed I/O steps are counted separately.
Explicit synchronization avoids relying on host-return behavior alone; see
[NVIDIA's API synchronization rules](https://docs.nvidia.com/cuda/cuda-runtime-api/api-sync-behavior.html).
Every run requires three completed I/O steps; counters are cumulative over the
ten cases plus replay. Output publication is required even when all kernels ran.

Seven compile-time table controls reject missing steps, wrong direction, wrong
size, wrong slot, early output, duplicate input and truncated output before
generated calls, copies or device-buffer allocation. An eighth control skips
output completion after all kernels and must fail despite three generated calls.
All twelve RFC 0312 controls remain required. Native observations nest the old
numerical observation and add only I/O plan digest and completion counters.
The verifier checks a closed schema, exact numerical contract and exact counts.

## Security and Provenance

This is an explicitly authorized native research exception, not normal-runtime
admission. It retains RFC 0312's pinned toolchains, deny-default Docker context,
networkless builds/workers, read-only root, UID 10001, dropped capabilities,
no-new-privileges, seccomp, no host mounts, bounded RAM/CPU/PIDs/time and sm86
SASS-only CUDA. C11 ASan/UBSan and CUDA SASS/no-PTX checks are required.
The host GPU driver remains an attack surface; container limits neither isolate
all GPU faults nor cap VRAM. Unrelated host workloads must remain untouched.

Record the exact source commit and transferred archive digest before acceptance.
New records bind the operator image, new program files, previous bridge program
and the I/O plan (which binds the old core snapshot). These are same-maintainer
observations, not cryptographic hardware attestation. Do not relabel old records.

## Acceptance

Both real targets must pass the unchanged 363 scalar checks / 33 generated
calls, ten cases plus replay, and twenty negative controls each. C11 must report
33 host bindings and no explicit copies. CUDA must report 22 uploads (11704
bytes) and 11 downloads (1452 bytes). Preflights and invalid table controls must
report no completed I/O. C11 sanitizer execution and all old proofs remain valid.

Accepted on 2026-09-15: both native targets met these conditions, including all
forty compiled negative runs and the C11 sanitizer run. Source commit:
`5136451be9f902fd5f71114bc5de1948e2a0ec01`; transferred archive SHA-256:
`6946cd41218ddadd3048cceeddeb6280a1fb1ab11d1b648244af33064b636593`.
The bound comparison is `tests/golden/proofs/native_io_comparison.json`.
See [the experiment report](../docs/BOUNDED_NATIVE_IO_PLAN.md) for counts and
record links. Accepted observations do not claim independent reproduction.

Independent reproduction, general/native admission, arbitrary inputs/shapes,
mixed native placement and performance remain unproven. A next larger question
is shared core planning of boundary residency and mixed native placements;
this experiment establishes an executable boundary contract first.
