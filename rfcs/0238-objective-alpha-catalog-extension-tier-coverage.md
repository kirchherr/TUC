# RFC 0238: Objective Alpha Catalog Extension-Tier Coverage

## Status

Accepted.

## Context

Objective Alpha Public Evidence Catalog v0 has grown from a governance-only
extension point into a small public proof surface with governance,
runtime-proof, and frontend-runtime-proof entries. Reviewers should not have to
infer that proof-role balance only by inspecting individual catalog rows.

The catalog already remains digest-only, source-free, RFC-bound, and separate
from the fixed sixteen-entry Objective Alpha Public Proof Bundle. The next
useful tightening is to make the required extension-tier coverage explicit in
both the catalog report and the admission gate.

## Decision

Add machine-readable extension-tier coverage fields to the Objective Alpha
Public Evidence Catalog and its Admission Gate:

- `catalog_required_extension_tiers`
- `catalog_missing_extension_tiers`
- `catalog_extension_tier_coverage_status`

The required v0 tiers are:

- `governance`
- `runtime_proof`
- `frontend_runtime_proof`

The catalog and admission gate must report `catalog_extension_tier_coverage_status:
complete` and an empty `catalog_missing_extension_tiers` list.

The public catalog contract remains anchored at:

- example: `examples/objective_alpha_public_evidence_catalog.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`

The admission-gate contract remains anchored at:

- example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`

## Security Boundary

This change is data-only. It does not execute catalog entry points, resolve
paths, access devices, discover plugins, load dynamic libraries, spawn
subprocesses, run JIT code, touch the network, parse source, import frontend
modules, or authorize generated artifacts.

It does not serialize module source, extracted kernel source, Source Intent
payloads, tensor values, runtime handles, host paths, device identifiers,
backend artifacts, raw timing samples, raw benchmark output, or native
performance claims.

## Consequences

Objective Alpha now exposes not only which catalog entries exist, but also which
public proof roles are required and whether any required role is missing. This
keeps the Universal Compute proof surface balanced without expanding the fixed
Public Proof Bundle or opening new execution surfaces.

Future catalog tiers can be added by RFC, but the admission gate remains
fail-closed: missing required coverage is a report construction error, not a
review note.