# RFC 0279: Objective Beta Research Claim

## Status

Accepted.

## Context

Objective Alpha proves the first bounded Universal Compute research shape.
Since then, TUC has added realistic Kernel Ingress evidence, First Real Triton
Kernel Path evidence, first-slice portfolio evidence, admission readiness, and a
maintainer approval request packet. These should be bound as a successor
snapshot without expanding Alpha's fixed public proof bundle.

## Decision

Add Objective Beta Research Claim v0:

- Example: `examples/objective_beta_research_claim.py`
- Schema: `schemas/objective_beta_research_claim_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_beta_research_claim.json`
- Doc: `docs/OBJECTIVE_BETA_RESEARCH_CLAIM.md`
- Tests: `tests/test_objective_beta_research_claim.py`

The claim binds Objective Alpha, Kernel Ingress, First Real Triton Path,
first-slice evidence, readiness, maintainer approval request, and Research
Scope Claim Gate evidence by digest.

## Non-Goals

This RFC does not approve source ingestion, implement a production parser,
execute Triton JIT, access devices, execute native backend artifacts, claim
native performance parity, or replace CUDA/ROCm/XLA/TVM/IREE.

## Security

The claim is source-free, digest-only, and fixed-artifact based. It must keep:

- `source_ingestion_admitted = false`
- `admission_ready = false`
- `surface_opened = false`
- `native_performance_claim = false`
- `vendor_replacement_claim = false`