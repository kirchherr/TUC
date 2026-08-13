# RFC 0256: Objective Alpha Research Claim Gate

- Status: Accepted
- Date: 2026-07-09
- Area: Objective Alpha research evidence

## Summary

Add `objective_alpha_research_claim_gate` as the CI-facing gate for the current
Objective Alpha Research Claim snapshot.

## Motivation

The claim snapshot gives reviewers a compact digest-only statement of the
current Objective Alpha Universal Compute research claim. The gate makes that
claim merge-relevant by binding its digest, evidence IDs, public bundle count,
catalog count, supported claims, blocked claims, and required invariants.

## Decision

Create `examples/objective_alpha_research_claim_gate.py` with schema
`schemas/objective_alpha_research_claim_gate_report.v0.schema.json`, golden
`tests/golden/proofs/objective_alpha_research_claim_gate.json`, and
documentation at `docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md`.

The gate consumes serialized claim-report data, validates the claim contract,
and rejects claim digest drift.

## Contract

- Example: `examples/objective_alpha_research_claim_gate.py`
- Schema: `schemas/objective_alpha_research_claim_gate_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_alpha_research_claim_gate.json`
- Documentation: `docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md`
- RFC path: `rfcs/0256-objective-alpha-research-claim-gate.md`

## Security Boundary

This RFC does not authorize broad source parsing, frontend package import,
plugin discovery, Triton JIT, device access, generated artifact execution,
native backend execution, native performance claims, backend artifact loading,
runtime handle serialization, raw tensor values, Source Intent payload bodies,
raw source text, host path exposure, commands, subprocesses, or network access.

The gate report is digest-only and source-free.

## Acceptance Criteria

- The gate report is schema-versioned and closed with `additionalProperties: false`.
- The gate binds the Objective Alpha Research Claim digest and metadata digest.
- The gate binds exactly six claim evidence IDs in fixed order.
- The gate requires public bundle count 16, catalog count 6, and total public
  evidence count 22.
- Native performance, vendor replacement, broad source parsing, arbitrary
  third-party backend execution, device access, generated artifact execution,
  and production Triton integration remain blocked.
