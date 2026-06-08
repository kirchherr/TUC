# RFC 0034: Capability Schema Negative Examples

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Gamma

## Summary

TUC adds documented and tested negative examples for invalid or misleading
backend capability claims.

The examples clarify that backend capability manifests must describe operation
acceptance, not latency, energy, calibration evidence, benchmark results,
hardware certification, measured accuracy, plugin entry points, or executable
backend behavior.

## Motivation

Backend capability manifests are intentionally narrow. Without concrete
negative examples, future backend authors may try to place useful-looking but
unsafe claims into `tuc.backend_capability.v0`.

This matters because misleading fields can weaken TUC's Universal Compute
boundary:

- Latency and energy assumptions belong to transfer-cost profiles.
- Calibration evidence needs its own schema and threat model.
- Benchmarks and hardware certificates need provenance and review rules.
- Noise-model implementation details must not become HAC-IR attributes or
  plugin import paths.

## Decision

Extend `docs/BACKEND_CAPABILITY_SCHEMA.md` with invalid and misleading
examples for:

- Latency or energy fields in backend capability manifests.
- Calibration evidence or hardware serials in capability manifests.
- Performance or certification claims.
- Impossible or misleading error budgets.

Extend backend-author negative tests to reject:

- Transfer-cost fields in capability manifests.
- Calibration evidence fields.
- Hardware serials.
- Benchmark and certificate fields.
- Measured-error fields.
- Noise-model module fields.
- Negative error-budget values.

## Security Model

The negative examples reinforce the existing pure-data boundary:

- Backend capability manifests do not execute backend code.
- Unknown manifest fields fail closed.
- Backend capability data does not include host paths, device identifiers,
  plugin modules, dynamic libraries, calibration artifacts, benchmark outputs,
  or generated artifacts.
- Error-budget limits remain finite and non-negative acceptance limits, not
  correctness proofs.

## Consequences

- Backend authors get concrete examples of what not to submit.
- Maintainers get test-backed rejection cases for misleading capability claims.
- Runtime planning assumptions stay in transfer-cost profiles.
- HAC-IR remains insulated from backend-specific measurement and certification
  claims.

## Alternatives Considered

1. Keep only the generic unknown-field rejection.

   Rejected because generic rejection does not teach authors which claims are
   misplaced or why.

2. Add optional benchmark and calibration fields now.

   Rejected because measured artifacts need provenance, resource budgets,
   review rules, and likely separate schemas.

3. Treat negative examples as prose only.

   Rejected because backend onboarding needs executable regression tests for
   common unsafe claims.

## Follow-Up

1. Add a HAC-IR semantic charter that separates compute intent, compiler facts,
   planning constraints, and forbidden backend details.
2. Add dedicated calibration-artifact and benchmark-evidence schemas only after
   explicit security RFCs.
3. Extend negative examples when specialized backend proof tracks begin.
