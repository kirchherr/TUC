# RFC 0074: Break-Even Workload Size Report

Status: Accepted

## Summary

TUC adds a diagnostic Break-Even Workload Size Report for reviewing future
claims about the workload size where planner overhead is amortized by execution.

## Motivation

The performance proof boundary identifies planner overhead as one of the major
risks for a hardware-independent compute interface. Small workloads can be
dominated by planning cost even when execution is correct and portable.

TUC needs a bounded review contract for break-even evidence before any future
proposal may claim that planning overhead is acceptable for a workload class.
Without this contract, proposals could smuggle raw timing samples, host paths,
command lines, backend artifacts, or device identifiers into proof artifacts.

## Decision

Add [Break-Even Workload Size Report](../docs/BREAK_EVEN_WORKLOAD_SIZE_REPORT.md)
with:

- `schemas/break_even_workload_size_report.v0.schema.json`
- `build_break_even_workload_size_report(proposal_name, workloads=())`
- `dump_break_even_workload_size_report(report)`
- report schema version `tuc.break_even_workload_size_report.v0`
- artifact status `diagnostic_only`
- performance claim status `blocked`

The report contains only bounded identifiers, validation status, optional
bounded problem size, and digest status. It does not contain raw timings.

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
  native source contents, backend binaries, generated code, or benchmark report
  contents

Unknown keys fail closed through JSON Schema and runtime validation.

## Readiness Semantics

`break_even_workload_size_ready` means only:

- at least one bounded workload entry is present
- every entry has status `validated_by_ci`
- every entry supplies a bounded problem size
- every entry supplies a `sha256:` digest

It does not mean TUC may claim native performance parity or near-native
performance. The report always emits `native_performance_claim = false` and
`performance_claim_status = blocked`.

## Consequences

Future native performance proposals gain a reviewable break-even evidence
contract before planner-benefit claims can be considered.

The current project remains blocked from native performance claims until the
full Performance Proof Boundary and Performance Proof Readiness report pass.

## Artifacts

- `schemas/break_even_workload_size_report.v0.schema.json`
- `examples/break_even_workload_size_report.py`
- `docs/BREAK_EVEN_WORKLOAD_SIZE_REPORT.md`
- `tests/test_break_even_workload_size_report.py`
- `tests/test_break_even_workload_size_schema.py`
