# RFC 0033: Backend Capability Schema Assumptions

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Gamma

## Summary

TUC documents backend capability schema assumptions for error budgets, latency,
energy, calibration, and noise modeling.

The goal is to keep backend self-description useful to future hardware authors
without letting backend-specific assumptions leak into HAC-IR or compiler-time
execution paths.

## Motivation

Backend capability data is the bridge between hardware-independent compute
intent and runtime planning. That bridge needs precise language before TUC
accepts more backend proposals.

Fields such as `max_error_budget`, `supports_noise_model`, and
`supports_calibration` can be misunderstood as correctness proofs or hardware
certification claims. Transfer-cost fields such as `bandwidth_gb_s`,
`base_latency_ns`, and `energy_pj_per_byte` can be misunderstood as measured
performance. TUC needs a clear contract that labels these values as prototype
capability claims and deterministic planning assumptions.

## Decision

Add `docs/BACKEND_CAPABILITY_SCHEMA.md`.

The document defines:

- `tuc.backend_capability.v0` fields.
- `tuc.transfer_cost_profile.v0` fields.
- Error-budget assumptions.
- Latency and energy assumptions.
- Calibration assumptions.
- Noise-model assumptions.
- Validation and security boundaries.
- Reviewer checklist for future schema changes.

Add tests that assert the document covers current manifest fields, schema
versions, planning assumptions, and forbidden execution surfaces.

## Security Model

The schema documentation preserves the current safe boundary:

- Capability manifests are declarative data.
- Transfer-cost profiles are deterministic planning assumptions.
- Capability checks do not execute backend code.
- Latency and energy fields do not certify hardware performance.
- Calibration flags do not permit device access or calibration-artifact loading.
- Noise-model flags do not permit HAC-IR semantic changes.

Any future calibration artifacts, measured performance reports, plugin
execution, or backend lifecycle behavior need separate schemas, threat models,
resource budgets, and sandboxing rules.

## Consequences

- Backend authors get clearer guidance before proposing new manifests.
- Maintainers have a checklist for rejecting misleading capability claims.
- HAC-IR remains protected from backend-specific performance, calibration, and
  device assumptions.
- Runtime planning can use transfer profiles without treating them as hardware
  certification.

## Alternatives Considered

1. Leave assumptions only in Backend API prose.

   Rejected because these fields are important enough to need a dedicated,
   test-referenced contract.

2. Add latency and energy fields directly to backend capability manifests.

   Rejected for v0 because latency and energy are movement/profile assumptions,
   not operation-acceptance facts.

3. Treat calibration and noise flags as backend certification.

   Rejected because TUC does not yet have real backend certification,
   calibration artifacts, or hardware execution.

## Follow-Up

1. Add capability-schema negative examples for invalid or misleading backend
   claims.
2. Add versioned calibration-artifact schema only after a dedicated security
   RFC.
3. Add measured performance evidence only after benchmark provenance and
   review requirements are defined.
