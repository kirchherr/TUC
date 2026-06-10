# RFC 0073: Native Baseline Comparison Report

Status: Accepted

## Summary

TUC adds a diagnostic Native Baseline Comparison Report for reviewing future
native performance evidence without executing benchmark code or ingesting raw
benchmark output.

## Motivation

The performance proof boundary already requires native baseline provenance,
benchmark methodology, workload scope, toolchain environment, and artifact
inventory. One important evidence item remains separate: the explicit comparison
between a TUC baseline artifact and a native benchmark artifact.

Without a bounded comparison contract, future proposals could smuggle raw timing
data, host paths, command lines, generated artifacts, or device details into
review documents. That would weaken secure-by-design review and make premature
native performance claims easier.

## Decision

Add [Native Baseline Comparison Report](../docs/NATIVE_BASELINE_COMPARISON_REPORT.md)
with:

- `schemas/native_baseline_comparison_report.v0.schema.json`
- `build_native_baseline_comparison_report(proposal_name, comparisons=())`
- `dump_native_baseline_comparison_report(report)`
- report schema version `tuc.native_baseline_comparison_report.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report contains only bounded identifiers, result validation status, and
digest status. It does not contain raw benchmark values.

## Security Boundary

The report must not:

- run benchmarks
- load benchmark report artifacts
- parse raw benchmark output
- store raw timing samples
- inspect host hardware
- read environment variables
- execute generated code or backend artifacts
- access devices
- run subprocesses
- load dynamic libraries
- include host paths, command lines, secrets, hardware serials, device IDs,
  native source contents, backend binaries, or generated code

Unknown keys fail closed through JSON Schema and runtime validation.

## Readiness Semantics

`native_baseline_comparison_ready` means only:

- at least one bounded comparison entry is present
- every comparison has result status `validated_by_ci`
- every comparison has a `sha256:` digest

It does not mean TUC may claim native performance parity. The report always
emits `native_performance_claim = false` and `performance_claim_status =
blocked`.

## Consequences

Future native performance proposals gain a reviewable comparison contract before
numbers can be considered evidence.

The current project remains blocked from native performance claims until the
full Performance Proof Boundary and Performance Proof Readiness report pass.

## Artifacts

- `schemas/native_baseline_comparison_report.v0.schema.json`
- `examples/native_baseline_comparison_report.py`
- `docs/NATIVE_BASELINE_COMPARISON_REPORT.md`
- `tests/test_native_baseline_comparison_report.py`
- `tests/test_native_baseline_comparison_schema.py`
