# RFC 0239: Source-To-Intent Capability Claim Gate Evidence-ID Binding

## Status

Accepted.

## Context

The Source-To-Intent Research Capability Claim report already records the exact
source-free evidence artifacts that support the current bounded Universal
Compute research claim. The CI-facing Capability Claim Gate previously exposed
only `evidence_count = "13"` in its text output.

A count is useful but not sufficient as a reviewer-facing binding. A gate that
only says how many artifacts exist can hide accidental evidence substitution
behind the claim report contract. The top-level gate should also show the exact
artifact IDs that the claim depends on.

## Decision

Add an exact evidence-ID binding to
`examples/source_to_intent_research_capability_claim_gate.py`.

The gate now emits:

```text
evidence_ids = "source_to_intent_research_proof_bundle,..."
```

The value is derived from the validated claim report and must match the
capability claim's required evidence IDs exactly and in order. The gate contract
rejects drift in this line.

The canonical artifacts remain:

- gate example: `examples/source_to_intent_research_capability_claim_gate.py`
- claim report input: `examples/source_to_intent_research_capability_claim.py`
- golden: `tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt`
- tests: `tests/test_source_to_intent_research_capability_claim_gate.py`
- docs: `docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md`

## Security Boundary

This change is data-only. It does not parse source text, import Triton modules,
execute source, run runtime backends, access devices, discover plugins, emit
generated artifacts, read host paths, or authorize performance claims.

The gate output remains source-free and contains stable identifiers, exact
evidence IDs, counts, claim boundaries, blocked claim names, and one SHA-256
claim digest.

## Consequences

Reviewers can now see which evidence artifacts support the bounded Universal
Compute research claim directly from the CI gate output. Future changes that
add, remove, reorder, or substitute evidence must update the claim report, gate,
golden, tests, docs, and RFC trail together.
