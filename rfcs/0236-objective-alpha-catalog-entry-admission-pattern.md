# RFC 0236: Objective Alpha Catalog Entry Admission Pattern

## Status

Accepted.

## Context

RFC 0233 created the Objective Alpha Public Evidence Catalog as the digest-only
extension surface after the fixed sixteen-entry Objective Alpha Public Proof
Bundle reached capacity. RFC 0234 added the catalog Admission Gate. RFC 0235
added the first non-governance `runtime_proof` entry, Runtime Backend
Equivalence Portfolio.

That sequence proved that catalog growth can stay separate from the fixed public
bundle, but it also created a drift risk: evidence IDs, entry points, artifact
kinds, extension tiers, digest sources, and raw-output policies could be updated
in separate constants or reports instead of one reviewed source of truth.

## Decision

Add a typed Objective Alpha Public Evidence Catalog Entry Admission Pattern as
an internal source of truth for current catalog entries.

Each admission spec contains only bounded data:

- evidence ID;
- entry point string;
- artifact kind;
- extension tier;
- digest source label;
- raw output policy.

The pattern derives the catalog's expected evidence IDs, entry points, artifact
kinds, extension tiers, digest sources, and raw-output policies from those specs.
The catalog builder then constructs public catalog entries from the reviewed
specs plus SHA-256 metadata digests from existing schema-versioned reports.

The public catalog contract remains anchored at:

- example: `examples/objective_alpha_public_evidence_catalog.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`

## Security Boundary

The admission pattern is data-only. It does not execute entry points, resolve
paths, import modules, discover plugins, access devices, load dynamic libraries,
spawn subprocesses, touch the network, run JIT code, parse source, or authorize
generated artifacts.

Admission spec text is bounded, schema-like metadata. It rejects unsafe path or
URL syntax, source text, raw tensor values, runtime handles, host paths, device
identifiers, backend artifacts, generated code, raw timing samples, raw benchmark
output, plugin entrypoints, and dynamic-library surfaces.

The only accepted public raw-output policy remains `digest_only`.

## Consequences

Future Objective Alpha catalog entries have a clearer review path: add or update
one admission spec, prove the existing report digest, and let the catalog and
Admission Gate derive their fixed expectations from that source.

This does not expand the fixed Objective Alpha Public Proof Bundle, does not add
an executable plugin path, and does not make any native performance or vendor
replacement claim.
