# RFC 0099: Runtime Candidate Scoring Policy

- Status: accepted-for-prototype
- Created: 2026-06-11
- Phase: Delta

## Summary

Add Runtime Candidate Scoring Policy v0 as a schema-versioned, deterministic
report for current candidate-selection semantics.

## Motivation

TUC now has runtime candidate score diagnostics and evidence. The next risk is
semantic drift: future scoring components could enter the planner without a
clear policy that explains which comparator inputs are active and which are
blocked.

Before adding transfer/noise-aware or error-budget-aware scoring, the current
rule-based comparator must be explicit and testable.

## Decision

Add:

- [Runtime Candidate Scoring Policy](../docs/RUNTIME_CANDIDATE_SCORING_POLICY.md)
- `schemas/runtime_candidate_scoring_policy.v0.schema.json`
- `examples/runtime_candidate_scoring_policy.py`
- golden output at
  `tests/golden/runtime_candidate_scoring_policy/current_policy_report.json`
- focused tests in `tests/test_runtime_candidate_scoring_policy.py`

Policy v0 records the active comparator order:

1. `transfer_score`
2. `layout_conversion_bytes`
3. `transfer_bytes`
4. `preferred_memory_domain_match`
5. `backend_name_tiebreaker`

It also records blocked future components:

- `noise_penalty`
- `error_budget_margin`
- `calibration_confidence`
- `benchmark_score`

## Security Model

The policy report is data-only. It does not add plugin discovery, backend
imports, dynamic-library loading, subprocess execution beyond the example
Python process, device access, network access, JIT execution, generated-artifact
execution, host-path reads, environment reads, benchmark output, secrets, write
tokens, or publishing permissions.

Policy v0 keeps automatic global optimization and noise/error-budget scoring
disabled.

## Consequences

- Candidate-selection semantics are now an explicit review artifact.
- Future scoring changes can be reviewed against a stable policy diff.
- Noise, error-budget, calibration, and benchmark score inputs remain blocked
  until separately modeled and reviewed.

## References

- [Runtime Candidate Scoring Policy](../docs/RUNTIME_CANDIDATE_SCORING_POLICY.md)
- [Runtime Candidate Score Evidence](../docs/RUNTIME_CANDIDATE_SCORE_EVIDENCE.md)
- `schemas/runtime_candidate_scoring_policy.v0.schema.json`
- `examples/runtime_candidate_scoring_policy.py`
