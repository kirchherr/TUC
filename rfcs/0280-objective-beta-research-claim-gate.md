# RFC 0280: Objective Beta Research Claim Gate

## Status

Accepted.

## Context

Objective Beta needs a CI-facing gate so the successor research snapshot cannot
silently expand claims, reorder evidence, or drift from source-free digest-only
review semantics.

## Decision

Add Objective Beta Research Claim Gate v0:

- Example: `examples/objective_beta_research_claim_gate.py`
- Schema: `schemas/objective_beta_research_claim_gate_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_beta_research_claim_gate.json`
- Doc: `docs/OBJECTIVE_BETA_RESEARCH_CLAIM_GATE.md`
- Tests: `tests/test_objective_beta_research_claim_gate.py`

The gate binds the serialized Objective Beta claim by digest and fails closed on
claim digest drift, source leakage, evidence-order drift, opened source
admission, native performance claims, or vendor replacement claims.

## Security

The gate validates metadata only. It does not execute source, import packages,
discover plugins, run JIT, access devices, load generated artifacts, or serialize
raw tensor/source values.