# RFC 0100: Runtime Candidate Scoring Conformance

Status: accepted

## Summary

Add Runtime Candidate Scoring Conformance v0 as a schema-versioned,
deterministic report that verifies the runtime planner's observable candidate
selection behavior against the active Runtime Candidate Scoring Policy.

## Motivation

Runtime Candidate Scoring Policy documents comparator semantics, but policy
alone does not prove that the planner still behaves that way. TUC needs a small
review artifact that detects accidental drift in transfer scoring, layout
conversion accounting, transfer-byte tie-breaking, preferred-domain
tie-breaking, and backend-name tie-breaking.

## Artifacts

- [Runtime Candidate Scoring Conformance](../docs/RUNTIME_CANDIDATE_SCORING_CONFORMANCE.md)
- `schemas/runtime_candidate_scoring_conformance_report.v0.schema.json`
- `examples/runtime_candidate_scoring_conformance.py`
- deterministic golden:
  `tests/golden/runtime_candidate_scoring_conformance/current_conformance_report.json`
- focused tests in `tests/test_runtime_candidate_scoring_conformance.py`

## Design

The report runs five bounded planning fixtures:

1. `transfer_score_latency_prefers_lower`
2. `layout_conversion_bytes_recorded`
3. `transfer_bytes_tiebreaker`
4. `preferred_memory_domain_match_tiebreaker`
5. `backend_name_tiebreaker`

Each fixture constructs typed in-memory `ComputeGraph` and `BackendCapability`
data, calls `partition_graph(..., include_candidate_scores=True)`, and records
only expected and observed backend names plus safe detail identifiers.

## Security

The report is data-only. It does not add plugin discovery, dynamic imports,
dynamic library loading, subprocess execution, device access, network access,
generated-artifact execution, JIT execution, host-path reads, environment
reads, raw benchmark output, or executable backend permission.

All report text is bounded and identifier-shaped. Issues are derived from case
status and active component coverage rather than accepted as arbitrary caller
text.

## Non-Goals

- No global optimizer.
- No benchmark execution.
- No native performance claim.
- No new backend execution path.
- No approval for noise, calibration, error-budget, or benchmark score inputs.

## Acceptance

The RFC is accepted when:

- the report passes with all five current cases,
- the golden output is deterministic,
- the JSON schema fails closed,
- the report is referenced from roadmap/status documentation,
- focused tests cover positive and fail-closed behavior.

## Follow-Up

Future candidate score components must extend this conformance layer before
they change planner behavior. Noise, error-budget, calibration, and benchmark
score components remain blocked until their independent data models, schemas,
goldens, and security review exist.
