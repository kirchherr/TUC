# RFC 0179: Source-To-Intent Research Capability Claim Gate

- Status: Accepted
- Date: 2026-06-17
- Owners: TUC maintainers
- Related artifacts:
  - `examples/source_to_intent_research_capability_claim_gate.py`
  - `examples/source_to_intent_research_capability_claim.py`
  - `tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt`
  - `tests/test_source_to_intent_research_capability_claim_gate.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md`
  - `.github/workflows/ci.yml`

## Context

RFC 0178 added a digest-only capability claim report that states the current
bounded Universal Compute research claim without approving production parsing,
native performance, hardware certification, arbitrary backend execution, or
vendor compiler replacement.

That report is useful for reviewers, but CI also needs a small text gate that
fails closed when the supported claim, blocked claims, accepted runtime count,
operation path, trusted backends, or evidence digests drift.

## Decision

Add Source-To-Intent Research Capability Claim Gate v0.

The gate:

- consumes the capability claim report;
- validates the report contract;
- compares the supplied report digest with the freshly built current report;
- emits a source-free text gate with claim ID, claim scope, claim status,
  accepted kernel count, runtime case count, backend-equivalence shape-profile
  case count, trusted runtime backends, supported claims, blocked claims,
  parser status, and artifact policy;
- fails closed on source leakage, invalid JSON, contract drift, claim expansion,
  or evidence digest drift;
- runs in CI after the capability claim report.

## Security

The gate does not parse source text, import modules from user code, execute
Triton, run runtime backends, access devices, discover plugins, emit generated
artifacts, or read host paths.

The gate output is source-free and records only identifiers, counts, blocked
claim names, and one SHA-256 digest.

## Consequences

The high-level research claim now has a merge-facing CI control. Future claim
expansion must update the evidence chain, claim report, gate, golden, tests,
docs, and RFCs together.
