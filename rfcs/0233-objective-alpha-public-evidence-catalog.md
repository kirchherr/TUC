# RFC 0233: Objective Alpha Public Evidence Catalog

## Status

Accepted.

## Context

RFC 0232 intentionally froze the Objective Alpha Public Proof Bundle as the
stable first public review entrypoint and required a deliberate extension path
before new public evidence could grow beyond the fixed 16-entry bundle.

Without a separate catalog, future evidence would either overload the bundle or
remain scattered across docs and examples.

## Decision

Add Objective Alpha Public Evidence Catalog v0 as a data-only report:

- example: `examples/objective_alpha_public_evidence_catalog.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`

The catalog binds the existing Objective Alpha Evidence Extension Policy by
metadata digest as its initial governance entry. It also anchors the stable
public proof bundle digest and preserves the same blocked claims, blocked
execution surfaces, and digest-only/source-free controls.

## Growth Policy

Catalog growth is append-only and RFC-bound. New catalog entries must be
schema-versioned, digest-only, source-free in public reports, and must not
serialize tensor values, source text, runtime handles, host paths, device
identifiers, backend artifacts, raw timing samples, or raw benchmark output.

The catalog does not authorize device access, generated-artifact execution,
third-party backend execution, broad source parsing, or native performance
claims.

## Consequences

Objective Alpha now has two public layers:

1. The fixed Public Proof Bundle for the first reviewer path.
2. The Public Evidence Catalog for controlled future evidence growth.

This keeps the core proof legible while allowing TUC to keep adding research
evidence without diluting the first entrypoint.