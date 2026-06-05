# RFC 0027: Compiler Decision Report

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 2

## Summary

TUC adds a compiler-level decision report that connects backend support
diagnostics with the final runtime partition plan.

Every `CompilationResult` now carries a `CompilerDecisionReport` and can render
it with `dump_decision_report`.

## Motivation

Backend support diagnostics explain whether a capability accepts an operation,
but compiler users need that information at the pipeline level. As backend
selection grows into cost-model and heterogeneous runtime work, TUC must avoid
opaque decisions that only appear as final assignments.

The decision report gives reviewers and backend authors a stable view of:

- The selected backend per operation.
- The support decisions for all registered backend candidates.
- The reason codes behind accepted and rejected candidates.

## Decision

Add:

- `CompilerDecisionReport`
- `OperationDecision`
- `build_decision_report`
- `dump_decision_report`
- `CompilationResult.decision_report`
- `CompilationResult.dump_decision_report`
- Documentation in `docs/COMPILER_DECISION_REPORT.md`

The report is built after partitioning from the HAC-IR graph, backend registry,
and partition plan.

## Security Model

Decision reports are pure data.

They do not:

- Import backend modules.
- Call backend `lower`.
- Spawn subprocesses.
- Load dynamic libraries.
- Open devices.
- Execute backend artifacts.
- Include host paths, device identifiers, imported module names, or backend
  execution output.

The compiler now constructs an explicit backend capability registry from
provided capabilities, so unsafe backend names and duplicate backend
registrations fail closed before partitioning.

## Consequences

- Compiler decisions become inspectable without adding backend execution
  surface.
- Future cost-model work has a stable report shape to extend.
- Existing diagnostics remain available as compact assignment strings.

## Follow-Up

1. Add candidate scoring once transfer/noise-aware cost models mature.
2. Add golden decision-report dumps for representative graphs.
3. Thread report summaries into future CLI or developer-facing debug views.
