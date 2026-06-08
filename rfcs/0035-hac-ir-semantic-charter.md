# RFC 0035: HAC-IR Semantic Charter

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Beta

## Summary

TUC adds a HAC-IR semantic charter.

The charter separates HAC-IR data into:

- Compute intent.
- Compiler facts.
- Planning constraints.
- Forbidden backend details.

## Motivation

TUC's central claim depends on HAC-IR being a real hardware-independent
interface. The existing dialect contract and neutrality checklist protect the
current attribute set, but maintainers also need a semantic rule for deciding
where future facts belong.

Without that rule, HAC-IR could slowly absorb backend assignments, vendor
architecture details, runtime handles, calibration artifacts, benchmark claims,
or generated artifact references. That would weaken the Universal Compute
claim and make future backends depend on TUC core semantics that should remain
neutral.

## Decision

Add `docs/HAC_IR_SEMANTIC_CHARTER.md`.

The charter states:

- Compute intent captures operation and tensor meaning.
- Compiler facts are deterministic facts produced by validated compiler passes.
- Planning constraints guide runtime placement without choosing a backend in
  HAC-IR.
- Backend-specific implementation, placement, artifact, calibration,
  benchmark, and certification details stay outside HAC-IR.

Add tests that assert the charter covers the current HAC-IR attributes, the
four semantic categories, forbidden backend surfaces, and the review questions
maintainers should use before approving HAC-IR changes.

## Security Model

The charter reinforces existing secure-by-design boundaries:

- HAC-IR values must be validated before lowering.
- HAC-IR facts must be deterministic and bounded.
- HAC-IR must not depend on backend code, device state, environment variables,
  subprocess output, network access, benchmark output, or generated artifacts.
- Backend selection belongs to runtime planning and HS-IR.
- Executable artifacts and calibration evidence require future schemas,
  threat models, resource budgets, and sandboxing rules.

## Consequences

- HAC-IR change review has a semantic decision rule, not only a field list.
- Future native MLIR work has a clearer boundary to preserve.
- Backend capability and runtime planning can evolve without contaminating
  HAC-IR semantics.
- Vendor capture is harder because backend-specific facts have explicit homes
  outside HAC-IR.

## Alternatives Considered

1. Keep only the neutrality checklist.

   Rejected because the checklist says what to review, but not enough about why
   each class of fact belongs or does not belong in HAC-IR.

2. Encode every semantic distinction in Python constants now.

   Rejected because the current slice is a charter for review and future native
   design. The executable contract already enforces the current v0 attributes.

3. Let each backend proposal decide where its facts belong.

   Rejected because HAC-IR neutrality must be protected by TUC core governance,
   not negotiated per backend.

## Follow-Up

1. Expand deterministic HAC-IR golden dumps for the next proof and MVP graphs.
2. Mirror the charter in future native MLIR ODS/TableGen documentation.
3. Add parser and deserializer fuzzing before accepting external HAC-IR text.
