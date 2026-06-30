# RFC 0240: Objective Alpha Capability Claim Gate Catalog Entry

## Status

Accepted.

## Context

Objective Alpha's fixed public proof bundle is full. The Objective Alpha Public
Evidence Catalog is the append-only, RFC-bound growth surface for additional
public evidence that should not be inserted into the fixed sixteen-entry bundle.

The Source-To-Intent Research Capability Claim Gate now exposes the exact
thirteen evidence IDs that support the bounded Universal Compute research
claim. That gate is the clearest public claim boundary for the current research
slice, but it was not yet represented as a catalog entry.

## Decision

Add `source_to_intent_research_capability_claim_gate` as a digest-only Objective
Alpha Public Evidence Catalog entry.

The entry uses:

- evidence ID: `source_to_intent_research_capability_claim_gate`
- entry point: `python examples/source_to_intent_research_capability_claim_gate.py`
- artifact kind: `deterministic_source_to_intent_research_capability_claim_gate_output`
- extension tier: `claim_boundary`
- digest source: `source_to_intent_research_capability_claim_gate_report`
- raw output policy: `digest_only`

The catalog now requires extension-tier coverage for `governance`,
`runtime_proof`, `frontend_runtime_proof`, and `claim_boundary`. The admission
gate binds the new claim-gate digest and fails closed if the expected entry IDs,
entry points, artifact kinds, tiers, raw-output policies, digest count, or tier
coverage drift.

## Contract

- Catalog example: `examples/objective_alpha_public_evidence_catalog.py`
- Catalog schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- Catalog docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`
- Admission gate example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- Admission gate schema:
  `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- Admission gate docs:
  `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`

## Security Boundary

This change is data-only. It does not parse source text, execute source,
run runtime backends, discover plugins, resolve filesystem paths, load dynamic
libraries, touch devices, spawn subprocesses, emit generated artifacts, or
authorize native performance claims.

The catalog stores only bounded identifiers, entry metadata, extension tiers,
SHA-256 metadata digests, blocked claims, blocked execution surfaces, and policy
status.

## Consequences

The public Objective Alpha evidence catalog now exposes a dedicated claim-boundary
entry next to governance, runtime-proof, and frontend-runtime-proof entries.
Reviewers can follow the current bounded Universal Compute research claim from
public catalog metadata to the CI-facing capability claim gate without expanding
the fixed public proof bundle or weakening the source-free evidence boundary.