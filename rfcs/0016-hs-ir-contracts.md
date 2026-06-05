# RFC 0016: HS-IR Contracts

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds explicit HS-IR v0 contracts for backend assignments, produced layouts,
movement summaries, and runtime-transfer summaries.

## Motivation

HAC-IR validation protects the hardware-agnostic lowering boundary. HS-IR needs
the same discipline for hardware-specific decisions so backend selection and
runtime planning remain inspectable and cannot silently drift from the
partition plan.

## Decision

Extend `tuc.ir.dialect` with:

- `HS_IR_DIALECT_VERSION`
- `HS_IR_MLIR_DIALECT`
- `HS_OPERATION_CONTRACTS`
- `validate_hs_operation_contract`
- `validate_hs_module_contract`

The HAC-IR to HS-IR lowering pass now attaches `tuc.produced_layout` in addition
to `tuc.assigned_backend`, sets the module dialect version from the shared
contract constant, and validates HS-IR before returning it.

## Security Model

The HS-IR validator is pure data validation. It does not discover, import, or
execute backend code. It does not read files, spawn subprocesses, load dynamic
libraries, or scan manifests.

The validator rejects:

- Unknown reserved `tuc.*` attributes.
- Backend assignment metadata that does not exactly match operations.
- Operation-level backend assignments that differ from graph metadata.
- Invalid produced layouts.
- Incorrect source-stage metadata.
- Runtime-transfer summaries with inconsistent totals.

## Consequences

- HS-IR is now a reviewable compiler boundary rather than a loose metadata bag.
- Backend choices and produced layouts are visible in deterministic dumps.
- Runtime-transfer metadata is checked before later backend lowering work can
  depend on it.
- Future native `tuc_hs` MLIR work has a concrete Python-level contract.

## Follow-Up

1. Add backend API v0.1 documentation that references HS-IR fields.
2. Add HS-IR contracts for concrete backend artifacts and calibration metadata.
3. Add negative tests for malicious backend capability claims once plugin
   registration exists.
4. Mirror the contract in native MLIR ODS/TableGen only after fuzzing and
   sanitizer gates exist.
