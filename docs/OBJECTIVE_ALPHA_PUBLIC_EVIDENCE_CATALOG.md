# Objective Alpha Public Evidence Catalog

Objective Alpha Public Evidence Catalog v0 is the separate digest-only review
surface for public evidence that should not be appended to the fixed sixteen
entry Objective Alpha Public Proof Bundle.

Run it with:

```bash
python examples/objective_alpha_public_evidence_catalog.py
```

The report is schema-versioned at:

```text
schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/objective_alpha_public_evidence_catalog.json
```

## What It Proves

The catalog proves that Objective Alpha has a stable extension surface after the
public proof bundle reached `entry_count: 16` and `entry_capacity: 16`.

The catalog currently binds four entries by SHA-256 metadata digest:

- the initial governance entry for the
  [Objective Alpha Evidence Extension Policy](OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md);
- the first non-governance `runtime_proof` entry for
  [Runtime Backend Equivalence Portfolio](RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md);
- a `frontend_runtime_proof` entry for
  [Source-To-Intent Research Kernel Ingress Proof Bundle](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md);
- a `claim_boundary` entry for the
  [Source-To-Intent Research Capability Claim Gate](SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md).

Future catalog entries must be added through an RFC and must remain
schema-versioned, digest-only, source-free in public reports, and free of
execution handles, device access, generated-artifact execution, and native
performance claims.

The catalog now emits machine-readable extension-tier coverage evidence:
`catalog_required_extension_tiers`, `catalog_missing_extension_tiers`, and
`catalog_extension_tier_coverage_status`. The current required set is
`governance`, `runtime_proof`, `frontend_runtime_proof`, and
`claim_boundary`; the status must be `complete` and the missing-tier list must
be empty.

The [Objective Alpha Public Evidence Catalog Admission Gate](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
machine-checks those admission rules. Canonical doc path:
`docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`.

## Entry Admission Pattern

Catalog entries are admitted through a typed, data-only admission pattern before
they become public catalog rows. The pattern is the internal source of truth for
current catalog evidence IDs, entry points, artifact kinds, extension tiers,
digest source labels, and raw-output policies.

This keeps the catalog and the admission gate aligned without executing entry
points or resolving filesystem paths. The only accepted raw-output policy is
`digest_only`; unsafe fragments such as source text, raw tensor values, runtime
handles, host paths, device identifiers, backend artifacts, generated code,
dynamic libraries, plugin entrypoints, and raw benchmark output are rejected at
spec construction time.

The pattern is governed by
`rfcs/0236-objective-alpha-catalog-entry-admission-pattern.md`.

## Why This Exists

The public proof bundle is the first reviewer entrypoint. The catalog is the
growth surface. Keeping them separate lets TUC add evidence without making the
main proof path harder to audit.

## Contract

- Example: `examples/objective_alpha_public_evidence_catalog.py`
- Schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- Tests: `tests/test_objective_alpha_public_evidence_catalog.py`
- Admission gate: [Objective Alpha Public Evidence Catalog Admission Gate](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
- Admission gate example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- Admission gate schema:
  `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- Initial catalog decision: `rfcs/0233-objective-alpha-public-evidence-catalog.md`
- First runtime-proof entry decision:
  `rfcs/0235-objective-alpha-backend-equivalence-portfolio-catalog-entry.md`
- Kernel Ingress Proof Bundle catalog-entry decision:
  `rfcs/0237-objective-alpha-kernel-ingress-proof-bundle-catalog-entry.md`
- Catalog extension-tier coverage decision:
  `rfcs/0238-objective-alpha-catalog-extension-tier-coverage.md`
- Capability Claim Gate catalog-entry decision:
  `rfcs/0240-objective-alpha-capability-claim-gate-catalog-entry.md`

## Security Boundary

The catalog serializes only bounded metadata, entry IDs, entry points, artifact
kinds, extension tiers, SHA-256 digests, blocked claims, blocked execution
surfaces, and policy status. It does not execute entry points, discover plugins,
access devices, load dynamic libraries, run JIT code, spawn subprocesses, touch
the network, parse source, or authorize generated artifacts.

It does not serialize tensor values, source text, runtime handles, host paths,
device identifiers, backend artifacts, raw timing samples, or raw benchmark
output.