# RFC 0067: Leaky Abstraction Report

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha / Beta / Epsilon

## Summary

TUC adds a diagnostic Leaky Abstraction Report for reviewing whether
hardware-specific performance facts stay outside HAC-IR.

This RFC does not add native benchmarks, native performance claims, executable
CUDA/HIP backends, device access, generated-artifact execution, raw benchmark
output ingestion, plugin discovery, dynamic libraries, subprocess execution, or
hardware-specific HAC-IR semantics.

## Motivation

RFC 0063 identifies leaky abstraction as one of the main limits of the
Universal Compute proof. If hardware-specific performance facts enter HAC-IR,
the hardware-independent interface becomes a disguised backend interface.

RFC 0064 requires `leaky_abstraction_report` evidence before native performance
proposals can pass readiness. This RFC supplies the first narrow diagnostic
report for HAC-IR boundary review.

## Decision

Add [Leaky Abstraction Report](../docs/LEAKY_ABSTRACTION_REPORT.md) with:

- `schemas/leaky_abstraction_report.v0.schema.json`
- `build_leaky_abstraction_report(hac_ir, performance_facts=())`
- `dump_leaky_abstraction_report(report)`
- report schema version `tuc.leaky_abstraction_report.v0`
- claim boundary `performance_proof_boundary.blocking.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report checks the existing `HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES` guard and
lets future performance proposals list hardware-specific facts with their
correct homes outside HAC-IR.

## Correct Homes

The v0 report allows performance facts to live in:

- `backend_capability`
- `hs_ir`
- `runtime_plan`
- `compiler_decision_report`
- `backend_implementation`
- `benchmark_artifact`
- `security_rfc`

It does not allow HAC-IR as a correct home for hardware-specific performance
facts.

## Security Boundary

The report must not include raw benchmark output, host paths, hardware serials,
device identifiers, plugin entrypoints, backend artifacts, generated code,
dynamic-library paths, cache paths, environment variables, or native
performance parity fields.

The report must not execute backend artifacts.
The report must not load benchmark artifacts.
The report must not add hardware-specific performance knobs to HAC-IR.

The schema is fail-closed with `additionalProperties: false` on every object.

## Evidence

The implementation adds:

- `schemas/leaky_abstraction_report.v0.schema.json`
- `examples/leaky_abstraction_report.py`
- `docs/LEAKY_ABSTRACTION_REPORT.md`
- `tests/test_leaky_abstraction_report.py`
- `tests/test_leaky_abstraction_report_schema.py`
- report APIs in `src/tuc/proof.py`

## Consequences

- Leaky abstraction becomes a reviewable diagnostic artifact.
- HAC-IR neutrality remains tied to executable guardrails.
- Performance proposals can list hardware-specific facts without giving those
  facts permission to enter HAC-IR.
- Native performance claims remain blocked until the rest of the performance
  proof evidence exists.

## Rejected Alternatives

1. Put hardware-specific performance facts into HAC-IR.

   Rejected because this destroys the hardware-independent interface.

2. Track abstraction leakage in prose only.

   Rejected because the report must be deterministic and testable.

3. Treat a clean leaky-abstraction report as native performance proof.

   Rejected because performance proof also requires native baseline provenance,
   benchmark methodology, planner-overhead evidence, correctness goldens,
   benchmark artifacts, and executable-backend security review.
