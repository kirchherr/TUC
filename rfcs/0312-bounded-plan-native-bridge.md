# RFC 0312: Bounded Core Plan to Native Dispatch

Status: Implemented and observed on both native targets, 2026-09-15

## Research Question

Can the existing compiler's checked operation assignments drive the RFC 0311
native three-stage chain instead of handwritten sequential dispatch?

The path is restricted inert source -> typed Source Intent -> metadata ->
ComputeGraph -> HAC-IR -> capability planning -> checked snapshot -> static
opcode/buffer table -> explicit native operator. There is no core modification,
plugin discovery, JIT, arbitrary plan interpreter, or general native admission.

## Binding

Two experiment-local capability descriptions accept matmul, elementwise and
reduction. Only one reviewed target is offered in each compilation, so this
does not prove an optimizer chooses between competing native implementations.
The ordinary compiler builds both partition plans and decision reports.
Their HAC-IR text must be identical across targets. HS-IR, assignments and
target dispatch differ. Missing capability coverage or a reference-CPU fallback
is rejected by the bridge, never silently executed as native code.

An exact, closed snapshot includes full HAC-IR, HS-IR, plan and decision dumps,
typed operation edges, assignments, source identity, and the numerical contract.
The dumps are bound as text, not parsed into operations. Lowering derives the
three opcode rows from typed operation edges and ordered core assignments.
Only freshly reconstructed snapshots for the fixed source are accepted.
Caller data is plain JSON: existing 512-item/depth limits, at most 16 KiB per
string, 64 KiB total serialized metadata, and 63-bit integer magnitude.

The target-independent computation is still the exact RFC 0311 nonlinear
function and its separate FP32 order. Kernels, fixtures, numerical oracle,
common harness and every RFC 0311 record stay byte-for-byte unchanged.
This experiment binds a new native program/image to a reused observation
schema, rather than relabeling old executions as plan-driven.

## Native Dispatch Contract

The table contains three steps and five logical buffers. Read-only inputs occupy
slots 0 and 1, terminal output slot 4. C11 binds projection/activation to 2/3;
CUDA binds them to 3/2. Both assignments are fixed, reviewed lowering policies,
not claims about a general allocator. Distinct bindings exercise actual operand
routing while keeping the mathematical program and 2516-byte tensor footprint.

The worker validates the entire table before any generated function/kernel
call or device-buffer allocation. Only three opcodes are accepted, each once.
Checks cover target identity, count, operand indices, initialized inputs,
write-once output slots, fixed shape roles, immutable external inputs, terminal
output and topology. A closed switch calls only the compiled reviewed kernels;
no function address, symbol name, path or executable command comes from data.

Five compile-time fault variants inject unknown opcode, wrong order, input
overwrite, missing step or wrong target. Each must emit a rejected observation
with zero generated calls and zero reported tensor bytes. C11 static storage
exists regardless of execution; the byte field is not process RSS. The original
seven numerical/coverage controls must also fail. Poisoning, synchronization,
replay, explicit FP32 policy and C11 ASan/UBSan remain mandatory.

## Deliberate Boundaries

The ordinary runtime registry has no trusted executor for either experiment
backend and continues to reject them. `execute_graph()` is unchanged.
Native execution is only through the separate operator procedure.

The current core partition plan models inter-operation movement, not input
upload and terminal download. These two input copies and one output copy remain
explicit operator responsibilities; no zero end-to-end transfer cost is claimed.
GPU memory is `UNKNOWN` in this experiment's capability/plan because the existing
enum has no neutral device-DRAM category. An RTX 3060 is not described as HBM.
No transfer-cost, physical-memory-class or mixed native placement proof follows.

## Security Exception and Provenance

This dedicated native exception follows the proof artifact review policy and
inherits RFC 0311's threat model: trusted repository-owned code and pinned tool
chains, untrusted snapshot/observation metadata, and a host-driver attack surface.
Native workers consume compiled static tables, not external serialized plans.
No new native parser/deserializer is introduced. Malformed metadata is tested
before lowering, and native schedule faults run in bounded containers.

Build contexts deny all except explicitly needed files. Images and Actions remain
digest/SHA-pinned, builds and workers networkless, root read-only, UID/GID 10001,
capabilities dropped, no-new-privileges, default seccomp, no host mounts, private
IPC, one CPU, 32 PIDs, 1 GiB memory/swap ceiling, 8 MiB noexec tmpfs, 64 file
descriptors, no core files or container logs. Alarm 15 seconds, operator timeout
30 seconds, build timeout 600 seconds. CUDA is sm86 SASS-only, one reviewed idle
GPU, no PTX JIT. Timeout/RAM constraints do not isolate GPU faults or limit VRAM.

New records bind the old numerical program digest, new program files, operator
image ID, exact core snapshot, shared HAC-IR and target dispatch header. The
source commit and archive hash must be recorded before observations are accepted.
Public observations omit tensor values, hardware IDs, paths, commands and timing.
These are same-maintainer assertions, not remotely attested execution receipts.

## Acceptance

Both real C11 and CUDA targets must pass the unchanged ten cases plus replay,
363 scalar checks and 33 generated calls each. All twelve negative controls must
reject, including five schedule controls before generated calls. C11 sanitizers
and CUDA SASS policy checks must pass. Existing proofs must remain reproducible.
Independent reproduction, general plan execution, native runtime admission,
cross-vendor execution, dynamic inputs/shapes and performance remain unproven.
