# RFC 0315: Bounded Native Placement Matrix

Status: Implementing; native observations pending

## Decision

Extend RFC 0314's fixed three-operation source graph into the complete finite
CPU/GPU placement matrix: ccc, ccg, cgc, cgg, gcc, gcg, ggc, ggg. Positions mean
Matmul, ReLU, axis-1 Sum; c is C11 host execution and g is CUDA execution.
Both backend capabilities advertise all three operations. Existing typed
require_backend overrides select each placement. HAC-IR and arithmetic remain
unchanged; core residency schedules boundary and intermediate copies.

All eight schedules are compiled into one reviewed matrix worker. A bounded
profile enum selects a schedule at invocation; there is no plan parser, source
loader, runtime compiler, plugin, path, command or device selector. All profiles
must be observed using the same image ID. A separate static C11 baseline remains
required. No automatic placement optimization or performance claim is made.

## Invariants and Threat Model

Trust boundaries are the existing typed overrides, fresh snapshot comparison,
static table lowering, native profile enum and metadata-only observation intake.
The previous metadata/file budgets remain unchanged. Profiles have exactly three
letters from a fixed set of eight. Only the known source, shapes, operations,
FP32 contract and corpus are admitted. Unknown/extended profile identifiers
reject before allocation. The C11 worker cannot admit GPU assignments.

The native worker checks selected-profile identity, counts, slots, sizes, tensor
identities, address spaces, write-once availability, operation order and placement
before device discovery/allocation. Maximums are ten slots and eleven events.
Per-run availability resets and advances only after successful work. Missing
copy or publication cannot become success. No buffer reuse or asynchronous work.
The normal runtime still rejects these experiment backends.

The operator retains pinned toolchains, deny-default Docker context, no network
or host mounts in workers, read-only non-root execution, dropped capabilities,
seccomp, no-new-privileges and bounded time/CPU/RAM/PIDs. Device access is explicit
on a reviewed idle sm86 host. GPU driver risk and incomplete GPU isolation/VRAM
limits remain; containers are not a complete GPU security boundary. Source
commit and transferred archive digest are recorded before execution.

## Acceptance

Static C11 and each matrix profile must complete ten cases plus replay with 363
scalar checks and 256 rounding witnesses. Require all eight distinct profiles,
one common matrix image/program, identical HAC-IR/source intent/numerical contract
and exactly planned CPU/GPU calls and copy counters. No substituted, duplicate,
missing or reordered profile may close the matrix. Preserve previous records.

Compile wrong-code controls affecting both host and GPU arithmetic so failures
cannot disappear when placement changes. Check malformed schedules, incorrect
placement, missing publication and missing produced-value copies. Reject an
unknown profile. C11 ASan/UBSan and sanitizer testing of native schedule selection
are required. CI executes only C11 and revalidates recorded GPU observations.

This is same-maintainer fixed-workload correctness evidence, not independent
reproduction, arbitrary programs/inputs, dynamic shapes, general native admission,
vendor portability, hardware attestation, measured speed or optimal placement.
