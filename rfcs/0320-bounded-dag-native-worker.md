# RFC 0320: Shared Native Worker for Bounded DAG Artifacts

Status: implementation candidate; physical execution not accepted.

## Decision

Exercise RFC 0319's reusable compiler through one shared native event worker.
Twelve fixed family/shape graphs each have all-CPU, all-GPU and alternating
GPU/CPU placement. Kernel source is identical across placements; only compiled
plan tables differ. A single CUDA image contains all 36 profiles, including
its CPU baseline. No graph-family logic enters the worker or kernel emitter.

`examples/bounded_dag_native.py` reconstructs and validates every compiler
bundle, generates integer descriptors, per-graph symbol wrappers and dispatch,
and binds compiler, oracle, generator, workflow and isolation-script sources.
The default command only emits a candidate. `--emit` creates a private context;
`--accept DIR --worker c11|matrix` revalidates that entire context and the exact
required receipts. Python never starts a process or loads device code.

## Native boundary

The worker accepts only a canonical decimal selector 0-35 and `--preflight` or
`--execute`. C11 accepts only the twelve all-CPU selectors. No runtime graph,
plan file, tensor data, shape, source text, plugin or compiler is accepted.
All descriptors, pointer tables and input/oracle bits are compiled constants.
The only runtime file read is the fixed `/proc/self/status` security check.

Before CUDA initialization or allocation, the validator checks tensor shapes,
operation arity, SSA, launch dimensions, exact operand identities, target spaces,
unique immutable tensor/space slots, schedule order, ready operands, fresh writes,
single input binding, identity-preserving copies and complete terminal outputs.
An independent semantic pass is followed by fieldwise comparison against the
immutable approved graph and plan. Valid alternative plans are not automatically
authorized. Unused fixed-array entries are bound too; padding bytes are ignored.

The worker owns a distinct allocation for every slot and always cleans up owned
storage on error. Every corpus replay resets readiness and poisons storage.
Copies and kernels synchronize before outputs become ready. CUDA launch glue
uses the manifest's exact 128-thread one-dimensional geometry. CPU and CUDA
primitives are the unmodified RFC 0319 sources, compiled with no contraction or
fast math, round-to-nearest, no flushing and sm86 SASS-only device code.

The independent fixed-family oracle establishes finite normal-or-zero rounded
intermediates for this corpus. The wrapper checks FE_TONEAREST and x86 MXCSR
rounding/FTZ/DAZ, input/oracle bit domains and each primitive's completed output.
GPU output-domain validation uses separate, bounded host downloads. Their
counters must never be conflated with compiler-planned tensor transfers.
Terminal comparison is exact binary32 except numerically equal signed zeros.
This does not establish an arbitrary-input numerical domain or error budget.

## Fixed workload and resource limits

There are at most 10 tensors, 7 operations, 16 slots, 18 events, 7,432 planned
buffer bytes and 2,656 planned copy bytes per profile. Three input vectors and
two replays produce these expected totals across 36 profiles:

| Counter | Expected total |
| --- | ---: |
| Case runs | 216 |
| CPU / GPU calls | 468 / 504 |
| Terminal scalar comparisons | 4,212 |
| Publications | 324 |
| Planned upload / download bytes | 67,872 / 26,280 |
| Validation-only download calls / bytes | 504 / 95,400 |

These values are synthetic protocol expectations until actual operator receipts
have passed acceptance. A candidate retains `native_execution_observed=false`.

Each container runs as UID/GID 10001, read-only, with no host mounts, network,
capabilities, privilege escalation or relaxed seccomp. Limits are one CPU,
1 GiB memory/no extra swap, 32 PIDs, 64 descriptors, no core dumps, bounded output,
8 MiB noexec tmpfs and private IPC. Each worker has a 20-second alarm and
30-second outer deadline. Builds use pinned inherited GCC/CUDA image digests,
offline build steps and a 600-second timeout. The context is allowlisted and
limited to 4 MiB; individual text files/aggregate records to 256 KiB and receipts
to 4 KiB. Receipt JSON rejects excessive nesting/items, duplicate keys,
nonfinite values, extra fields, type substitutions and counter drift.

CUDA exposes only device zero with compute capability 8.6, disables PTX JIT and
cache, and verifies the built image contains sm86 machine code and no PTX.
GPU access still shares the host driver/kernel; this is a bounded research
exception, not an isolation mechanism for hostile GPU programs.

## Controls and CPU-only CI exception

Four compile-time fault variants skip the first operation, corrupt the first
published value, omit its publication, or skip the first required copy. The
copy fault applies only to GPU/mixed profiles. Exact failure reasons and the
observed partial counters are required; exit 1 is reserved for those expected
failures. Invocation, environment, allocation, device and cleanup errors exit 2.
Unknown selectors/modes must reject before any compute or CUDA initialization.

The separate `bounded-dag-native-proof.yml` workflow may build and execute the
twelve fixed C11 profiles and their controls, static and under ASan/UBSan. It
also runs all 36 plan baselines and 194,688 single-bit mutations of approved
integer plan fields through the native validator under sanitizers. This tests
rejection against the approved descriptors, not a claim that every mutated
generic graph would be semantically invalid. Graph corruption and forged
expected-plan controls supplement the sweep.

CPU acceptance requires 125 bounded JSON files; matrix acceptance requires 206.
Every baseline/preflight/control must be present, the full source context must
match reconstruction, and image IDs must be well-formed. The records are
same-maintainer execution metadata, not signatures or independent provenance.
CPU CI uses commit-pinned actions, a read-only token, no stored credentials and
the existing hash-pinned dependencies. It neither exposes a GPU nor performs a
remote-host connection. Older workflows, programs and evidence remain intact.

## Physical-run gate and remaining work

Before any new dev001 connection or transfer, prepare the exact committed source
and archive digest, complete source/security review and obtain fresh explicit
user authorization for this payload and run scope. Check current NVIDIA driver
and Container Toolkit advisories and the actual host baseline before execution.
Earlier fixed fan-in/fanout approvals do not authorize this different payload.
Never relax host protections to make a failed check pass.

Physical acceptance requires all 36 same-image profiles and 132 exact fault
rejections, plus both invalid invocations, bound to the approved source and
image. Preserve actual metadata separately from synthetic expectations.
General runtime admission, dynamic shapes, new vendors/ISAs, concurrent
scheduling, performance and independent reproduction remain outside this RFC.
