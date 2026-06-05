# RFC 0015: HAC-IR Dialect Contracts

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds explicit HAC-IR v0 dialect contracts in Python before native MLIR
dialect implementation begins.

The new contract records:

- MVP operation names and future `tuc_hac.*` spellings.
- Operation arity bounds.
- A total tensor budget per operation.
- Required compiler-produced movement and semantic attributes.
- Optional compiler attributes.
- Security validation rules for namespaced `tuc.*` attributes.

## Motivation

The MLIR design spike made the future syntax visible, but syntax alone is not a
safe compiler boundary. TUC needs a small executable contract that can validate
the current HAC-IR objects before lowering and also serve as the source of truth
for future MLIR ODS/TableGen work.

## Decision

Add `tuc.ir.dialect` with:

- `HAC_IR_DIALECT_VERSION`
- `HAC_IR_MLIR_DIALECT`
- `HAC_ATTRIBUTE_CONTRACTS`
- `HAC_OPERATION_CONTRACTS`
- `validate_hac_operation_contract`
- `validate_hac_module_contract`

The compiler pipeline validates HAC-IR after TLIR lowering and again before
HAC-IR to HS-IR lowering.

## Security Model

The validator is pure data validation. It does not read paths, import modules,
spawn subprocesses, load dynamic libraries, discover plugins, or call backends.

Unknown `tuc.*` attributes fail closed. This blocks early accidental expansion
of the compiler-reserved namespace and prevents HS-IR/backend metadata from
appearing before the proper stage.

Known non-namespaced user hints remain allowed but are type-checked when they
are security-relevant.

## Consequences

- HAC-IR now has a reviewable v0 operation and attribute contract.
- Native MLIR work has a concrete target without adding native attack surface.
- Wrong-stage metadata is caught earlier.
- Future backend authors can see the compiler facts they may rely on.

## Alternatives Considered

1. Move directly to native MLIR ODS/TableGen.

   Rejected for now because native parser and pass infrastructure should wait
   for fuzzing, sanitizer gates, and a tighter native-code threat model.

2. Keep the contract only in prose.

   Rejected because prose-only contracts drift quickly and cannot protect the
   lowering boundary.

## Follow-Up

1. Generate or cross-check MLIR ODS fragments from these contracts.
2. Add HS-IR-specific contracts for backend assignments and produced layouts.
3. Add backend API v0.1 documentation that references HAC-IR contract fields.
4. Add native fuzzing and sanitizer CI before accepting external MLIR text.
