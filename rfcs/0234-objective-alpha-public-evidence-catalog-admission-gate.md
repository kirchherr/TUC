# RFC 0234: Objective Alpha Public Evidence Catalog Admission Gate

## Status

Accepted.

## Context

RFC 0233 added Objective Alpha Public Evidence Catalog v0 as the growth surface
for public evidence outside the fixed sixteen-entry Public Proof Bundle.

A catalog without an admission gate would still depend on manual review to catch
entry drift, relaxed digest policies, or accidental reintroduction of execution
surfaces.

## Decision

Add Objective Alpha Public Evidence Catalog Admission Gate v0 as a data-only
report:

- example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`

The gate accepts the current Public Evidence Catalog only when the catalog
passes, the catalog digest is bound, the stable Public Proof Bundle remains full,
the Extension Policy digest is bound, the initial catalog entry remains fixed,
and catalog growth stays append-only and RFC-bound.

## Security Boundary

The gate does not execute entry points, parse source, access devices, discover
plugins, spawn subprocesses, run JIT code, load dynamic libraries, access the
network, or authorize generated artifacts.

It serializes bounded metadata only and preserves the existing blocked claims,
blocked execution surfaces, and digest-only/source-free controls.

## Consequences

Objective Alpha now has a three-layer public evidence path:

1. Public Proof Bundle: the fixed first reviewer entrypoint.
2. Public Evidence Catalog: the controlled growth surface.
3. Catalog Admission Gate: the machine-checkable policy guard for that surface.

Future catalog growth can be reviewed against the same admission contract rather
than relying on README or roadmap text alone.