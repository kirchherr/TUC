# RFC 0254: Objective Alpha Source Intent Mixed Runtime Public Proof Catalog Entry

- Status: Accepted
- Date: 2026-07-08
- Area: Objective Alpha public evidence catalog

## Summary

Admit `source_intent_mixed_runtime_public_proof_bundle` as a digest-only
`frontend_runtime_proof` entry in the Objective Alpha Public Evidence Catalog.

The entry binds the Source Intent Mixed Runtime Public Proof Bundle by SHA-256
metadata digest after the fixed Objective Alpha Public Proof Bundle has reached
its sixteen-entry capacity.

## Motivation

The Source Intent Mixed Runtime Public Proof Bundle is the smallest current
end-to-end Universal Compute research proof that connects Source Intent plain
data, execution-free metadata conversion, mixed backend placement,
trusted runtime execution, output contracts, public output closure, reference
correctness, and backend equivalence.

Keeping it outside the fixed public proof bundle preserves the stable first
review surface while still making the new proof discoverable and machine
reviewable.

## Decision

Add this catalog admission spec:

```text
evidence_id: source_intent_mixed_runtime_public_proof_bundle
entry_point: python examples/source_intent_mixed_runtime_public_proof_bundle.py
artifact_kind: schema_versioned_source_intent_mixed_runtime_public_proof_bundle_report
extension_tier: frontend_runtime_proof
digest_source: source_intent_mixed_runtime_public_proof_bundle_report
raw_output_policy: digest_only
```

The Objective Alpha Public Evidence Catalog report and admission gate must bind
this entry by metadata digest only.

## Required Artifacts

- Catalog example: `examples/objective_alpha_public_evidence_catalog.py`
- Catalog schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- Catalog golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- Catalog docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`
- Catalog admission gate example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- Catalog admission gate schema: `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- Catalog admission gate docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`
- Source Intent mixed proof docs: `docs/SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md`

## Security Boundary

This RFC does not authorize broad source parsing, Python execution, Triton JIT,
plugin discovery, device access, generated artifact execution, backend artifact
execution, host path exposure, runtime handles, raw tensor values, value
digests, commands, raw source text, Source Intent payload bodies, raw benchmark
output, or native performance claims.

The catalog entry is data-only. The catalog stores the SHA-256 digest of the
serialized proof report and bounded metadata about the entry.

## Acceptance Criteria

- The catalog keeps the fixed public proof bundle at sixteen entries and admits
  this entry through the RFC-bound catalog growth surface.
- The new entry is ordered after the Source-To-Intent Kernel Ingress Proof
  Bundle and before the Source-To-Intent Research Capability Claim Gate.
- The admission gate requires the new digest binding invariant
  `source_intent_mixed_runtime_public_proof_bundle_digest_entry_bound`.
- The schemas are closed with `additionalProperties: false` and digest-only
  fields.
- Golden evidence and tests pass without adding source, execution, path,
  plugin, device, generated-code, backend-artifact, or performance-claim
  surfaces.
