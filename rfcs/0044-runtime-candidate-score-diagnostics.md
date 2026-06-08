# RFC 0044: Runtime Candidate Score Diagnostics

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Delta

## Summary

TUC adds opt-in runtime candidate score diagnostics.

The implementation introduces `CandidateScore` records on `PartitionPlan`.
Callers can request them with `include_candidate_scores=True` on
`partition_graph(...)` or `compile_graph(...)`.

This is diagnostic evidence only. It does not add automatic global optimization
or change default runtime placement behavior.

## Motivation

Runtime planning is a strategic proof asset. TUC already reports final
assignments, accepted/rejected backend support diagnostics, transfer edges, and
manual override effects. The next missing review surface is the score tuple used
when multiple accepted candidates remain.

Without candidate score diagnostics, future transfer-aware, noise-aware, or
override-aware scoring could change backend choices without a compact artifact
showing which score components drove the result.

## Decision

Add `CandidateScore` as bounded runtime-planning data with:

- operation name
- backend name
- selection stage
- selected flag
- transfer score
- transfer score unit
- transfer bytes
- layout conversion bytes
- preferred memory-domain match flag
- memory domain
- produced layout

Runtime plan dumps include a `candidate_scores` block when diagnostics are
enabled.

Compiler decision reports include per-operation `candidate_scores` blocks when
the partition plan carries those diagnostics.

Golden fixtures cover the first candidate-score graph:

- `tests/golden/runtime_plans/candidate_scores.txt`
- `tests/golden/compiler_decisions/candidate_scores.txt`

## Security Model

Candidate scores are derived only from:

- validated graph operations
- explicit backend capability data
- bounded movement estimates
- validated transfer-cost profiles
- already validated manual override effects

The implementation does not:

- execute backend code
- discover plugins
- import modules
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- touch the network
- read host paths
- read environment variables
- change HAC-IR
- change backend capability data
- change operation semantics

Diagnostic names, units, byte counts, booleans, memory domains, and layouts are
validated before they can be dumped.

## Consequences

- Future candidate scoring has a stable evidence surface.
- Maintainers can review score components without relying only on final
  assignment reasons.
- Existing compile and partition behavior remains unchanged unless callers opt
  into candidate diagnostics.

## Follow-Up

1. Add noise/error-budget score components only after those models are stable
   and documented separately from HAC-IR semantics.
2. Add candidate scoring for future softmax proof graphs once nonlinear
   operation-family planning is documented.
3. Keep automatic global optimization blocked until score semantics are
   versioned, golden-tested, and reviewed as a separate RFC.

