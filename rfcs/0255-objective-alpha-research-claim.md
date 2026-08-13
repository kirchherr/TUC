# RFC 0255: Objective Alpha Research Claim

- Status: Accepted
- Date: 2026-07-08
- Area: Objective Alpha research evidence

## Summary

Add `objective_alpha_research_claim` as a compact digest-only snapshot of the
current Objective Alpha Universal Compute research claim.

## Motivation

Objective Alpha now has a full public proof bundle, a catalog growth surface,
public admission gates, and a Source Intent mixed-runtime proof. Reviewers need
a single small artifact that states what this proves without embedding all
supporting reports or opening new execution surfaces.

## Decision

Create `examples/objective_alpha_research_claim.py` with schema
`schemas/objective_alpha_research_claim_report.v0.schema.json`, golden
`tests/golden/proofs/objective_alpha_research_claim.json`, and documentation at
`docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM.md`.

The report binds these artifacts by SHA-256 digest:

- `objective_alpha_public_proof_bundle`
- `objective_alpha_public_proof_bundle_gate`
- `objective_alpha_evidence_extension_policy`
- `objective_alpha_public_evidence_catalog`
- `objective_alpha_public_evidence_catalog_admission_gate`
- `source_intent_mixed_runtime_public_proof_bundle`

## Security Boundary

This RFC does not authorize broad source parsing, frontend package import,
plugin discovery, Triton JIT, device access, generated artifact execution,
native backend execution, native performance claims, backend artifact loading,
runtime handle serialization, raw tensor values, Source Intent payload bodies,
raw source text, host path exposure, commands, subprocesses, or network access.

The claim report is digest-only and source-free.

## Acceptance Criteria

- The report is schema-versioned and closed with `additionalProperties: false`.
- The report binds exactly six supporting artifacts by SHA-256 digest.
- The public proof bundle is still full at sixteen entries.
- The public evidence catalog has six entries and its admission gate passes.
- The Source Intent mixed-runtime proof passes backend equivalence and reference
  correctness.
- Native performance, vendor replacement, broad source parsing, arbitrary
  third-party backend execution, device access, generated artifact execution,
  and production Triton integration remain blocked.
