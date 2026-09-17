# RFC 0318: Bounded Native Fan-In Workers

Status: Bounded C11 and six-profile native validation accepted, 2026-09-17

## Scope

Implement the fixed RFC 0317 candidate without changing its source, numerical
contract, corpus, six placement plans or candidate fixtures. C11 admits cccc;
one CUDA sm86 image admits cccc, gccc, cgcc, gcgg, cggg and gggg. All preserve
the same HAC-IR. There is no extension of the ordinary runtime or backend API.
The producers are independent in dataflow, but execution is sequential and
blocking. This is not a concurrency or performance experiment.

The worker emits separate 231-element left and 35-element right ReLU kernels,
then uses the reviewed 33x7x5 Matmul and axis-1 Sum primitive lowering. Each
profile binds the unchanged candidate plan digest. Its candidate plan still
says native_execution_observed=false: a plan is never an execution receipt.

## Trust Boundaries

The Python verifier parses repository-owned source as data, validates its exact
intent digest before lowering, and reconstructs bounded artifacts byte-for-byte.
It never launches a process, loads a library, discovers plugins or accesses a
device. The default CLI only verifies. --accept reads bounded JSON metadata,
requires preflight, execution, all applicable faults and C11 sanitizer reports,
and binds the program files and operator image ID. Synthetic expected values
are protocol tests, not native evidence. JSON receipts remain same-maintainer
claims rather than cryptographic attestation or independent reproduction.

Only the separate operator script builds/runs containers. Native inputs, plans,
shapes, opcodes and corpus are compiled constants; argv selects an exact profile
and preflight/execute mode only. There is no native plan parser, JIT, external
tensor input, plugin, dynamic source import, host mount or network in a worker.
The contract sanitizer mutates compiled metadata fields in bounded local arrays;
it does not treat pointers or strings as untrusted serialized input.

## Native Invariants

Validate the entire schedule before allocation or compute. Require four ordered
operations, six fixed tensor identities, exact bytes/spaces/placement mask,
single-assignment slots, distinct typed join operands and one final publication.
Each input must be bound once; both producers must complete before the join.
A raw input is not its produced operand, even when their byte sizes match.
Copies preserve identity/size and cross address spaces. All reads require
availability, all writes create a fresh slot, and every buffer must be accounted
for. The independent native validator checks these invariants in addition to
the pure canonical-plan comparison; it is not a general runtime scheduler.

Runtime availability resets every corpus run. Non-input buffers are poisoned
with NaNs, owned buffers are freed on failures, and GPU copies/kernels synchronize
before an operand becomes available. Host output storage is exactly 33 floats.
Left/right producer, operand-copy, join, publication and transfer counters must
match the derived plan. The first corpus case is repeated after nine other
cases; 363 scalar comparisons and 265 rounding witnesses are expected/profile.

## Fault Controls

Ten static faults cover counts, slots, space, order, size, duplicates, placement
and three wrong join-operand combinations. Each must reject before allocation.
Eight numeric faults cover bypass-left/right/both, missing join, incomplete
left/right coverage, over-budget output and nonfinite output. Seven runtime
faults cover skipped producers, invalidated/clobbered left/right operands and
missing publication. Four mixed profiles additionally omit their required
produced-operand copy, covering left/right inputs at CPU/GPU joins.

The operator requires exit status 1 and exact failure metadata, not merely a
nonzero exit. Unknown selectors reject without calls. C11 runs the baseline
under ASan/UBSan and a bounded exhaustive single-bit mutation sweep of all six
plans' integer fields. Required sanitizer success cannot be replaced by a
preflight. Wrong-code controls are compile-time variants, never runtime input.

## Resource and Supply-Chain Budget

- At most 9 slots, 10 events and 4768 logical buffer bytes per profile.
- Ten fixed cases plus one replay; four function calls and 33 outputs/run.
- Bounded 64 KiB artifact/observation files and inherited metadata limits.
- Each worker: 15-second internal alarm, 30-second outer timeout, 1 CPU,
  1 GiB memory/no extra swap, 32 PIDs, 64 descriptors, disabled core dumps.
- Read-only filesystem, UID/GID 10001, no capabilities, no-new-privileges,
  default seccomp, private IPC, 16 MiB shm and 8 MiB noexec temporary storage.
- Docker builds have 600-second timeouts, digest-pinned inherited images and
  frontend, explicit allowlisted context and no network in build commands.
- CUDA exposes only device 0/compute capability, sm86 SASS only; PTX JIT/cache
  disabled, no fast math, reassociation or FMA contraction. Host and device
  dispatch use the same frozen arithmetic kernels and corpus.
- CI uses pinned checkout/setup actions, read-only token, no stored checkout
  credentials, hashlocked dependencies, hosted Ubuntu and CPU-only execution.

GPU containers still share the host kernel/driver. Before a new dev001 transfer
or run, bind the exact source commit/archive, obtain fresh explicit approval,
review current driver/toolkit advisories and confirm isolation/baseline. The
prior fanout authorization does not cover this payload. No host security setting
may be weakened to make sanitizer or device execution pass.

## Acceptance Gate

Require successful C11 sanitizer/fault controls and all six same-image physical
profiles, then review metadata-only records under PROOF_ARTIFACT_REVIEW.md.
All fanout/older evidence and RFC 0317 fixtures remain unchanged. General native
admission, arbitrary
sources/inputs, dynamic shapes, independent reproduction and performance remain
blocked. Execution/acceptance is tracked separately from implementation.

## Observed Acceptance

The approved source commit `4d996e68f1fb9630f3c9bef9e5be67b683120209` passed
the exact operator on dev001 after archive/program binding and a fresh NVIDIA
advisory/isolation review. C11 and six same-image profiles pass; the matrix
completes 2178 scalar checks, 1590 rounding witnesses and 132 CPU/132 GPU calls.
All 179 targeted faults plus two invalid selectors reject with exact receipts.
C11 ASan/UBSan and 16032 contract-field bitflip rejection probes pass.

Actual receipts are retained in 37 new bounded metadata-only proof files.
The separate `examples/bounded_native_fanin_equivalence.py` validates record
bindings without modifying the executed worker. Full controls are revalidated
by the evidence tests. See [the evidence and provenance report](../docs/BOUNDED_NATIVE_FANIN.md)
for source/archive/image digests, observed environment, advisory scope and limits.
This is same-maintainer evidence, not independent reproduction, cryptographic
attestation, parallel scheduling or performance evidence.
