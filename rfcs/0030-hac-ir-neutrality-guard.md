# RFC 0030: HAC-IR Neutrality Guard

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Beta

## Summary

TUC adds an explicit HAC-IR neutrality guard for high-risk hardware-specific
compiler attributes.

The guard keeps HAC-IR focused on hardware-independent compute intent while
rejecting attributes that belong to backend capabilities, HS-IR, runtime
planning, backend lowering, or future sandboxed artifact handling.

## Motivation

The Universal Compute claim depends on HAC-IR being a real neutral interface,
not a place where vendor details are smuggled in under compiler-owned
attribute names.

Unknown reserved `tuc.*` attributes already fail closed. This RFC adds a
reviewable list of likely mistakes so maintainers can distinguish generic
unknown attributes from explicit hardware leakage such as device IDs, launch
configuration, backend binaries, dynamic libraries, plugin entrypoints, or
specialized accelerator placement details.

## Decision

Add `HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES` to `tuc.ir.dialect`.

`validate_hac_module_contract(...)` now rejects these attributes with a
dedicated HAC-IR hardware-leakage diagnostic before generic unknown-attribute
handling.

Add `docs/HAC_IR_NEUTRALITY.md` with reviewer-facing rules for deciding whether
new facts belong in HAC-IR, capabilities, HS-IR, runtime planning, or backend
lowering.

## Security Model

This change is pure data validation:

- It does not import backend modules.
- It does not discover plugins.
- It does not spawn subprocesses.
- It does not load dynamic libraries.
- It does not read device paths.
- It does not execute generated artifacts.

The guard rejects dangerous metadata before lowerings or backend selection can
treat it as a valid compiler fact.

## Consequences

- HAC-IR neutrality becomes an executable invariant.
- Reviewers get a concrete checklist for compiler-boundary changes.
- Vendor, backend, device, plugin, and artifact details remain outside HAC-IR.
- Future backend authors must describe hardware through capability data and
  later-stage contracts rather than by expanding HAC-IR opportunistically.

## Alternatives Considered

1. Rely only on unknown `tuc.*` rejection.

   Rejected because it hides important architecture mistakes behind a generic
   error and gives reviewers no named baseline for common hardware leaks.

2. Allow vendor-prefixed HAC-IR attributes.

   Rejected because vendor-specific fields would weaken the hardware-neutral
   interface and make future backends depend on core TUC semantics.

3. Move all hardware-neutrality rules into prose.

   Rejected because prose cannot protect lowering boundaries.

## Follow-Up

1. Extend positive and negative tests when HAC-IR operation families expand.
2. Mirror these rules in future native MLIR ODS/TableGen contracts.
3. Add parser and deserializer fuzzing before accepting external HAC-IR text.
