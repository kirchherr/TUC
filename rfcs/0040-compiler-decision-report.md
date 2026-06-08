# RFC 0040: Compiler Decision Report

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Gamma/Delta

## Summary

TUC adds compiler-level decision reports that connect pure backend support
diagnostics to runtime partition assignments.

The new report is exposed through `CompilationResult.decision_report` and
`CompilationResult.dump_decision_report()`.

## Motivation

The backend registry can already explain why each registered backend capability
accepts or rejects one operation. Runtime planning can already explain final
assignments, transfer bytes, produced layouts, and fallback reasons.

Those pieces were still separate. Reviewers had to inspect registry diagnostics
before planning and runtime-plan dumps after planning, then mentally connect
them.

TUC needs a single compiler artifact that says:

- this operation was assigned here
- these capabilities accepted it
- these capabilities rejected it
- this planning reason selected the assignment

That keeps backend selection explainable before adding candidate scoring or
more complex planning.

## Decision

Add `tuc.compiler.decisions` with:

- `OperationDecisionReport`
- `CompilerDecisionReport`
- `build_compiler_decision_report(...)`

The compiler pipeline builds the report after HAC-IR validation and runtime
partitioning, then stores it on `CompilationResult`.

The report uses the explicit `BackendRegistry.from_capabilities(...)` path to
derive support diagnostics from trusted in-memory capability data. It does not
store backend objects or run backend lowering.

## Security Model

The decision report is pure data.

It does not:

- discover backend plugins
- import backend modules
- execute backend code
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- read environment variables
- touch the network

It is derived from validated HAC-IR operations, bounded backend capability
data, registry support diagnostics, and the already-built runtime partition
plan.

## Consequences

- Compiler results now carry structured decision evidence.
- Reviewers can see rejected backend reasons next to the final assignment.
- Fallback decisions become easier to audit.
- Candidate scoring can later build on an inspectable report rather than
  replacing opaque logic with more opaque logic.

## Alternatives Considered

1. Keep registry diagnostics separate from compiler results.

   Rejected because compiler users need the support evidence attached to the
   actual compilation result they are reviewing.

2. Put support diagnostics into HAC-IR attributes.

   Rejected because backend support is not hardware-independent compute intent.
   It belongs in compiler/runtime evidence, not HAC-IR semantics.

3. Execute backend dry-run checks for richer diagnostics.

   Rejected because capability checks must remain execution-free until a
   separate plugin lifecycle, sandboxing, and threat model exists.

## Follow-Up

1. Add golden decision-report fixtures for representative proof and MVP graphs.
2. Extend decision reports with candidate scores only after transfer/noise-aware
   scoring is stable and documented.
3. Keep rejected backend diagnostics bounded and free of host paths or backend
   executable details.
