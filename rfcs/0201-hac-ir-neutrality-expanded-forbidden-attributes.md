# RFC 0201: HAC-IR Neutrality Expanded Forbidden Attributes

- Status: accepted-for-prototype
- Created: 2026-06-22
- Phase: Beta

## Summary

TUC expands the executable HAC-IR forbidden-attribute baseline to cover
additional hardware leakage categories that commonly appear when compiler
projects move from synthetic graphs toward performance-oriented backend work.

The new baseline rejects vendor execution units, warp and wavefront sizes,
cache-line details, memory-bank placement, hardware identifiers, runtime
handles, backend artifacts, FPGA bitstreams, vendor libraries, and TPU/NPU/ROCm
or Metal-family target details before they can be interpreted as HAC-IR facts.

## Motivation

The Universal Compute claim depends on HAC-IR staying a hardware-independent
interface. The next practical risk is not only explicit CUDA/HIP fields; it is
performance-shaped metadata that looks generic enough to slip into HAC-IR but
is actually tied to a backend execution model.

Examples include tensor-core selection, warp size, wavefront size, memory-bank
placement, cache-line width, device UUIDs, hardware serials, runtime handles,
and vendor libraries. These facts can matter for performance, but they do not
define the meaning of the workload.

## Decision

Extend `HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES` in `tuc.ir.dialect`.

The expanded list remains a reviewable baseline. Unknown reserved `tuc.*`
attributes still fail closed, so the list is not the only protection. Its job
is to make the highest-risk mistakes explicit and to keep the error diagnostic
architecturally meaningful.

Update the HAC-IR neutrality checklist, semantic charter, and negative tests so
reviewers can see that performance-specific hardware facts belong to backend
capabilities, backend contracts, HS-IR, runtime plans, transfer-cost profiles,
or performance evidence rather than HAC-IR.

## Security Model

This change is validation-only:

- It does not import backend modules.
- It does not discover plugins.
- It does not spawn subprocesses.
- It does not load dynamic libraries.
- It does not read device paths or device identifiers.
- It does not execute generated artifacts.

The fail-closed behavior reduces the chance that hostile or accidental metadata
can influence lowering, runtime planning, or proof artifacts through HAC-IR.

## Consequences

- HAC-IR neutrality is more robust against performance-shaped leakage.
- Future backend authors get a clearer place to put hardware facts.
- Performance work can continue without weakening the hardware-independent
  interface.
- Leaky-abstraction evidence automatically tracks the expanded baseline through
  `checked_forbidden_attributes`.

## Alternatives Considered

1. Rely only on generic unknown `tuc.*` rejection.

   Rejected because it gives reviewers less signal about high-risk hardware
   categories and makes neutrality regressions harder to discuss.

2. Allow performance-specific hints in HAC-IR when they improve native speed.

   Rejected because the project is currently proving a hardware-independent
   interface, not claiming native performance parity.

3. Move these details into a generic `tuc.hardware_hint` field.

   Rejected because a generic escape hatch would become a leaky abstraction and
   weaken the core proof boundary.

## Follow-Up

1. Keep adding forbidden attribute names when new hardware classes reveal
   recurring leakage patterns.
2. Add native MLIR dialect checks when the prototype dialect is mirrored into a
   real MLIR contract.
3. Keep performance and planner-overhead evidence outside HAC-IR while linking
   it to reproducible proof artifacts.
