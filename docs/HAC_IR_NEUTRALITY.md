# HAC-IR Neutrality Checklist

HAC-IR is TUC's hardware-independent compute-intent layer. It may describe
what computation means, what movement facts the compiler derived, and what
constraints a planner should respect. It must not describe where code will run
or how a backend will implement it.

Use this checklist for every change that touches HAC-IR operations,
attributes, lowering, dumps, frontend metadata, or dialect contracts.

## Neutrality Rules

HAC-IR may contain:

- Operation family and tensor semantics.
- Compiler-produced movement estimates.
- Abstract layouts and abstract memory-domain preferences.
- Error budgets expressed as intent or constraints.
- Deterministic metadata needed for validation and review.

HAC-IR must not contain:

- Backend assignments.
- Vendor names or target architectures.
- Device identifiers, device paths, runtime handles, streams, queues, or launch
  grids.
- Backend kernel names, backend binaries, generated artifacts, dynamic
  libraries, plugin entrypoints, or executable artifact references.
- Specialized placement details such as a photonic mesh, neuromorphic core,
  CUDA device, HIP target, Metal device, or vendor-specific accelerator knob.

Those details belong to backend capabilities, HS-IR, backend lowering, runtime
planning, or sandboxed artifact handling after a dedicated security RFC.

## Current Executable Guard

The Python v0 contract exposes:

```text
tuc.ir.HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES
```

`validate_hac_module_contract(...)` rejects these attributes with an explicit
HAC-IR hardware-leakage diagnostic. Unknown reserved `tuc.*` attributes also
fail closed, so this list is not the only protection; it is the reviewable
baseline for the most likely mistakes.

## Reviewer Checklist

Before approving a HAC-IR change, verify:

- The change increases hardware independence or protects the neutral boundary.
- Any new `tuc.*` attribute is compiler-produced, deterministic, bounded, and
  documented.
- The attribute does not name a vendor, backend, device, plugin, binary,
  generated artifact, runtime handle, or backend-specific placement target.
- Hardware-specific facts stay in capabilities, HS-IR, runtime plans, or
  backend implementation contracts.
- The validator rejects malformed values before lowering.
- Negative tests cover unknown reserved attributes and any likely
  hardware-specific leakage.
- Dumps remain deterministic and inspectable.
- No new path imports modules, loads dynamic libraries, discovers plugins,
  spawns subprocesses, touches devices, reads caller-selected artifact paths, or
  executes generated code.

## Adding A New HAC-IR Attribute

Every new HAC-IR attribute needs:

1. A contract entry in `tuc.ir.dialect`.
2. A short explanation in `docs/HAC_IR_DIALECT.md`.
3. Positive validation coverage.
4. At least one negative test for malformed values.
5. A clear statement of why the attribute belongs in HAC-IR instead of
   capabilities, HS-IR, runtime planning, or backend lowering.

If an attribute is useful only for one backend family, it does not belong in
HAC-IR.
