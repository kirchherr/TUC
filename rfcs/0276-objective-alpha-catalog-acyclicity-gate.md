# RFC 0276: Objective Alpha Catalog Acyclicity Gate

- Status: Accepted
- Date: 2026-07-28
- Related:
  - `rfcs/0233-objective-alpha-public-evidence-catalog.md`
  - `rfcs/0234-objective-alpha-public-evidence-catalog-admission-gate.md`
  - `rfcs/0275-objective-alpha-real-triton-first-slice-portfolio-catalog-entry.md`

## Context

Objective Alpha public evidence now grows through a separate public evidence
catalog after the fixed 16-entry public proof bundle reached capacity. The
catalog is useful only if entries remain below the catalog, catalog admission,
and research-claim gates. A catalog entry that binds one of those downstream
review surfaces can create a dependency cycle and make the public proof story
harder to audit.

## Decision

Add `examples/objective_alpha_catalog_acyclicity_gate.py` as a data-only review
gate for the current catalog. The gate reads fixed versioned Golden artifacts,
confirms the catalog and catalog admission gate still pass, scans each catalog
entry report for forbidden downstream dependency IDs, and emits only SHA-256
digests plus bounded PASS metadata.

The v0 report is schema-versioned at
`schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json`, has
golden evidence at `tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json`,
and is documented at `docs/OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md`.

## Required Invariants

- the Objective Alpha Public Evidence Catalog report passes;
- the Objective Alpha Public Evidence Catalog Admission Gate report passes;
- catalog entries do not bind catalog or claim gates;
- catalog entry reports remain source-free;
- forbidden downstream IDs are absent from scanned entry reports;
- dependency cycle count remains zero.

## Security Boundary

The gate must not execute catalog entry points, import frontend packages,
discover plugins, access devices, load dynamic libraries, run JIT code, spawn
subprocesses, touch the network, parse source, or authorize generated artifacts.
It must not serialize report bodies, source text, raw tensor values, runtime
handles, host paths, device identifiers, backend artifacts, raw benchmark data,
or generated code.

## Consequences

Future Objective Alpha catalog additions now have an explicit machine-checkable
review guard that prevents catalog entries from depending on the catalog,
catalog admission gate, Objective Alpha research claim, Objective Alpha research
claim gate, or project-level research-scope claim gate.
