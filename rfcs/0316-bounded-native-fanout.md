# RFC 0316: Bounded Native Fanout

Status: Implemented; native observations accepted 2026-09-17

## Decision

Extend the fixed odd-shape source to a branched graph: Matmul produces one
immutable projection consumed by ReLU and a direct axis-1 Sum. A second Sum
consumes ReLU. Publish both raw and positive row sums in that order. Existing
source intake, typed overrides and core residency planning remain unchanged.

Admit only three fixed placements: cccc, gccc, gggg (Matmul, ReLU, raw Sum,
positive Sum). One matrix image contains all three schedules; a separate C11
baseline remains mandatory. This is not the complete sixteen-placement matrix.
In gccc the projection is downloaded once and the same host slot feeds two
consumers. Cache reuse means one immutable value in one address space, not
allocator reuse, aliasing, cross-invocation retention or concurrent execution.

## Numeric Contract

The unchanged ten-case corpus uses exact binary32 inputs, 33x7 and 7x5 matrices,
separate ordered multiplication/addition, no FMA/reassociation and finite normal
intermediates. Each branch inherits the gamma_13 absolute-error bound against
its exact rational expression: raw sum or sum after 1-Lipschitz ReLU. A separate
ordered binary32 oracle checks evaluation policy. Both 33-element outputs and
baseline replay are required: 726 scalar checks and 44 calls per placement.
This admits neither arbitrary inputs nor general source/shape lowering.

## Threat Model and Limits

The dedicated native exception inherits RFC 0315's isolation requirements.
Only freshly reconstructed fixed Source Intent and plans lower to static tables.
Unknown profile names, metadata extensions, wrong consumer edges, placements,
duplicate slots, premature publication and output substitution reject. No native
plan parser, code loader, plugin, JIT, caller path, command or device selection.

Native bounds: three profiles, ten slots, twelve events, six logical tensors,
two outputs. Logical bytes per run: 2648 (cccc), 4372 (gccc), 3976 (gggg).
Existing 64 KiB artifact/metadata budgets are unchanged. Static validation
checks the shared input slot and both terminal publications. Runtime availability
resets each invocation and advances only after successful calls/copies.

Workers retain pinned toolchains, deny-default build context, no network/host
mounts, read-only non-root execution, default seccomp, dropped capabilities,
no-new-privileges and bounded CPU/RAM/PIDs/time. Explicit GPU access requires
review of an idle sm86 host. GPU driver risk and incomplete VRAM/device isolation
remain. Source commit and archive digest must be recorded before native runs.

## Acceptance

Require native C11 and all three same-image matrix profiles, exact completion
and copy counters, two consumers per projection and two published outputs.
In gccc require eleven projection copies for twenty-two consumer calls across
the corpus/replay, never one copy per consumer. Require all numerical and static
fault controls, omitted second publication, invalidated shared availability and
clobbered shared contents. Missing copies must fail before dependent work.
C11 ASan/UBSan and all single-bit integer schedule-field mutations must pass.
This deterministic mutation test is not coverage-guided or pointer fuzzing.

CI executes only C11 and revalidates recorded GPU observations. Prior records,
core defaults, numerical policies and ordinary native admission stay unchanged.
No performance, energy, optimal-placement, independent-reproduction, hardware
attestation or cross-vendor claim follows from this same-maintainer experiment.

## Result

The static C11 baseline and all three same-image physical matrix profiles pass
726 scalar checks each. The mixed gccc profile completes eleven projection
downloads for twenty-two consumer calls, with both outputs published on every
run. Matrix total: 2178 scalar checks, 77 CPU calls and 55 GPU calls.
All 84 negative controls reject. C11 ASan/UBSan and 8736 native schedule-field
bitflip rejections pass. No observed program file changed during acceptance.

Source/archive provenance, all grouped observations, boundaries and reproduction
commands are in [Bounded Native Fanout](../docs/BOUNDED_NATIVE_FANOUT.md).
A bounded native fan-in join is a possible successor and requires separate
source and numerical-contract review; ordinary native admission remains closed.
