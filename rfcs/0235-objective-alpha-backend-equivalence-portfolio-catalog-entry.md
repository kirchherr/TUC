# RFC 0235: Objective Alpha Backend Equivalence Portfolio Catalog Entry

## Status

Accepted.

## Context

RFC 0233 created the Objective Alpha Public Evidence Catalog as the digest-only
extension surface after the fixed sixteen-entry Public Proof Bundle reached
capacity. RFC 0234 added an Admission Gate for that catalog.

The catalog initially contained only the governance entry that bound the
Objective Alpha Evidence Extension Policy. That proved the growth surface, but
it did not yet prove that non-governance research evidence can be admitted
without diluting the public proof boundary.

Runtime Backend Equivalence Portfolio v0 already aggregates the systolic,
vector, and mixed-backend equivalence slices as schema-versioned, data-only
backend-diversity evidence. It is the strongest current non-governance evidence
candidate because it directly supports the Universal Compute thesis while still
blocking native performance, device access, and vendor-replacement claims.

## Decision

Add `runtime_backend_equivalence_portfolio` as the first non-governance entry in
Objective Alpha Public Evidence Catalog v0.

The public catalog contract remains anchored at:

- example: `examples/objective_alpha_public_evidence_catalog.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`

The catalog entry is:

- evidence ID: `runtime_backend_equivalence_portfolio`
- entry point: `python examples/runtime_backend_equivalence_portfolio.py`
- artifact kind: `schema_versioned_backend_equivalence_portfolio_report`
- extension tier: `runtime_proof`
- raw output policy: `digest_only`

The catalog stores only the SHA-256 digest of the serialized portfolio report.
The serialized portfolio report remains owned by its existing schema, golden,
docs, tests, and Runtime Evidence Gate binding.

## Security Boundary

This catalog entry does not execute the portfolio example, resolve paths, access
devices, discover plugins, load dynamic libraries, spawn subprocesses, touch the
network, run JIT code, parse source, or authorize generated artifacts.

It does not serialize tensor values, source text, runtime handles, host paths,
device identifiers, backend artifacts, raw timing samples, raw benchmark output,
or native performance claims.

## Consequences

Objective Alpha Public Evidence Catalog now demonstrates controlled growth with
one governance entry and one runtime-proof entry.

Future non-governance catalog entries must follow the same model: existing
schema-versioned evidence first, RFC-bound catalog admission second, digest-only
public linkage always.