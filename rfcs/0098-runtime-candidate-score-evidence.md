# RFC 0098: Runtime Candidate Score Evidence

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Delta

## Summary

Add Runtime Candidate Score Evidence v0 as a schema-versioned, deterministic
report for opt-in runtime candidate score diagnostics.

## Motivation

Candidate score diagnostics already explain why the rule-based runtime planner
selected one accepted backend over another. The missing piece is a compact
evidence artifact that reviewers and CI can use to detect drift.

TUC should prove that richer runtime planning remains explainable before it
allows automatic global optimization or performance claims.

## Decision

Add:

- [Runtime Candidate Score Evidence](../docs/RUNTIME_CANDIDATE_SCORE_EVIDENCE.md)
- `schemas/runtime_candidate_score_evidence_report.v0.schema.json`
- `examples/runtime_candidate_score_evidence.py`
- golden output at
  `tests/golden/runtime_candidate_score_evidence/profiled_candidate_score_report.json`
- focused tests in `tests/test_runtime_candidate_score_evidence.py`
- a read-only CI workflow step running
  `python examples/runtime_candidate_score_evidence.py`

The report verifies that default planning stays score-free, opt-in planning
emits bounded score evidence, compiler decision reports carry the same score
count and score digest, every operation has exactly one selected candidate, and
rejected candidate evidence remains visible.

## Security Model

The report is data-only. It does not add plugin discovery, backend imports,
dynamic-library loading, subprocess execution beyond the CI Python process,
device access, network access, JIT execution, generated-artifact execution,
host-path reads, environment reads, secrets, write tokens, or publishing
permissions.

Candidate scores remain diagnostics. They do not authorize backend execution,
native performance claims, global optimization, or backend approval.

## Consequences

- Runtime planning explanation quality becomes a testable evidence artifact.
- Future score components can be reviewed against a stable report shape.
- Automatic global optimization remains blocked until separately versioned,
  golden-tested, and reviewed.

## References

- [Runtime Candidate Score Evidence](../docs/RUNTIME_CANDIDATE_SCORE_EVIDENCE.md)
- [Runtime Transfer Plan](../docs/RUNTIME_PLAN.md)
- `schemas/runtime_candidate_score_evidence_report.v0.schema.json`
- `examples/runtime_candidate_score_evidence.py`
