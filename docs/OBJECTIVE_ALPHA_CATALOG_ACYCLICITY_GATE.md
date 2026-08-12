# Objective Alpha Catalog Acyclicity Gate

Objective Alpha Catalog Acyclicity Gate v0 is the machine-checkable guardrail
that keeps public catalog entries below Objective Alpha catalog and claim gates.
It prevents future catalog rows from binding downstream review surfaces back into
the catalog-entry layer.

Run it with:

```bash
python examples/objective_alpha_catalog_acyclicity_gate.py
```

The report is schema-versioned at:

```text
schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json
```

## What It Proves

The gate proves that the current
[Objective Alpha Public Evidence Catalog](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md)
and its
[Admission Gate](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
pass before catalog-entry acyclicity is accepted.

It then scans the fixed, versioned evidence artifacts for all nine current
catalog entries and fails closed if any entry report references one of these
downstream dependency IDs:

- `objective_alpha_public_evidence_catalog`
- `objective_alpha_public_evidence_catalog_admission_gate`
- `objective_alpha_research_claim`
- `objective_alpha_research_claim_gate`
- `research_scope_claim_gate`

A passing report emits `cycle_count: 0`, empty `detected_cycles`, empty
`issues`, source-free scan results, and SHA-256 digests for the catalog report,
the catalog admission gate report, and every scanned catalog entry report.

## Security Boundary

The gate reads only fixed repository evidence artifacts and emits only bounded
metadata and SHA-256 digests. It does not execute catalog entry points, import
frontend packages, discover plugins, access devices, load dynamic libraries, run
JIT code, spawn subprocesses, touch the network, parse source, or authorize
generated artifacts.

It does not serialize report bodies, tensor values, source text, runtime
handles, host paths, device identifiers, backend artifacts, raw timing samples,
or raw benchmark output.

## Contract

- Example: `examples/objective_alpha_catalog_acyclicity_gate.py`
- Schema: `schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json`
- Golden: `tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json`
- Tests: `tests/test_objective_alpha_catalog_acyclicity_gate.py`
- Catalog doc: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`
- Catalog admission gate doc:
  `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`
- Gate decision: `rfcs/0276-objective-alpha-catalog-acyclicity-gate.md`
